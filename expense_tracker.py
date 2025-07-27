from typing import Dict, List, Any, Optional
from database import Database
from llm_processor import ExpenseExtractor, QueryAnalyzer
import datetime


class ExpenseTracker:
    def __init__(self, db_path: str = "expense_tracker.db"):
        """Khởi tạo expense tracker"""
        self.db = Database(db_path)
        self.llm_processor = ExpenseExtractor()
        self.query_analyzer = QueryAnalyzer()
        self.current_user_id = 1  # Mặc định user đầu tiên
    
    def process_user_message(self, message: str) -> Dict[str, Any]:
        """
        Xử lý tin nhắn từ người dùng
        Returns: Dict chứa kết quả xử lý và thông tin phản hồi
        """
        
        # Bước 1: Phân tích intent
        intent_result = self.query_analyzer.analyze_intent(message)
        
        if intent_result['confidence'] < 0.4:
            return {
                'success': False,
                'message': f"Không hiểu rõ ý định của bạn. {intent_result['analysis']}",
                'suggestion': "Vui lòng thử lại với: 'ăn/uống [món] [giá]' hoặc 'xóa [món]'"
            }
        
        # Bước 2: Xử lý theo intent
        intent = intent_result['intent']
        
        if intent == 'add_expense':
            return self._handle_expense_entry(message)
        elif intent == 'delete_expense':
            return self._handle_expense_deletion(message)
        elif intent == 'update_balance':
            balance_update = self.llm_processor.process_balance_update(message)
            if balance_update:
                return self._handle_balance_update(balance_update)
            else:
                return {
                    'success': False,
                    'message': 'Không thể xử lý lệnh cập nhật số dư'
                }
        else:
            return {
                'success': False,
                'message': f"Chưa hỗ trợ loại yêu cầu này: {intent_result['analysis']}",
                'suggestion': "Thử: 'ăn phở 30k' hoặc 'xóa giao dịch phở'"
            }
    
    def _handle_expense_entry(self, message: str) -> Dict[str, Any]:
        """Xử lý việc thêm chi tiêu"""
        try:
            # Trích xuất thông tin từ LLM
            expense_info = self.llm_processor.extract_expense_info(message)
            
            if expense_info['confidence'] < 0.4:  # Giảm threshold để dễ dàng hơn
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
                }
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
                return {
                    'success': True,
                    'message': "✅ Đã cập nhật số dư",
                    'balance': current_balance,
                    'updated_fields': balance_update
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
                    }
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