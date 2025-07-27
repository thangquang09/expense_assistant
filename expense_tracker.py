from typing import Dict, List, Any, Optional
from database import Database
from llm_processor import ExpenseExtractor, QueryAnalyzer
from google_sheets_sync import get_sheets_sync
import datetime


class ExpenseTracker:
    def __init__(self, db_path: str = "expense_tracker.db"):
        """Khởi tạo expense tracker"""
        self.db = Database(db_path)
        self.llm_processor = ExpenseExtractor()
        self.query_analyzer = QueryAnalyzer()
        self.sheets_sync = get_sheets_sync()
        self.current_user_id = 1  # Mặc định user đầu tiên
        
        # Auto sync if enabled
        if self.sheets_sync.enabled:
            print("🔗 Google Sheets sync được kích hoạt")
    
    def process_user_message(self, message: str) -> Dict[str, Any]:
        """
        Xử lý tin nhắn từ người dùng
        Returns: Dict chứa kết quả xử lý và thông tin phản hồi
        """
        
        # Bước 1: Phân tích intent
        intent_result = self.query_analyzer.analyze_intent(message)
        
        # Check offline mode
        offline_mode = intent_result.get('offline_mode', False)
        
        if intent_result['confidence'] < 0.3:  # Giảm threshold cho offline mode
            suggestion = "Vui lòng thử lại với: 'ăn/uống [món] [giá]' hoặc 'xóa [món]'"
            if offline_mode:
                suggestion += "\n🔴 Chế độ offline: Vui lòng nhập rõ ràng hơn"
            
            return {
                'success': False,
                'message': f"Không hiểu rõ ý định của bạn. {intent_result['analysis']}",
                'suggestion': suggestion,
                'offline_mode': offline_mode
            }
        
        # Bước 2: Xử lý theo intent
        intent = intent_result['intent']
        
        result = None
        if intent == 'add_expense':
            result = self._handle_expense_entry(message)
        elif intent == 'delete_expense':
            result = self._handle_expense_deletion(message)
        elif intent == 'update_balance':
            # Kiểm tra xem có phải là cập nhật số dư không
            balance_update = self.llm_processor._extract_balance_update_info(message)
            if balance_update:
                result = self._handle_balance_update(balance_update)
            else:
                result = {
                    'success': False,
                    'message': 'Không thể xử lý lệnh cập nhật số dư'
                }
        elif intent == 'view_statistics':
            result = self._handle_statistics_request(message)
        else:
            suggestion = "Thử: 'ăn phở 30k', 'xóa phở', 'thống kê hôm nay'"
            if offline_mode:
                suggestion += "\n🔴 Chế độ offline: Nhập chính xác hơn"
            
            result = {
                'success': False,
                'message': f"Chưa hỗ trợ loại yêu cầu này: {intent_result['analysis']}",
                'suggestion': suggestion
            }
        
        # Thêm thông tin offline mode vào result
        if result and offline_mode:
            result['offline_mode'] = True
            if result.get('success', False):
                result['message'] = f"🔴 {result['message']} (offline mode)"
        
        return result
    
    def _handle_expense_entry(self, message: str) -> Dict[str, Any]:
        """Xử lý việc thêm chi tiêu"""
        try:
            # Trích xuất thông tin từ LLM
            expense_info = self.llm_processor.extract_expense_info(message)
            
            # Điều chỉnh threshold dựa trên chế độ offline
            min_confidence = 0.25 if expense_info.get('offline_mode', False) else 0.4
            
            if expense_info['confidence'] < min_confidence:
                return {
                    'success': False,
                    'message': f"Không thể hiểu rõ thông tin chi tiêu. Độ tin cậy: {expense_info['confidence']:.2f}",
                    'suggestion': "Vui lòng thử lại với format: '[thời gian] ăn/uống [món] [giá]' (VD: 'trưa ăn phở 35k')"
                }
            
            # Thêm vào database với transaction_type và account_type
            transaction_id = self.db.add_transaction(
                user_id=self.current_user_id,
                food_item=expense_info['food_item'],
                price=expense_info['price'],
                meal_time=expense_info['meal_time'],
                transaction_type=expense_info.get('transaction_type', 'expense'),
                account_type=expense_info.get('account_type', 'cash')
            )
            
            # Tự động cập nhật số dư
            balance_updated = self._auto_update_balance(expense_info)
            
            # Lấy thống kê nhanh
            today_summary = self.db.get_spending_summary(self.current_user_id, 1)  # Hôm nay
            week_summary = self.db.get_spending_summary(self.current_user_id, 7)   # Tuần này
            
            # Auto sync to Google Sheets nếu enabled
            if self.sheets_sync.enabled:
                try:
                    # Sync transaction vừa tạo
                    new_transaction = {
                        'id': transaction_id,
                        'food_item': expense_info['food_item'],
                        'price': expense_info['price'],
                        'meal_time': expense_info['meal_time'],
                        'transaction_date': datetime.date.today().isoformat(),
                        'transaction_time': datetime.datetime.now().time().isoformat(),
                        'created_at': datetime.datetime.now().isoformat()
                    }
                    self.sheets_sync.sync_transactions([new_transaction])
                except Exception as e:
                    print(f"⚠️ Lỗi sync to Sheets: {e}")
            
            # Tạo thông điệp phản hồi
            transaction_type = expense_info.get('transaction_type', 'expense')
            account_type = expense_info.get('account_type', 'cash')
            
            if transaction_type == 'income':
                action_icon = "💰"
                action_text = "Đã ghi nhận thu nhập"
            else:
                action_icon = "💸"  
                action_text = "Đã ghi nhận chi tiêu"
            
            account_text = "tiền mặt" if account_type == 'cash' else "tài khoản"
            
            return {
                'success': True,
                'transaction_id': transaction_id,
                'message': f"{action_icon} {action_text}: {expense_info['food_item']} - {expense_info['price']:,.0f}đ ({account_text})",
                'expense_info': expense_info,
                'balance_updated': balance_updated,
                'statistics': {
                    'today_total': today_summary['total_spent'] or 0,
                    'today_count': today_summary['transaction_count'],
                    'week_total': week_summary['total_spent'] or 0,
                    'week_count': week_summary['transaction_count'],
                    'this_transaction': expense_info['price']
                },
                'synced_to_sheets': self.sheets_sync.enabled
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Lỗi xử lý: {str(e)}",
                'error': str(e)
            }
    
    def _auto_update_balance(self, transaction_info: Dict[str, Any]) -> bool:
        """Tự động cập nhật số dư dựa trên giao dịch"""
        try:
            transaction_type = transaction_info.get('transaction_type', 'expense')
            account_type = transaction_info.get('account_type', 'cash')
            amount = transaction_info['price']
            
            # Xác định số tiền cộng/trừ
            if transaction_type == 'income':
                # Thu nhập -> cộng vào số dư
                balance_change = amount
            else:
                # Chi tiêu -> trừ khỏi số dư  
                balance_change = -amount
            
            # Cập nhật số dư theo loại tài khoản
            if account_type == 'cash':
                success = self.db.update_balance_by_amount(
                    user_id=self.current_user_id,
                    cash_amount=balance_change
                )
            else:  # account
                success = self.db.update_balance_by_amount(
                    user_id=self.current_user_id,
                    account_amount=balance_change
                )
            
            return success
            
        except Exception as e:
            print(f"⚠️ Lỗi cập nhật số dư tự động: {e}")
            return False
    
    def _handle_balance_update(self, balance_update: Dict[str, float]) -> Dict[str, Any]:
        """Xử lý việc cập nhật số dư"""
        try:
            # Phân biệt giữa SET (thiết lập) và ADD (cộng/trừ)
            is_set_operation = 'cash_balance' in balance_update or 'account_balance' in balance_update
            is_add_operation = 'cash_amount' in balance_update or 'account_amount' in balance_update
            
            if is_set_operation:
                # SET Operation: Thiết lập số dư về giá trị cụ thể
                success = self.db.update_user_balance(
                    user_id=self.current_user_id,
                    cash_balance=balance_update.get('cash_balance'),
                    account_balance=balance_update.get('account_balance')
                )
                operation_type = "set"
                
            elif is_add_operation:
                # ADD Operation: Cộng/trừ vào số dư hiện tại
                success = self.db.update_balance_by_amount(
                    user_id=self.current_user_id,
                    cash_amount=balance_update.get('cash_amount'),
                    account_amount=balance_update.get('account_amount')
                )
                operation_type = "add"
                
            else:
                return {
                    'success': False,
                    'message': "❌ Không xác định được loại thao tác cập nhật số dư"
                }
            
            if success:
                current_balance = self.db.get_user_balance(self.current_user_id)
                
                # Auto sync balance to Google Sheets
                if self.sheets_sync.enabled:
                    try:
                        self.sheets_sync.sync_balance(current_balance)
                    except Exception as e:
                        print(f"⚠️ Lỗi sync balance to Sheets: {e}")
                
                # Tạo thông điệp mô tả thay đổi
                changes = []
                
                if operation_type == "set":
                    # Thông báo thiết lập số dư
                    if balance_update.get('cash_balance') is not None:
                        amount = balance_update['cash_balance']
                        changes.append(f"Tiền mặt = {amount:,.0f}đ")
                        
                    if balance_update.get('account_balance') is not None:
                        amount = balance_update['account_balance']
                        changes.append(f"Tài khoản = {amount:,.0f}đ")
                    
                    action_icon = "🔄"
                    action_text = "Đã thiết lập số dư"
                    
                else:
                    # Thông báo cộng/trừ số dư
                    if balance_update.get('cash_amount') is not None:
                        amount = balance_update['cash_amount']
                        if amount > 0:
                            changes.append(f"Tiền mặt +{amount:,.0f}đ")
                        else:
                            changes.append(f"Tiền mặt {amount:,.0f}đ")
                            
                    if balance_update.get('account_amount') is not None:
                        amount = balance_update['account_amount']
                        if amount > 0:
                            changes.append(f"Tài khoản +{amount:,.0f}đ")
                        else:
                            changes.append(f"Tài khoản {amount:,.0f}đ")
                    
                    action_icon = "💰"
                    action_text = "Đã cập nhật số dư"
                
                change_text = ", ".join(changes)
                
                return {
                    'success': True,
                    'message': f"{action_icon} {action_text}: {change_text}",
                    'balance': current_balance,
                    'updated_fields': balance_update,
                    'operation_type': operation_type,
                    'synced_to_sheets': self.sheets_sync.enabled
                }
            else:
                return {
                    'success': False,
                    'message': "❌ Không thể cập nhật số dư"
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Lỗi cập nhật số dư: {str(e)}"
            }
    
    def _handle_expense_deletion(self, message: str) -> Dict[str, Any]:
        """Xử lý việc xóa giao dịch"""
        try:
            # Kiểm tra các trường hợp đặc biệt để xóa giao dịch gần nhất
            message_clean = message.strip().lower()
            
            # Các từ khóa để xóa giao dịch gần nhất
            recent_keywords = ['xóa', 'gần nhất', 'recent', 'last', 'latest', '']
            
            # Nếu chỉ là từ khóa đơn giản, xóa giao dịch gần nhất
            if (message_clean in recent_keywords or 
                message_clean == 'xóa giao dịch gần nhất' or
                message_clean == 'xóa gần nhất' or
                len(message_clean) == 0):
                
                # Xóa giao dịch gần nhất
                delete_result = self.db.delete_most_recent_transaction(self.current_user_id)
                
                if delete_result['success']:
                    # Tự động cập nhật số dư (đảo ngược giao dịch)
                    balance_updated = self._reverse_balance_for_deleted_transaction(delete_result['deleted_transaction'])
                    
                    # Lấy thống kê sau khi xóa
                    today_summary = self.db.get_spending_summary(self.current_user_id, 1)
                    week_summary = self.db.get_spending_summary(self.current_user_id, 7)
                    
                    return {
                        'success': True,
                        'message': f"🗑️ {delete_result['message']}",
                        'deleted_info': {
                            'food_item': delete_result['deleted_transaction']['food_item'],
                            'price': delete_result['deleted_transaction']['price'],
                            'meal_time': delete_result['deleted_transaction'].get('meal_time'),
                            'confidence': 1.0  # 100% confident vì xóa chính xác
                        },
                        'deleted_transaction': delete_result['deleted_transaction'],
                        'balance_updated': balance_updated,
                        'statistics': {
                            'today_total': today_summary['total_spent'] or 0,
                            'today_count': today_summary['transaction_count'],
                            'week_total': week_summary['total_spent'] or 0,
                            'week_count': week_summary['transaction_count'],
                            'deleted_amount': delete_result['deleted_transaction']['price']
                        },
                        'note': 'Đã xóa giao dịch gần nhất và cập nhật số dư'
                    }
                else:
                    return {
                        'success': False,
                        'message': f"❌ {delete_result['message']}",
                        'suggestion': "Không có giao dịch nào để xóa"
                    }
            
            # Trường hợp bình thường: trích xuất thông tin từ LLM
            delete_info = self.llm_processor.extract_delete_info(message)
            
            if delete_info['confidence'] < 0.4:
                return {
                    'success': False,
                    'message': f"Không thể hiểu rõ giao dịch cần xóa. Độ tin cậy: {delete_info['confidence']:.2f}",
                    'suggestion': "Vui lòng thử: 'xóa [món ăn]', 'xóa [món ăn] [giá]', hoặc chỉ 'xóa' để xóa giao dịch gần nhất"
                }
            
            # Xóa giao dịch từ database
            delete_result = self.db.delete_transaction_by_criteria(
                user_id=self.current_user_id,
                food_item=delete_info['food_item'],
                price=delete_info['price'],
                meal_time=delete_info['meal_time']
            )
            
            if delete_result['success']:
                # Tự động cập nhật số dư (đảo ngược giao dịch)
                balance_updated = self._reverse_balance_for_deleted_transaction(delete_result['deleted_transaction'])
                
                # Lấy thống kê sau khi xóa
                today_summary = self.db.get_spending_summary(self.current_user_id, 1)
                week_summary = self.db.get_spending_summary(self.current_user_id, 7)
                
                # Note: Không auto sync deletion to Sheets vì có thể phức tạp
                # User có thể manually export lại nếu cần
                
                return {
                    'success': True,
                    'message': f"🗑️ {delete_result['message']}",
                    'deleted_info': delete_info,
                    'deleted_transaction': delete_result['deleted_transaction'],
                    'balance_updated': balance_updated,
                    'statistics': {
                        'today_total': today_summary['total_spent'] or 0,
                        'today_count': today_summary['transaction_count'],
                        'week_total': week_summary['total_spent'] or 0,
                        'week_count': week_summary['transaction_count'],
                        'deleted_amount': delete_result['deleted_transaction']['price']
                    },
                    'note': 'Để sync deletion lên Sheets, dùng menu Export'
                }
            else:
                return {
                    'success': False,
                    'message': f"❌ {delete_result['message']}",
                    'suggestion': "Kiểm tra lại tên món ăn hoặc xem danh sách giao dịch gần đây. Hoặc chỉ gõ 'xóa' để xóa giao dịch gần nhất."
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Lỗi xử lý xóa giao dịch: {str(e)}",
                'error': str(e)
            }
    
    def _reverse_balance_for_deleted_transaction(self, deleted_transaction: Dict[str, Any]) -> bool:
        """Đảo ngược tác động của giao dịch bị xóa lên số dư"""
        try:
            # Sử dụng thông tin từ deleted_transaction (đã có đầy đủ account_type và transaction_type)
            transaction_type = deleted_transaction.get('transaction_type', 'expense')
            account_type = deleted_transaction.get('account_type', 'cash')
            amount = deleted_transaction['price']
            
            print(f"🔍 Giao dịch bị xóa: {transaction_type} từ {account_type}")
            
            # Đảo ngược tác động
            if transaction_type == 'income':
                # Thu nhập bị xóa → trừ khỏi số dư
                balance_change = -amount
                print(f"💰➖ Thu nhập bị xóa: -{amount:,.0f}đ từ {account_type}")
            else:
                # Chi tiêu bị xóa → cộng vào số dư
                balance_change = amount
                print(f"💸➕ Chi tiêu bị xóa: +{amount:,.0f}đ vào {account_type}")
            
            # Cập nhật số dư theo ĐÚNG loại tài khoản
            if account_type == 'cash':
                success = self.db.update_balance_by_amount(
                    user_id=self.current_user_id,
                    cash_amount=balance_change
                )
                print(f"💵 Cập nhật tiền mặt: {'+' if balance_change > 0 else ''}{balance_change:,.0f}đ")
            else:  # account
                success = self.db.update_balance_by_amount(
                    user_id=self.current_user_id,
                    account_amount=balance_change
                )
                print(f"🏦 Cập nhật tài khoản: {'+' if balance_change > 0 else ''}{balance_change:,.0f}đ")
            
            if success:
                print("✅ Đã đảo ngược số dư thành công")
            else:
                print("❌ Lỗi đảo ngược số dư")
                
            return success
            
        except Exception as e:
            print(f"⚠️ Lỗi đảo ngược số dư: {e}")
            return False
    
    def _handle_statistics_request(self, message: str) -> Dict[str, Any]:
        """Xử lý yêu cầu xem thống kê"""
        try:
            # Trích xuất thông tin thống kê
            stats_info = self.llm_processor.extract_statistics_info(message)
            
            if stats_info['confidence'] < 0.4:
                return {
                    'success': False,
                    'message': f"Không hiểu rõ yêu cầu thống kê. Độ tin cậy: {stats_info['confidence']:.2f}",
                    'suggestion': "Thử: 'thống kê hôm nay', 'chi tiêu tuần này', 'báo cáo 5 ngày'"
                }
            
            # Lấy dữ liệu thống kê
            days = stats_info['days']
            summary = self.db.get_spending_summary(self.current_user_id, days)
            recent_transactions = self.db.get_recent_transactions(self.current_user_id, 5)
            
            # Auto sync statistics to Sheets nếu enabled
            if self.sheets_sync.enabled:
                try:
                    stats_data = summary.copy()
                    stats_data['days'] = days
                    self.sheets_sync.sync_statistics(stats_data)
                except Exception as e:
                    print(f"⚠️ Lỗi sync statistics to Sheets: {e}")
            
            # Tạo thông điệp phù hợp
            period_text = {
                'today': 'hôm nay',
                'week': 'tuần này', 
                'month': 'tháng này',
                'custom': f'{days} ngày qua'
            }.get(stats_info['period'], f'{days} ngày')
            
            return {
                'success': True,
                'message': f"📊 Thống kê chi tiêu {period_text}",
                'statistics_detailed': {
                    'period': period_text,
                    'days': days,
                    'total_spent': summary['total_spent'] or 0,
                    'transaction_count': summary['transaction_count'],
                    'avg_spent': summary['avg_spent'] or 0,
                    'min_spent': summary['min_spent'] or 0,
                    'max_spent': summary['max_spent'] or 0,
                    'recent_transactions': recent_transactions[:3]  # Top 3 gần nhất
                },
                'synced_to_sheets': self.sheets_sync.enabled
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Lỗi xử lý thống kê: {str(e)}",
                'error': str(e)
            }
    
    def export_to_sheets(self) -> Dict[str, Any]:
        """Export toàn bộ dữ liệu lên Google Sheets"""
        if not self.sheets_sync.enabled:
            return {
                'success': False,
                'message': 'Google Sheets sync chưa được kích hoạt',
                'suggestion': 'Setup credentials.json để kích hoạt'
            }
        
        try:
            success = self.sheets_sync.export_full_data(self.db)
            if success:
                url = self.sheets_sync.get_spreadsheet_url()
                return {
                    'success': True,
                    'message': '🎉 Đã export toàn bộ dữ liệu lên Google Sheets',
                    'spreadsheet_url': url
                }
            else:
                return {
                    'success': False,
                    'message': 'Lỗi khi export dữ liệu'
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Lỗi export: {str(e)}"
            }
    
    def get_balance_summary(self) -> Dict[str, Any]:
        """Lấy tổng quan số dư"""
        balance = self.db.get_user_balance(self.current_user_id)
        return {
            'cash_balance': balance['cash_balance'],
            'account_balance': balance['account_balance'],
            'total_balance': balance['cash_balance'] + balance['account_balance']
        }
    
    def get_spending_report(self, days: int = 7) -> Dict[str, Any]:
        """Lấy báo cáo chi tiêu"""
        summary = self.db.get_spending_summary(self.current_user_id, days)
        recent_transactions = self.db.get_recent_transactions(self.current_user_id, 10)
        
        return {
            'period_days': days,
            'summary': summary,
            'recent_transactions': recent_transactions,
            'balance': self.get_balance_summary()
        }
    
    def get_recent_transactions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Lấy giao dịch gần đây"""
        return self.db.get_recent_transactions(self.current_user_id, limit) 