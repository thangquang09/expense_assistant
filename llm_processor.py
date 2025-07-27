import os
import re
import datetime
from typing import Dict, Optional, Any
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage

# Load environment variables
load_dotenv()


class QueryAnalyzer:
    def __init__(self):
        """Khởi tạo Query Analyzer để phân tích intent"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY không được tìm thấy trong file .env")
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0.1
        )
    
    def analyze_intent(self, user_message: str) -> Dict[str, Any]:
        """
        Phân tích intent của câu chat
        Returns: Dict với intent và thông tin liên quan
        """
        
        system_prompt = """
        Bạn là chuyên gia phân tích ý định (intent) từ câu chat về chi tiêu.
        
        Phân tích câu chat và xác định intent:
        1. "add_expense" - Thêm giao dịch chi tiêu mới
        2. "delete_expense" - Xóa giao dịch chi tiêu đã có
        3. "update_balance" - Cập nhật số dư tài khoản
        4. "unknown" - Không rõ ý định
        
        Trả về JSON chính xác:
        {
            "intent": "add_expense|delete_expense|update_balance|unknown",
            "confidence": 0.9,
            "analysis": "giải thích ngắn gọn"
        }
        
        Từ khóa nhận biết:
        - add_expense: "ăn", "uống", "mua", "order", "gọi", có giá tiền
        - delete_expense: "xóa", "xoá", "hủy", "bỏ", "delete", "remove"
        - update_balance: "cập nhật", "tiền mặt", "tài khoản", "số dư"
        
        Ví dụ:
        Input: "ăn phở 30k"
        Output: {"intent": "add_expense", "confidence": 0.95, "analysis": "Thêm giao dịch ăn phở"}
        
        Input: "xóa giao dịch ăn phở 30k"
        Output: {"intent": "delete_expense", "confidence": 0.9, "analysis": "Xóa giao dịch ăn phở"}
        
        Input: "cập nhật tiền mặt 500k"
        Output: {"intent": "update_balance", "confidence": 0.95, "analysis": "Cập nhật số dư tiền mặt"}
        """
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Câu chat: '{user_message}'")
            ]
            
            response = self.llm.invoke(messages)
            response_text = response.content.strip()
            
            return self._parse_intent_response(response_text, user_message)
            
        except Exception as e:
            print(f"Lỗi phân tích intent: {e}")
            return self._fallback_intent_analysis(user_message)
    
    def _parse_intent_response(self, response_text: str, original_message: str) -> Dict[str, Any]:
        """Parse response từ LLM cho intent analysis"""
        try:
            import json
            
            # Làm sạch response
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            result = json.loads(response_text)
            
            # Validate intent
            valid_intents = ['add_expense', 'delete_expense', 'update_balance', 'unknown']
            if result.get('intent') not in valid_intents:
                raise ValueError("Intent không hợp lệ")
            
            return {
                'intent': result['intent'],
                'confidence': min(max(result.get('confidence', 0.5), 0.0), 1.0),
                'analysis': result.get('analysis', '')
            }
            
        except Exception as e:
            print(f"Lỗi parse intent response: {e}")
            return self._fallback_intent_analysis(original_message)
    
    def _fallback_intent_analysis(self, message: str) -> Dict[str, Any]:
        """Fallback rule-based intent analysis"""
        message_lower = message.lower()
        
        # Kiểm tra delete intent
        delete_keywords = ['xóa', 'xoá', 'hủy', 'bỏ', 'delete', 'remove']
        if any(keyword in message_lower for keyword in delete_keywords):
            return {
                'intent': 'delete_expense',
                'confidence': 0.7,
                'analysis': 'Phát hiện từ khóa xóa'
            }
        
        # Kiểm tra update balance intent
        balance_keywords = ['cập nhật', 'tiền mặt', 'tài khoản', 'số dư']
        if any(keyword in message_lower for keyword in balance_keywords):
            return {
                'intent': 'update_balance', 
                'confidence': 0.7,
                'analysis': 'Phát hiện từ khóa cập nhật số dư'
            }
        
        # Kiểm tra add expense intent
        expense_keywords = ['ăn', 'uống', 'mua', 'order', 'gọi']
        price_patterns = [r'\d+k', r'\d+000', r'\d+\s*nghìn']
        
        has_expense_keyword = any(keyword in message_lower for keyword in expense_keywords)
        has_price = any(re.search(pattern, message_lower) for pattern in price_patterns)
        
        if has_expense_keyword and has_price:
            return {
                'intent': 'add_expense',
                'confidence': 0.6,
                'analysis': 'Phát hiện từ khóa chi tiêu và giá tiền'
            }
        
        return {
            'intent': 'unknown',
            'confidence': 0.3,
            'analysis': 'Không xác định được ý định'
        }


class ExpenseExtractor:
    def __init__(self):
        """Khởi tạo LLM processor với Google Gemini"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY không được tìm thấy trong file .env")
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0.1  # Để kết quả ít random hơn
        )
    
    def extract_expense_info(self, user_message: str) -> Dict[str, Any]:
        """
        Trích xuất thông tin chi tiêu từ câu chat của người dùng
        Returns: Dict với keys: food_item, price, meal_time, confidence
        """
        
        # System prompt để hướng dẫn LLM
        system_prompt = """
        Bạn là một chuyên gia trích xuất thông tin chi tiêu từ văn bản tiếng Việt.
        
        Từ câu chat của người dùng, hãy trích xuất:
        1. food_item: Tên món ăn/đồ uống (bắt buộc)
        2. price: Giá tiền bằng số (bắt buộc) 
        3. meal_time: Thời điểm ăn (sáng, trưa, chiều, tối, hoặc giờ cụ thể nếu có)
        
        Trả về kết quả theo định dạng JSON chính xác:
        {
            "food_item": "tên món ăn",
            "price": số_tiền_số,
            "meal_time": "thời_điểm_ăn hoặc null",
            "confidence": 0.9
        }
        
        Lưu ý:
        - price phải là số, không có ký tự đặc biệt
        - Nếu không xác định được meal_time thì để null
        - confidence từ 0.0 đến 1.0 thể hiện độ tin cậy
        - Chỉ trả về JSON, không có text khác
        
        Ví dụ:
        Input: "trưa ăn phở 35k"
        Output: {"food_item": "phở", "price": 35000, "meal_time": "trưa", "confidence": 0.95}
        
        Input: "mua cà phê 25000"
        Output: {"food_item": "cà phê", "price": 25000, "meal_time": null, "confidence": 0.9}
        """
        
        try:
            # Tạo messages cho LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Câu chat: '{user_message}'")
            ]
            
            # Gọi LLM
            response = self.llm.invoke(messages)
            response_text = response.content.strip()
            
            # Xử lý response
            return self._parse_llm_response(response_text, user_message)
            
        except Exception as e:
            print(f"Lỗi khi gọi LLM: {e}")
            # Fallback về rule-based parsing
            return self._fallback_extraction(user_message)
    
    def extract_delete_info(self, user_message: str) -> Dict[str, Any]:
        """
        Trích xuất thông tin giao dịch cần xóa
        Returns: Dict với keys: food_item, price (optional), meal_time (optional)
        """
        
        system_prompt = """
        Bạn là chuyên gia trích xuất thông tin giao dịch cần xóa từ câu chat.
        
        Từ câu chat về việc xóa giao dịch, hãy trích xuất:
        1. food_item: Tên món ăn/đồ uống cần xóa (bắt buộc)
        2. price: Giá tiền (tùy chọn, để tìm chính xác hơn)
        3. meal_time: Thời điểm ăn (tùy chọn)
        
        Trả về JSON:
        {
            "food_item": "tên món ăn",
            "price": số_tiền_hoặc_null,
            "meal_time": "thời_điểm_hoặc_null",
            "confidence": 0.9
        }
        
        Ví dụ:
        Input: "xóa giao dịch ăn phở 30k"
        Output: {"food_item": "phở", "price": 30000, "meal_time": null, "confidence": 0.9}
        
        Input: "xóa trưa uống cà phê"
        Output: {"food_item": "cà phê", "price": null, "meal_time": "trưa", "confidence": 0.85}
        
        Input: "hủy ăn bánh"
        Output: {"food_item": "bánh", "price": null, "meal_time": null, "confidence": 0.8}
        """
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Câu chat: '{user_message}'")
            ]
            
            response = self.llm.invoke(messages)
            response_text = response.content.strip()
            
            return self._parse_delete_response(response_text, user_message)
            
        except Exception as e:
            print(f"Lỗi khi trích xuất thông tin xóa: {e}")
            return self._fallback_delete_extraction(user_message)
    
    def _parse_delete_response(self, response_text: str, original_message: str) -> Dict[str, Any]:
        """Parse response cho delete extraction"""
        try:
            import json
            
            # Làm sạch response
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            result = json.loads(response_text)
            
            if not isinstance(result.get('food_item'), str) or not result['food_item']:
                raise ValueError("food_item không hợp lệ")
            
            return {
                'food_item': result['food_item'].strip(),
                'price': float(result['price']) if result.get('price') else None,
                'meal_time': result.get('meal_time'),
                'confidence': min(max(result.get('confidence', 0.5), 0.0), 1.0)
            }
            
        except Exception as e:
            print(f"Lỗi parse delete response: {e}")
            return self._fallback_delete_extraction(original_message)
    
    def _fallback_delete_extraction(self, message: str) -> Dict[str, Any]:
        """Fallback extraction cho delete"""
        result = {
            'food_item': '',
            'price': None,
            'meal_time': None,
            'confidence': 0.4
        }
        
        # Loại bỏ các từ khóa xóa để tìm món ăn
        message_clean = message.lower()
        delete_words = ['xóa', 'xoá', 'hủy', 'bỏ', 'delete', 'remove', 'giao dịch']
        for word in delete_words:
            message_clean = message_clean.replace(word, ' ')
        
        # Tìm giá tiền
        price_patterns = [r'(\d+)k', r'(\d+)000', r'(\d+)\s*nghìn']
        for pattern in price_patterns:
            match = re.search(pattern, message_clean)
            if match:
                price_str = match.group(1)
                if 'k' in pattern or 'nghìn' in pattern:
                    result['price'] = float(price_str) * 1000
                else:
                    result['price'] = float(price_str)
                break
        
        # Tìm meal_time
        meal_patterns = {
            'sáng': ['sáng', 'buổi sáng'],
            'trưa': ['trưa', 'buổi trưa'],
            'chiều': ['chiều', 'buổi chiều'],
            'tối': ['tối', 'buổi tối']
        }
        
        for meal_time, keywords in meal_patterns.items():
            if any(keyword in message_clean for keyword in keywords):
                result['meal_time'] = meal_time
                break
        
        # Tìm món ăn (từ còn lại sau khi loại bỏ các từ khóa)
        food_keywords = ['ăn', 'uống', 'mua']
        words = message_clean.split()
        
        for i, word in enumerate(words):
            if any(keyword in word for keyword in food_keywords):
                if i + 1 < len(words):
                    result['food_item'] = words[i + 1]
                    break
        
        if not result['food_item']:
            # Lấy từ có vẻ như món ăn
            for word in words:
                if len(word) > 2 and word not in ['sáng', 'trưa', 'chiều', 'tối']:
                    result['food_item'] = word
                    break
        
        if not result['food_item']:
            result['food_item'] = 'Không xác định'
        
        return result
    
    def _parse_llm_response(self, response_text: str, original_message: str) -> Dict[str, Any]:
        """Parse response từ LLM"""
        try:
            # Tìm JSON trong response
            import json
            
            # Làm sạch response text
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            # Parse JSON
            result = json.loads(response_text)
            
            # Validate kết quả
            if not isinstance(result.get('food_item'), str) or not result['food_item']:
                raise ValueError("food_item không hợp lệ")
            
            if not isinstance(result.get('price'), (int, float)) or result['price'] <= 0:
                raise ValueError("price không hợp lệ")
            
            # Đảm bảo các field bắt buộc
            return {
                'food_item': result['food_item'].strip(),
                'price': float(result['price']),
                'meal_time': result.get('meal_time'),
                'confidence': min(max(result.get('confidence', 0.5), 0.0), 1.0)
            }
            
        except Exception as e:
            print(f"Lỗi parse LLM response: {e}")
            return self._fallback_extraction(original_message)
    
    def _fallback_extraction(self, message: str) -> Dict[str, Any]:
        """Fallback rule-based extraction khi LLM thất bại"""
        result = {
            'food_item': '',
            'price': 0.0,
            'meal_time': None,
            'confidence': 0.3  # Confidence thấp cho fallback
        }
        
        # Tìm giá tiền
        price_patterns = [
            r'(\d+)k',  # 35k
            r'(\d+)000',  # 35000
            r'(\d+)\s*nghìn',  # 35 nghìn
            r'(\d+\.\d+)k',  # 35.5k
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, message.lower())
            if match:
                price_str = match.group(1)
                if 'k' in pattern or 'nghìn' in pattern:
                    result['price'] = float(price_str) * 1000
                else:
                    result['price'] = float(price_str)
                break
        
        # Tìm meal_time
        meal_patterns = {
            'sáng': ['sáng', 'buổi sáng', 'breakfast'],
            'trưa': ['trưa', 'buổi trưa', 'lunch'],
            'chiều': ['chiều', 'buổi chiều', 'afternoon'],
            'tối': ['tối', 'buổi tối', 'dinner', 'supper']
        }
        
        message_lower = message.lower()
        for meal_time, keywords in meal_patterns.items():
            if any(keyword in message_lower for keyword in keywords):
                result['meal_time'] = meal_time
                break
        
        # Tìm món ăn (simple heuristic)
        food_keywords = ['ăn', 'uống', 'mua', 'order', 'gọi']
        for keyword in food_keywords:
            if keyword in message_lower:
                # Tìm từ ngay sau keyword
                words = message.split()
                for i, word in enumerate(words):
                    if keyword in word.lower() and i + 1 < len(words):
                        result['food_item'] = words[i + 1]
                        break
                break
        
        if not result['food_item']:
            result['food_item'] = 'Không xác định'
        
        return result
    
    def process_balance_update(self, message: str) -> Optional[Dict[str, float]]:
        """
        Xử lý câu lệnh cập nhật số dư
        Returns: Dict với cash_balance và/hoặc account_balance, hoặc None nếu không phải lệnh cập nhật
        """
        
        system_prompt = """
        Bạn là chuyên gia phân tích câu lệnh cập nhật số dư tài chính.
        
        Từ câu chat, xác định xem có phải là lệnh cập nhật số dư không và trích xuất:
        1. cash_balance: Số dư tiền mặt (nếu có)
        2. account_balance: Số dư tài khoản ngân hàng (nếu có)
        
        Trả về JSON:
        {
            "is_balance_update": true/false,
            "cash_balance": số_tiền_hoặc_null,
            "account_balance": số_tiền_hoặc_null
        }
        
        Từ khóa cho tiền mặt: "tiền mặt", "cash", "tiền lẻ"
        Từ khóa cho tài khoản: "tài khoản", "ngân hàng", "account", "atm"
        
        Ví dụ:
        Input: "cập nhật tiền mặt 500k"
        Output: {"is_balance_update": true, "cash_balance": 500000, "account_balance": null}
        
        Input: "tài khoản còn 2 triệu"
        Output: {"is_balance_update": true, "cash_balance": null, "account_balance": 2000000}
        """
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Câu chat: '{message}'")
            ]
            
            response = self.llm.invoke(messages)
            response_text = response.content.strip()
            
            # Parse response
            import json
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            result = json.loads(response_text)
            
            if result.get('is_balance_update', False):
                balance_update = {}
                if result.get('cash_balance') is not None:
                    balance_update['cash_balance'] = float(result['cash_balance'])
                if result.get('account_balance') is not None:
                    balance_update['account_balance'] = float(result['account_balance'])
                
                return balance_update if balance_update else None
            
        except Exception as e:
            print(f"Lỗi xử lý balance update: {e}")
        
        return None 