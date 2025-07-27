import os
import re
import datetime
from typing import Dict, Optional, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global flag để track trạng thái kết nối
_llm_available = True
_offline_warning_shown = False


class QueryAnalyzer:
    def __init__(self):
        """Khởi tạo Query Analyzer để phân tích intent"""
        global _llm_available
        
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                print("⚠️ Không tìm thấy GEMINI_API_KEY - chuyển sang chế độ offline")
                _llm_available = False
                self.llm = None
                return
            
            # Test connection nhanh trước khi khởi tạo LLM
            if not self._test_connection():
                print("⚠️ Không có kết nối internet - chuyển sang chế độ offline")
                _llm_available = False
                self.llm = None
                return
            
            # Chỉ import khi có API key và internet
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=api_key,
                temperature=0.1
            )
        except Exception as e:
            print(f"⚠️ Lỗi khởi tạo LLM: {e} - chuyển sang chế độ offline")
            _llm_available = False
            self.llm = None
    
    def _test_connection(self) -> bool:
        """Test kết nối internet nhanh"""
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except (OSError, socket.timeout):
            return False
    
    def analyze_intent(self, user_message: str) -> Dict[str, Any]:
        """
        Phân tích intent của câu chat
        Returns: Dict với intent và thông tin liên quan
        """
        global _llm_available, _offline_warning_shown
        
        # Nếu đã biết offline, skip LLM ngay
        if not _llm_available or not self.llm:
            if not _offline_warning_shown:
                print("\n🔴 CHẾ ĐỘ OFFLINE")
                print("💡 Vui lòng nhập rõ ràng hơn: 'ăn phở 30k', 'xóa phở', 'thống kê hôm nay'")
                _offline_warning_shown = True
            
            result = self._fallback_intent_analysis(user_message)
            result['offline_mode'] = True
            return result
        
        # Thử dùng LLM với timeout ngắn
        try:
            return self._analyze_with_llm(user_message)
        except Exception as e:
            print(f"⚠️ LLM không khả dụng: {e}")
            _llm_available = False
            
            # Hiển thị warning một lần
            if not _offline_warning_shown:
                print("\n🔴 CHUYỂN SANG CHẾ ĐỘ OFFLINE")
                print("💡 Vui lòng nhập rõ ràng hơn: 'ăn phở 30k', 'xóa phở', 'thống kê hôm nay'")
                _offline_warning_shown = True
            
            result = self._fallback_intent_analysis(user_message)
            result['offline_mode'] = True
            return result
    
    def _analyze_with_llm(self, user_message: str) -> Dict[str, Any]:
        """Phân tích với LLM - với timeout"""
        from langchain.schema import HumanMessage, SystemMessage
        
        system_prompt = """
        Bạn là chuyên gia phân tích ý định (intent) từ câu chat về chi tiêu.
        
        Phân tích câu chat và xác định intent:
        1. "add_expense" - Thêm giao dịch chi tiêu mới
        2. "delete_expense" - Xóa giao dịch chi tiêu đã có
        3. "update_balance" - Cập nhật số dư tài khoản
        4. "view_statistics" - Xem thống kê chi tiêu
        5. "unknown" - Không rõ ý định
        
        Trả về JSON chính xác:
        {
            "intent": "add_expense|delete_expense|update_balance|view_statistics|unknown",
            "confidence": 0.9,
            "analysis": "giải thích ngắn gọn"
        }
        
        Từ khóa nhận biết:
        - add_expense: "ăn", "uống", "mua", "order", "gọi", có giá tiền
        - delete_expense: "xóa", "xoá", "hủy", "bỏ", "delete", "remove"
        - update_balance: "cập nhật", "tiền mặt", "tài khoản", "số dư"
        - view_statistics: "thống kê", "báo cáo", "tổng", "chi tiêu", "xem", "hôm nay", "tuần", "tháng"
        
        Ví dụ:
        Input: "ăn phở 30k"
        Output: {"intent": "add_expense", "confidence": 0.95, "analysis": "Thêm giao dịch ăn phở"}
        
        Input: "xóa giao dịch ăn phở 30k"
        Output: {"intent": "delete_expense", "confidence": 0.9, "analysis": "Xóa giao dịch ăn phở"}
        
        Input: "cập nhật tiền mặt 500k"
        Output: {"intent": "update_balance", "confidence": 0.95, "analysis": "Cập nhật số dư tiền mặt"}
        
        Input: "thống kê hôm nay"
        Output: {"intent": "view_statistics", "confidence": 0.9, "analysis": "Xem thống kê chi tiêu hôm nay"}
        
        Input: "tổng chi tiêu tuần này"
        Output: {"intent": "view_statistics", "confidence": 0.85, "analysis": "Xem tổng chi tiêu tuần này"}
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Câu chat: '{user_message}'")
        ]
        
        # Thêm timeout ngắn hơn cho LLM call
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("LLM call timeout")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(5)  # 5 giây timeout
        
        try:
            response = self.llm.invoke(messages)
            signal.alarm(0)  # Cancel timeout
            response_text = response.content.strip()
            return self._parse_intent_response(response_text, user_message)
        finally:
            signal.alarm(0)  # Ensure timeout is cancelled
    
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
            valid_intents = ['add_expense', 'delete_expense', 'update_balance', 'view_statistics', 'unknown']
            if result.get('intent') not in valid_intents:
                raise ValueError("Intent không hợp lệ")
            
            return {
                'intent': result['intent'],
                'confidence': min(max(result.get('confidence', 0.5), 0.0), 1.0),
                'analysis': result.get('analysis', ''),
                'offline_mode': False
            }
            
        except Exception as e:
            print(f"Lỗi parse LLM response: {e}")
            return self._fallback_intent_analysis(original_message)
    
    def _fallback_intent_analysis(self, message: str) -> Dict[str, Any]:
        """Enhanced rule-based intent analysis cho chế độ offline"""
        message_lower = message.lower().strip()
        
        # Enhanced delete patterns
        delete_patterns = [
            r'(xóa|xoá|hủy|bỏ|delete|remove)',
            r'(xóa\s*(giao\s*dịch|transaction))',
            r'(hủy\s*(giao\s*dịch|transaction))'
        ]
        
        if any(re.search(pattern, message_lower) for pattern in delete_patterns):
            return {
                'intent': 'delete_expense',
                'confidence': 0.8,
                'analysis': 'Phát hiện từ khóa xóa (offline mode)',
                'offline_mode': True
            }
        
        # Enhanced statistics patterns
        stats_patterns = [
            r'(thống\s*kê|báo\s*cáo|tổng\s*kết)',
            r'(chi\s*tiêu\s*(hôm\s*nay|tuần|tháng))',
            r'(xem\s*(chi\s*tiêu|thống\s*kê))',
            r'(hôm\s*nay|tuần\s*này|tháng\s*này)',
            r'(\d+\s*ngày(\s*qua|\s*gần\s*đây)?)',
            r'(tổng\s*(chi\s*tiêu|tiền))'
        ]
        
        if any(re.search(pattern, message_lower) for pattern in stats_patterns):
            return {
                'intent': 'view_statistics',
                'confidence': 0.85,
                'analysis': 'Phát hiện từ khóa thống kê (offline mode)',
                'offline_mode': True
            }
        
        # Enhanced balance update patterns
        balance_patterns = [
            r'(cập\s*nhật|update).*(tiền\s*mặt|cash|số\s*dư)',
            r'(tiền\s*mặt|cash).*(còn|có|\d)',
            r'(tài\s*khoản|account|ngân\s*hàng).*(còn|có|\d)',
            r'(số\s*dư).*(cập\s*nhật|update|còn|\d)'
        ]
        
        if any(re.search(pattern, message_lower) for pattern in balance_patterns):
            return {
                'intent': 'update_balance',
                'confidence': 0.8,
                'analysis': 'Phát hiện từ khóa cập nhật số dư (offline mode)',
                'offline_mode': True
            }
        
        # Enhanced expense patterns
        expense_patterns = [
            r'(ăn|uống|mua|order|gọi|ôrđơ)\s+\w+\s*\d+',  # "ăn phở 30k"
            r'(sáng|trưa|chiều|tối)\s+(ăn|uống)\s+\w+',    # "trưa ăn phở"
            r'\w+\s*\d+k?\s*(nghìn|ngàn)?',                # "phở 30k"
            r'(breakfast|lunch|dinner)\s+\w+',              # English patterns
        ]
        
        # Kiểm tra có giá tiền không
        price_patterns = [r'\d+k\b', r'\d+000\b', r'\d+\s*(nghìn|ngàn)', r'\d+\.\d+k']
        has_price = any(re.search(pattern, message_lower) for pattern in price_patterns)
        
        # Kiểm tra có từ khóa ăn uống không
        food_keywords = ['ăn', 'uống', 'mua', 'order', 'gọi', 'breakfast', 'lunch', 'dinner']
        has_food_keyword = any(keyword in message_lower for keyword in food_keywords)
        
        if (has_price and has_food_keyword) or any(re.search(pattern, message_lower) for pattern in expense_patterns):
            return {
                'intent': 'add_expense',
                'confidence': 0.75,
                'analysis': 'Phát hiện từ khóa chi tiêu và giá tiền (offline mode)',
                'offline_mode': True
            }
        
        return {
            'intent': 'unknown',
            'confidence': 0.2,
            'analysis': 'Không xác định được ý định (offline mode)',
            'offline_mode': True
        }


class ExpenseExtractor:
    def __init__(self):
        """Khởi tạo LLM processor với Google Gemini"""
        global _llm_available
        
        # Kiểm tra global flag trước
        if not _llm_available:
            self.llm = None
            return
            
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                print("⚠️ Không tìm thấy GEMINI_API_KEY cho ExpenseExtractor")
                _llm_available = False
                self.llm = None
                return
            
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=api_key,
                temperature=0.1  # Để kết quả ít random hơn
            )
        except Exception as e:
            print(f"⚠️ Lỗi khởi tạo ExpenseExtractor: {e}")
            _llm_available = False
            self.llm = None
    
    def extract_expense_info(self, user_message: str) -> Dict[str, Any]:
        """
        Trích xuất thông tin chi tiêu từ câu chat của người dùng
        Returns: Dict với keys: food_item, price, meal_time, confidence
        """
        global _llm_available
        
        # Nếu offline, skip LLM ngay
        if not _llm_available or not self.llm:
            return self._fallback_extraction(user_message)
        
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
            from langchain.schema import HumanMessage, SystemMessage
            
            # Tạo messages cho LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Câu chat: '{user_message}'")
            ]
            
            # Gọi LLM với timeout
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("LLM call timeout")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(3)  # 3 giây timeout cho extraction
            
            try:
                response = self.llm.invoke(messages)
                signal.alarm(0)
                response_text = response.content.strip()
                
                # Xử lý response
                return self._parse_llm_response(response_text, user_message)
            finally:
                signal.alarm(0)
            
        except Exception as e:
            print(f"Lỗi khi gọi LLM: {e}")
            _llm_available = False
            # Fallback về rule-based parsing
            return self._fallback_extraction(user_message)
    
    def extract_delete_info(self, user_message: str) -> Dict[str, Any]:
        """
        Trích xuất thông tin giao dịch cần xóa
        Returns: Dict với keys: food_item, price (optional), meal_time (optional)
        """
        
        if not self.llm:
            return self._fallback_delete_extraction(user_message)
        
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
            from langchain.schema import HumanMessage, SystemMessage
            
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
            'confidence': 0.3,  # Base confidence cho fallback
            'offline_mode': True  # Flag để nhận biết offline mode
        }
        
        message_lower = message.lower()
        confidence_boost = 0.0
        
        # Tìm giá tiền
        price_patterns = [
            r'(\d+)k\b',  # 35k
            r'(\d+)000\b',  # 35000
            r'(\d+)\s*nghìn\b',  # 35 nghìn
            r'(\d+\.\d+)k\b',  # 35.5k
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, message_lower)
            if match:
                price_str = match.group(1)
                if 'k' in pattern or 'nghìn' in pattern:
                    result['price'] = float(price_str) * 1000
                else:
                    result['price'] = float(price_str)
                confidence_boost += 0.2  # Có giá tiền rõ ràng
                break
        
        # Tìm meal_time
        meal_patterns = {
            'sáng': ['sáng', 'buổi sáng', 'breakfast'],
            'trưa': ['trưa', 'buổi trưa', 'lunch'],
            'chiều': ['chiều', 'buổi chiều', 'afternoon'],
            'tối': ['tối', 'buổi tối', 'dinner', 'supper']
        }
        
        for meal_time, keywords in meal_patterns.items():
            if any(keyword in message_lower for keyword in keywords):
                result['meal_time'] = meal_time
                confidence_boost += 0.15  # Có thời gian rõ ràng
                break
        
        # Tìm món ăn - enhanced logic
        food_keywords = ['ăn', 'uống', 'mua', 'order', 'gọi']
        words = message.split()
        
        # Strategy 1: Tìm từ ngay sau food keyword
        for i, word in enumerate(words):
            word_lower = word.lower()
            for keyword in food_keywords:
                if keyword in word_lower and i + 1 < len(words):
                    potential_food = words[i + 1]
                    # Loại bỏ số tiền khỏi tên món
                    potential_food = re.sub(r'\d+k?', '', potential_food).strip()
                    if potential_food and len(potential_food) > 1:
                        result['food_item'] = potential_food
                        confidence_boost += 0.2  # Có món ăn rõ ràng
                        break
            if result['food_item']:
                break
        
        # Strategy 2: Nếu chưa tìm được, tìm từ có ý nghĩa
        if not result['food_item']:
            for word in words:
                word_clean = re.sub(r'\d+k?', '', word.lower()).strip()
                # Loại bỏ các từ thời gian và action
                skip_words = ['sáng', 'trưa', 'chiều', 'tối', 'ăn', 'uống', 'mua', 'order', 'gọi', 'buổi']
                if word_clean not in skip_words and len(word_clean) > 2:
                    result['food_item'] = word_clean
                    confidence_boost += 0.1  # Có món ăn nhưng không chắc chắn
                    break
        
        # Strategy 3: Fallback - lấy từ đầu tiên không phải keyword
        if not result['food_item']:
            for word in words:
                word_lower = word.lower()
                if (word_lower not in ['sáng', 'trưa', 'chiều', 'tối', 'ăn', 'uống', 'mua'] 
                    and not re.search(r'\d+k?', word_lower) and len(word) > 2):
                    result['food_item'] = word
                    break
        
        if not result['food_item']:
            result['food_item'] = 'Không xác định'
            confidence_boost -= 0.1  # Penalty cho không tìm được món
        
        # Điều chỉnh confidence dựa trên số lượng thông tin tìm được
        final_confidence = result['confidence'] + confidence_boost
        
        # Bonus cho input có format hoàn chỉnh
        if result['price'] > 0 and result['food_item'] != 'Không xác định':
            if result['meal_time']:
                final_confidence += 0.1  # Perfect match: có đủ cả 3 yếu tố
            else:
                final_confidence += 0.05  # Good match: có món và giá
        
        # Đảm bảo confidence trong khoảng hợp lệ
        result['confidence'] = min(max(final_confidence, 0.2), 0.9)
        
        return result
    
    def process_balance_update(self, message: str) -> Optional[Dict[str, float]]:
        """
        Xử lý câu lệnh cập nhật số dư
        Returns: Dict với cash_balance và/hoặc account_balance, hoặc None nếu không phải lệnh cập nhật
        """
        
        if not self.llm:
            return None  # Tạm thời không hỗ trợ offline cho balance update
        
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
            from langchain.schema import HumanMessage, SystemMessage
            
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
    
    def extract_statistics_info(self, user_message: str) -> Dict[str, Any]:
        """
        Trích xuất thông tin yêu cầu thống kê
        Returns: Dict với period (thời gian) và các tham số khác
        """
        
        if not self.llm:
            return self._fallback_statistics_extraction(user_message)
        
        system_prompt = """
        Bạn là chuyên gia trích xuất thông tin yêu cầu thống kê chi tiêu.
        
        Từ câu chat về việc xem thống kê, hãy trích xuất:
        1. period: Khoảng thời gian ("today", "week", "month", hoặc số ngày)
        2. specific_days: Số ngày cụ thể (nếu có)
        
        Trả về JSON:
        {
            "period": "today|week|month|custom",
            "days": số_ngày_hoặc_null,
            "confidence": 0.9
        }
        
        Từ khóa nhận biết:
        - "today": "hôm nay", "ngày hôm nay", "today"
        - "week": "tuần này", "tuần", "7 ngày", "week"
        - "month": "tháng này", "tháng", "30 ngày", "month"
        - "custom": "3 ngày", "5 ngày qua", số ngày cụ thể
        
        Ví dụ:
        Input: "thống kê hôm nay"
        Output: {"period": "today", "days": 1, "confidence": 0.95}
        
        Input: "chi tiêu tuần này"
        Output: {"period": "week", "days": 7, "confidence": 0.9}
        
        Input: "xem báo cáo 5 ngày qua"
        Output: {"period": "custom", "days": 5, "confidence": 0.85}
        
        Input: "tổng chi tiêu"
        Output: {"period": "week", "days": 7, "confidence": 0.7}
        """
        
        try:
            from langchain.schema import HumanMessage, SystemMessage
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Câu chat: '{user_message}'")
            ]
            
            response = self.llm.invoke(messages)
            response_text = response.content.strip()
            
            return self._parse_statistics_response(response_text, user_message)
            
        except Exception as e:
            print(f"Lỗi khi trích xuất thông tin thống kê: {e}")
            return self._fallback_statistics_extraction(user_message)
    
    def _parse_statistics_response(self, response_text: str, original_message: str) -> Dict[str, Any]:
        """Parse response cho statistics extraction"""
        try:
            import json
            
            # Làm sạch response
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            result = json.loads(response_text)
            
            # Validate period
            valid_periods = ['today', 'week', 'month', 'custom']
            if result.get('period') not in valid_periods:
                result['period'] = 'week'  # default
            
            # Validate days
            days = result.get('days', 7)
            if not isinstance(days, (int, float)) or days <= 0:
                days = 7  # default
            
            return {
                'period': result['period'],
                'days': int(days),
                'confidence': min(max(result.get('confidence', 0.5), 0.0), 1.0)
            }
            
        except Exception as e:
            print(f"Lỗi parse statistics response: {e}")
            return self._fallback_statistics_extraction(original_message)
    
    def _fallback_statistics_extraction(self, message: str) -> Dict[str, Any]:
        """Fallback extraction cho statistics"""
        message_lower = message.lower()
        
        # Tìm số ngày cụ thể
        import re
        day_match = re.search(r'(\d+)\s*ngày', message_lower)
        if day_match:
            days = int(day_match.group(1))
            return {
                'period': 'custom',
                'days': days,
                'confidence': 0.8
            }
        
        # Kiểm tra các period cố định
        if any(keyword in message_lower for keyword in ['hôm nay', 'ngày hôm nay']):
            return {
                'period': 'today',
                'days': 1,
                'confidence': 0.9
            }
        
        if any(keyword in message_lower for keyword in ['tuần', 'tuần này', '7 ngày']):
            return {
                'period': 'week',
                'days': 7,
                'confidence': 0.9
            }
        
        if any(keyword in message_lower for keyword in ['tháng', 'tháng này', '30 ngày']):
            return {
                'period': 'month',
                'days': 30,
                'confidence': 0.9
            }
        
        # Default
        return {
            'period': 'week',
            'days': 7,
            'confidence': 0.6
        } 