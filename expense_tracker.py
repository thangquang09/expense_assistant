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
            balance_update = self.llm_processor.process_balance_update(message)
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
            
            # Thêm vào database (chỉ để thống kê)
            transaction_id = self.db.add_transaction(
                user_id=self.current_user_id,
                food_item=expense_info['food_item'],
                price=expense_info['price'],
                meal_time=expense_info['meal_time']
            )
            
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
            
            return {
                'success': True,
                'transaction_id': transaction_id,
                'message': f"✅ Đã ghi nhận: {expense_info['food_item']} - {expense_info['price']:,.0f}đ",
                'expense_info': expense_info,
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
    
    def _handle_balance_update(self, balance_update: Dict[str, float]) -> Dict[str, Any]:
        """Xử lý việc cập nhật số dư"""
        try:
            success = self.db.update_user_balance(
                user_id=self.current_user_id,
                cash_balance=balance_update.get('cash_balance'),
                account_balance=balance_update.get('account_balance')
            )
            
            if success:
                current_balance = self.db.get_user_balance(self.current_user_id)
                
                # Auto sync balance to Google Sheets
                if self.sheets_sync.enabled:
                    try:
                        self.sheets_sync.sync_balance(current_balance)
                    except Exception as e:
                        print(f"⚠️ Lỗi sync balance to Sheets: {e}")
                
                return {
                    'success': True,
                    'message': "✅ Đã cập nhật số dư",
                    'balance': current_balance,
                    'updated_fields': balance_update,
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
            # Trích xuất thông tin giao dịch cần xóa
            delete_info = self.llm_processor.extract_delete_info(message)
            
            if delete_info['confidence'] < 0.4:
                return {
                    'success': False,
                    'message': f"Không thể hiểu rõ giao dịch cần xóa. Độ tin cậy: {delete_info['confidence']:.2f}",
                    'suggestion': "Vui lòng thử: 'xóa [món ăn]' hoặc 'xóa [món ăn] [giá]'"
                }
            
            # Xóa giao dịch từ database
            delete_result = self.db.delete_transaction_by_criteria(
                user_id=self.current_user_id,
                food_item=delete_info['food_item'],
                price=delete_info['price'],
                meal_time=delete_info['meal_time']
            )
            
            if delete_result['success']:
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
                    'suggestion': "Kiểm tra lại tên món ăn hoặc xem danh sách giao dịch gần đây"
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Lỗi xử lý xóa giao dịch: {str(e)}",
                'error': str(e)
            }
    
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