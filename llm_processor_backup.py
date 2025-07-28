import os
import re
import datetime
import logging
from typing import Dict, Optional, Any, List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from config import get_current_model, get_model_settings

# Suppress verbose langchain retry logs
logging.getLogger("langchain_google_genai").setLevel(logging.ERROR)
logging.getLogger("langchain_ollama").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)

# Load environment variables
load_dotenv()

# Global flag để track trạng thái kết nối
_llm_available = True
_offline_warning_shown = False


# Pydantic Models for LLM Response Schemas
class IntentAnalysis(BaseModel):
    """Schema for intent analysis results"""
    intent: str = Field(description="Intent category: add_expense, delete_expense, update_balance, view_statistics, unknown")
    confidence: float = Field(description="Confidence level (0.0-1.0)", ge=0.0, le=1.0)
    analysis: str = Field(description="Brief analysis of the user's intent")


class ExpenseInfo(BaseModel):
    """Schema for expense extraction results"""
    food_item: str = Field(description="Name of food/drink or transaction description")
    price: float = Field(description="Price amount as number")
    meal_time: Optional[str] = Field(default=None, description="Meal time: sáng, trưa, chiều, tối, or specific time")
    transaction_type: str = Field(default="expense", description="Transaction type: expense or income")
    account_type: str = Field(default="cash", description="Account type: cash or account")
    confidence: float = Field(description="Confidence level (0.0-1.0)", ge=0.0, le=1.0)


class BalanceUpdate(BaseModel):
    """Schema for balance update analysis"""
    is_balance_update: bool = Field(description="Whether this is a balance update request")
    operation_type: str = Field(description="Operation type: set or add")
    cash_balance: Optional[float] = Field(default=None, description="Cash balance to set (for SET operations)")
    account_balance: Optional[float] = Field(default=None, description="Account balance to set (for SET operations)")
    cash_amount: Optional[float] = Field(default=None, description="Cash amount to add/subtract (for ADD operations)")
    account_amount: Optional[float] = Field(default=None, description="Account amount to add/subtract (for ADD operations)")
    description: str = Field(description="Brief description of the operation")


class DeleteInfo(BaseModel):
    """Schema for delete transaction analysis"""
    food_item: Optional[str] = Field(default=None, description="Food item to delete")
    price: Optional[float] = Field(default=None, description="Price of transaction to delete")
    meal_time: Optional[str] = Field(default=None, description="Meal time of transaction to delete")
    delete_recent: bool = Field(default=False, description="Whether to delete the most recent transaction")
    confidence: float = Field(description="Confidence level (0.0-1.0)", ge=0.0, le=1.0)


class StatisticsInfo(BaseModel):
    """Schema for statistics request analysis"""
    period: str = Field(description="Statistics period: daily, weekly, monthly")
    specific_date: Optional[str] = Field(default=None, description="Specific date if requested")
    confidence: float = Field(description="Confidence level (0.0-1.0)", ge=0.0, le=1.0)


def create_llm_instance():
    """Tạo instance LLM dựa trên cấu hình hiện tại"""
    global _llm_available
    
    try:
        current_model = get_current_model()
        model_settings = get_model_settings(current_model)
        provider = model_settings["provider"]
        
        if provider == "google":
            # Google Gemini
            api_key = os.getenv(model_settings["api_key_env"])
            if not api_key:
                print(f"⚠️ Không tìm thấy {model_settings['api_key_env']} - chuyển sang chế độ offline")
                return None
            
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            return ChatGoogleGenerativeAI(
                model=model_settings["model_name"],
                google_api_key=api_key,
                temperature=0.1
            )
            
        elif provider == "ollama":
            # Ollama models
            try:
                from langchain_ollama import ChatOllama
                
                # Test Ollama connection
                if not _test_ollama_connection(model_settings["base_url"]):
                    print(f"⚠️ Không thể kết nối Ollama tại {model_settings['base_url']}")
                    print("💡 Hãy khởi động Ollama: ollama serve")
                    return None
                
                return ChatOllama(
                    model=model_settings["model_name"],
                    base_url=model_settings["base_url"],
                    temperature=0.1,
                    timeout=30  # 30 giây timeout cho Ollama
                )
                
            except ImportError:
                print("⚠️ Cần cài đặt langchain-ollama: uv add langchain-ollama")
                return None
        
        else:
            print(f"⚠️ Provider không hỗ trợ: {provider}")
            return None
            
    except Exception as e:
        print(f"⚠️ Lỗi khởi tạo LLM: {e}")
        return None

def _test_ollama_connection(base_url: str) -> bool:
    """Test kết nối đến Ollama server"""
    try:
        import requests
        response = requests.get(f"{base_url}/api/tags", timeout=3)
        return response.status_code == 200
    except Exception:
        return False

class QueryAnalyzer:
    def __init__(self):
        """Khởi tạo Query Analyzer để phân tích intent"""
        global _llm_available
        
        try:
            # Test connection nhanh trước khi khởi tạo LLM
            if not self._test_connection():
                print("⚠️ Không có kết nối internet - chuyển sang chế độ offline")
                _llm_available = False
                self.llm = None
                return
            
            # Sử dụng hàm create_llm_instance mới
            self.llm = create_llm_instance()
            
            if self.llm is None:
                _llm_available = False
                
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
        
        # Thử dùng LLM với error handling cải thiện
        try:
            return self._analyze_with_llm(user_message)
        except Exception as e:
            error_msg = str(e)
            
            # Check for quota error - fail fast
            if "quota" in error_msg.lower() or "429" in error_msg:
                if not _offline_warning_shown:
                    print("⚠️ LLM quota exceeded - chuyển sang offline mode")
                    print("\n🔴 CHUYỂN SANG CHẾ ĐỘ OFFLINE")
                    print("💡 Vui lòng nhập rõ ràng hơn: 'ăn phở 30k', 'xóa phở', 'thống kê hôm nay'")
                    _offline_warning_shown = True
                _llm_available = False
            else:
                print(f"⚠️ LLM không khả dụng: {error_msg[:100]}...")
                _llm_available = False
                
                if not _offline_warning_shown:
                    print("\n🔴 CHUYỂN SANG CHẾ ĐỘ OFFLINE")
                    print("💡 Vui lòng nhập rõ ràng hơn: 'ăn phở 30k', 'xóa phở', 'thống kê hôm nay'")
                    _offline_warning_shown = True
            
            result = self._fallback_intent_analysis(user_message)
            result['offline_mode'] = True
            return result
    
    def _analyze_with_llm(self, user_message: str) -> Dict[str, Any]:
        """Phân tích với LLM - với timeout và Pydantic parser"""
        from langchain.schema import HumanMessage, SystemMessage
        
        # Create Pydantic parser
        parser = PydanticOutputParser(pydantic_object=IntentAnalysis)
        
        system_prompt = """
        Bạn là chuyên gia phân tích ý định (intent) từ câu chat về chi tiêu.
        
        Phân tích câu chat và xác định intent:
        1. "add_expense" - Thêm giao dịch chi tiêu hoặc thu nhập
        2. "delete_expense" - Xóa giao dịch 
        3. "update_balance" - Cập nhật số dư tài khoản
        4. "view_statistics" - Xem thống kê 
        5. "unknown" - Không rõ ý định
        
        Ví dụ phân loại:
        - "ăn phở 30k" → add_expense
        - "lãnh lương 5000k" → add_expense  
        - "xóa phở" → delete_expense
        - "cập nhật tiền mặt 200k" → update_balance
        - "thống kê hôm nay" → view_statistics
        
        {format_instructions}
        """
        
        prompt_template = PromptTemplate(
            template=system_prompt + "\n\nCâu chat: '{user_message}'\n\nPhân tích:",
            input_variables=["user_message"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        try:
            # Create chain
            chain = prompt_template | self.llm | parser
            
            # Invoke chain
            response = chain.invoke({"user_message": user_message})
            
            return {
                'intent': response.intent,
                'confidence': response.confidence,
                'analysis': response.analysis,
                'offline_mode': False
            }
        except Exception as e:
            # Fallback to old parsing if Pydantic fails
            return self._parse_intent_response_fallback(str(e), user_message)
    
    def _parse_intent_response_fallback(self, error_msg: str, original_message: str) -> Dict[str, Any]:
        """Fallback parsing when Pydantic fails"""
        print(f"Pydantic parsing failed: {error_msg[:50]}...")
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
        
        # Enhanced balance update patterns  
        balance_patterns = [
            r'(cập\s*nhật|update).*(số\s*dư|balance|tiền)',
            r'(thiết\s*lập|đặt|set).*(số\s*dư|balance)',
            r'(số\s*dư|balance).*(là|thành|=)',
            r'(tiền\s*mặt|cash).*(là|thành|chỉ\s*có)',
            r'(tài\s*khoản|account).*(là|thành|chỉ\s*có)'
        ]
        
        # Enhanced statistics patterns
        stats_patterns = [
            r'(thống\s*kê|statistic|báo\s*cáo|report)',
            r'(hôm\s*nay|today|daily)',
            r'(tuần|week|weekly)',
            r'(tháng|month|monthly)',
            r'(xem|show|hiển\s*thị).*(chi\s*tiêu|expense)'
        ]
        
        confidence = 0.7
        
        # Check patterns
        for pattern in delete_patterns:
            if re.search(pattern, message_lower):
                return {
                    'intent': 'delete_expense',
                    'confidence': confidence,
                    'analysis': 'Detected delete intent from keywords',
                    'offline_mode': True
                }
        
        for pattern in balance_patterns:
            if re.search(pattern, message_lower):
                return {
                    'intent': 'update_balance', 
                    'confidence': confidence,
                    'analysis': 'Detected balance update intent',
                    'offline_mode': True
                }
        
        for pattern in stats_patterns:
            if re.search(pattern, message_lower):
                return {
                    'intent': 'view_statistics',
                    'confidence': confidence,
                    'analysis': 'Detected statistics request',
                    'offline_mode': True
                }
        
        # Default to expense if has price pattern
        price_pattern = r'\d+[k\.]?\d*[k]?'
        if re.search(price_pattern, message_lower):
            return {
                'intent': 'add_expense',
                'confidence': 0.6,
                'analysis': 'Detected potential expense with price',
                'offline_mode': True
            }
        
        return {
            'intent': 'unknown',
            'confidence': 0.3,
            'analysis': 'Could not determine intent clearly',
            'offline_mode': True
        }


class ExpenseExtractor:
    def __init__(self):
        """Khởi tạo LLM processor với mô hình được cấu hình"""
        global _llm_available
        
        # Kiểm tra global flag trước
        if not _llm_available:
            self.llm = None
            return
            
        try:
            # Sử dụng hàm create_llm_instance chung
            self.llm = create_llm_instance()
            
            if self.llm is None:
                _llm_available = False
                
        except Exception as e:
            print(f"⚠️ Lỗi khởi tạo ExpenseExtractor: {e}")
            _llm_available = False
            self.llm = None
    
    def extract_expense_info(self, user_message: str) -> Dict[str, Any]:
        """
        Trích xuất thông tin chi tiêu từ tin nhắn của user với Pydantic
        Returns: Dict với các keys: food_item, price, meal_time, confidence
        """
        global _llm_available
        
        if not _llm_available or not self.llm:
            return self._fallback_extraction(user_message)
        
        # Create Pydantic parser
        parser = PydanticOutputParser(pydantic_object=ExpenseInfo)
        
        # Enhanced system prompt optimized for Llama3
        system_prompt = """
        Bạn là chuyên gia trích xuất thông tin tài chính từ văn bản tiếng Việt.
        
        Phân loại transaction_type:
        - "income": lãnh lương, nhận tiền, thu nhập, được trả, tiền thưởng, tiền lương
        - "expense": ăn, uống, mua, chi tiêu, trả tiền, mất tiền, tiêu
        
        Phân loại account_type (QUAN TRỌNG):
        - "cash": tiền mặt, cash, tiền lẻ, tiền túi
        - "account": tài khoản, ngân hàng, chuyển khoản, ck, bank, atm, banking
        
        QUAN TRỌNG - Price parsing:
        - Nếu có "k" ở cuối số: nhân với 1000 (ví dụ: 35k = 35000, 5000k = 5000000)
        - Nếu không có "k": giữ nguyên số
        
        QUAN TRỌNG - Account type keywords:
        - "ck" = "chuyển khoản" → account_type PHẢI LÀ "account"
        - "bank" = "ngân hàng" → account_type PHẢI LÀ "account"  
        - "chuyển khoản" → account_type PHẢI LÀ "account"
        - "cash" = "tiền mặt" → account_type PHẢI LÀ "cash"
        
        {format_instructions}
        """
        
        prompt_template = PromptTemplate(
            template=system_prompt + "\n\nCâu chat: '{user_message}'\n\nTrích xuất:",
            input_variables=["user_message"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        try:
            # Gọi LLM với timeout
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("LLM call timeout")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            
            # Timeout khác nhau cho từng provider
            current_model = get_current_model()
            model_settings = get_model_settings(current_model)
            provider = model_settings["provider"]
            
            if provider == "ollama":
                signal.alarm(15)  # 15 giây cho Ollama (model load + inference)
            else:
                signal.alarm(5)   # 5 giây cho Google API
            
            try:
                # Create chain
                chain = prompt_template | self.llm | parser
                
                # Invoke chain
                response = chain.invoke({"user_message": user_message})
                signal.alarm(0)
                
                # Convert Pydantic model to dict with validation
                result = {
                    'food_item': response.food_item,
                    'price': response.price,
                    'meal_time': response.meal_time,
                    'transaction_type': response.transaction_type,
                    'account_type': response.account_type,
                    'confidence': response.confidence,
                    'offline_mode': False
                }
                
                # Validate and fix result
                return self._validate_and_fix_llm_result(result, user_message)
                
            finally:
                signal.alarm(0)
            
        except Exception as e:
            error_msg = str(e)
            
            # Handle quota errors quietly
            if "quota" in error_msg.lower() or "429" in error_msg:
                if _llm_available:  # Only show once
                    print("⚠️ LLM quota exceeded")
                _llm_available = False
            else:
                print(f"⚠️ Lỗi khi gọi LLM: {error_msg[:50]}...")
                _llm_available = False
                
            # Fallback về rule-based parsing
            return self._fallback_extraction(user_message)
    
    def extract_delete_info(self, user_message: str) -> Dict[str, Any]:
        """
        Trích xuất thông tin giao dịch cần xóa với Pydantic
        Returns: Dict với keys: food_item, price (optional), meal_time (optional)
        """
        
        if not self.llm:
            return self._fallback_delete_extraction(user_message)
        
        # Create Pydantic parser
        parser = PydanticOutputParser(pydantic_object=DeleteInfo)
        
        system_prompt = """
        Bạn là chuyên gia trích xuất thông tin giao dịch cần xóa từ câu chat.
        
        Phân tích câu chat và xác định:
        1. Có phải muốn xóa giao dịch gần nhất không
        2. Hoặc xóa giao dịch cụ thể (theo tên món, giá, thời gian)
        
        Từ khóa xóa gần nhất: "xóa", "gần nhất", "recent", hoặc để trống
        Từ khóa xóa cụ thể: tên món ăn, giá tiền, thời gian bữa ăn
        
        {format_instructions}
        """
        
        prompt_template = PromptTemplate(
            template=system_prompt + "\n\nCâu chat: '{user_message}'\n\nPhân tích:",
            input_variables=["user_message"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        try:
            # Gọi LLM với timeout
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("LLM timeout")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            
            # Timeout khác nhau cho từng provider
            current_model = get_current_model()
            model_settings = get_model_settings(current_model)
            provider = model_settings["provider"]
            
            if provider == "ollama":
                signal.alarm(15)  # 15 giây cho Ollama
            else:
                signal.alarm(5)   # 5 giây cho Google API
            
            try:
                # Create chain
                chain = prompt_template | self.llm | parser
                
                # Invoke chain  
                response = chain.invoke({"user_message": user_message})
                signal.alarm(0)
                
                # Convert to expected format
                result = {
                    'food_item': response.food_item,
                    'price': response.price,
                    'meal_time': response.meal_time,
                    'delete_recent': response.delete_recent,
                    'confidence': response.confidence,
                    'offline_mode': False
                }
                
                return result
                
            finally:
                signal.alarm(0)
            
        except Exception as e:
            error_msg = str(e)
            print(f"⚠️ Lỗi delete extraction: {error_msg[:50]}...")
            return self._fallback_delete_extraction(user_message)
    
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
    
    def _validate_and_fix_llm_result(self, result: Dict[str, Any], original_message: str) -> Dict[str, Any]:
        """
        Validate và fix kết quả từ LLM, với xử lý đặc biệt cho Pydantic results
        """
        
        # Validate và fix price (xử lý đơn vị k)
        if 'price' in result:
            price = result['price']
            # Nếu price quá nhỏ và message chứa 'k', có thể LLM đã miss đơn vị
            if price < 1000 and ('k' in original_message.lower() or 'K' in original_message):
                # Tìm số có 'k' trong message
                price_match = re.search(r'(\d+)k', original_message.lower())
                if price_match:
                    result['price'] = float(price_match.group(1)) * 1000
                    print(f"🔧 Fixed price: {price} → {result['price']}")
        
        # Đảm bảo food_item hợp lệ
        food_item = result.get('food_item', '')
        if not food_item or food_item.strip() == '':
            # Thử extract từ original message
            words = original_message.split()
            for word in words:
                if not re.match(r'^\d+[k.]?\d*[k]?$', word.lower()) and word.lower() not in ['ăn', 'uống', 'mua', 'cash', 'bank', 'ck', 'sáng', 'trưa', 'chiều', 'tối']:
                    result['food_item'] = word
                    break
            
            if not result.get('food_item'):
                result['food_item'] = 'giao dịch'
                if result.get('confidence', 0.8) > 0.5:
                    result['confidence'] = 0.5
        
        # Đảm bảo transaction_type hợp lệ
        transaction_type = result.get('transaction_type', 'expense')
        if transaction_type not in ['expense', 'income']:
            # Phân tích từ original message
            message_lower = original_message.lower()
            income_keywords = ['lãnh lương', 'nhận tiền', 'thu nhập', 'được trả', 'tiền thưởng', 'lương', 'salary']
            
            if any(keyword in message_lower for keyword in income_keywords):
                transaction_type = 'income'
            else:
                transaction_type = 'expense'
        
        result['transaction_type'] = transaction_type
        
        # Đảm bảo account_type hợp lệ
        account_type = result.get('account_type', 'cash')
        if account_type not in ['cash', 'account']:
            # Phân tích từ original message  
            message_lower = original_message.lower()
            account_keywords = ['tài khoản', 'ngân hàng', 'account', 'atm', 'banking', 'chuyển khoản', 'ck', 'bank']
            cash_keywords = ['tiền mặt', 'cash', 'tiền lẻ', 'tiền túi']
            
            if any(keyword in message_lower for keyword in account_keywords):
                account_type = 'account'
            elif any(keyword in message_lower for keyword in cash_keywords):
                account_type = 'cash'
            else:
                account_type = 'cash'
        
        result['account_type'] = account_type
        
        # Đảm bảo confidence trong khoảng hợp lệ
        confidence = result.get('confidence', 0.8)
        result['confidence'] = min(max(confidence, 0.2), 0.95)
        
        return result
    
    def _fallback_extraction(self, message: str) -> Dict[str, Any]:
        """Fallback rule-based extraction khi LLM thất bại"""
        result = {
            'food_item': '',
            'price': 0.0,
            'meal_time': None,
            'transaction_type': 'expense',  # Default
            'account_type': 'cash',  # Default
            'confidence': 0.3,  # Base confidence cho fallback
            'offline_mode': True  # Flag để nhận biết offline mode
        }
        
        message_lower = message.lower()
        confidence_boost = 0.0
        
        # Phân tích transaction_type
        income_keywords = ['lãnh', 'lương', 'nhận', 'thu', 'được', 'thưởng', 'salary', 'income', 'tiền lương']
        expense_keywords = ['ăn', 'uống', 'mua', 'chi', 'tiêu', 'trả', 'spend']
        
        if any(keyword in message_lower for keyword in income_keywords):
            result['transaction_type'] = 'income'
            confidence_boost += 0.1
        elif any(keyword in message_lower for keyword in expense_keywords):
            result['transaction_type'] = 'expense'
            confidence_boost += 0.1
        
        # Phân tích account_type - Enhanced for llama3 testing
        account_keywords = ['tài khoản', 'ngân hàng', 'account', 'atm', 'banking', 'chuyển khoản', 'vào tài khoản', 'ck', 'bank']
        cash_keywords = ['tiền mặt', 'cash', 'tiền lẻ', 'tiền túi']
        
        # Special handling for "ck" - must be account
        if 'ck' in message_lower or 'chuyển khoản' in message_lower:
            result['account_type'] = 'account'
            confidence_boost += 0.2  # High confidence for explicit keywords
        elif any(keyword in message_lower for keyword in account_keywords):
            result['account_type'] = 'account'
            confidence_boost += 0.1
        elif any(keyword in message_lower for keyword in cash_keywords):
            result['account_type'] = 'cash'
            confidence_boost += 0.1
        
        # Enhanced price parsing - Fixed for large numbers
        import re
        price_patterns = [
            r'(\d+)k\b',  # 35k, 5000k
            r'(\d+)000\b',  # 35000
            r'(\d+)\s*nghìn\b',  # 35 nghìn
            r'(\d+\.\d+)k\b',  # 35.5k
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, message_lower)
            if match:
                price_str = match.group(1)
                if 'k' in pattern or 'nghìn' in pattern:
                    # Fixed: Always multiply by 1000 for "k" suffix
                    result['price'] = float(price_str) * 1000
                else:
                    result['price'] = float(price_str)
                confidence_boost += 0.2  # Có giá tiền rõ ràng
                break
        
        # Tìm meal_time
        meal_patterns = {
            'sáng': ['sáng', 'buổi sáng'],
            'trưa': ['trưa', 'buổi trưa', 'lunch'],
            'chiều': ['chiều', 'buổi chiều', 'afternoon'],
            'tối': ['tối', 'buổi tối', 'dinner', 'supper']
        }
        
        for meal_time, keywords in meal_patterns.items():
            if any(keyword in message_lower for keyword in keywords):
                result['meal_time'] = meal_time
                confidence_boost += 0.15  # Có thời gian rõ ràng
                break
        
        # Tìm món ăn/mô tả giao dịch - enhanced logic
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
        
        # Strategy 2: Tìm mô tả cho giao dịch thu nhập
        if not result['food_item'] and result['transaction_type'] == 'income':
            income_descriptions = ['lương', 'thưởng', 'thu nhập', 'tiền lương', 'nhận tiền']
            for desc in income_descriptions:
                if desc in message_lower:
                    result['food_item'] = desc
                    confidence_boost += 0.15
                    break
        
        # Strategy 3: Nếu chưa tìm được, tìm từ có ý nghĩa
        if not result['food_item']:
            for word in words:
                word_clean = re.sub(r'\d+k?', '', word.lower()).strip()
                # Loại bỏ các từ thời gian và action
                skip_words = ['sáng', 'trưa', 'chiều', 'tối', 'ăn', 'uống', 'mua', 'order', 'gọi', 'buổi', 
                             'lãnh', 'nhận', 'từ', 'vào', 'tài', 'khoản', 'tiền', 'mặt']
                if word_clean not in skip_words and len(word_clean) > 2:
                    result['food_item'] = word_clean
                    confidence_boost += 0.1  # Có từ nhưng không chắc chắn
                    break
        
        # Strategy 4: Fallback - mô tả chung
        if not result['food_item']:
            if result['transaction_type'] == 'income':
                result['food_item'] = 'thu nhập'
            else:
                result['food_item'] = 'chi tiêu'
        
        # Điều chỉnh confidence dựa trên số lượng thông tin tìm được
        final_confidence = result['confidence'] + confidence_boost
        
        # Bonus cho input có format hoàn chỉnh
        if result['price'] > 0 and result['food_item'] not in ['thu nhập', 'chi tiêu']:
            if result['meal_time']:
                final_confidence += 0.1  # Perfect match: có đủ cả 3 yếu tố
            else:
                final_confidence += 0.05  # Good match: có món và giá
        
        # Đảm bảo confidence trong khoảng hợp lệ
        result['confidence'] = min(max(final_confidence, 0.2), 0.9)
        
        return result
    
    def _extract_balance_update_info(self, user_message: str) -> Optional[Dict[str, Any]]:
        """Trích xuất thông tin cập nhật số dư từ tin nhắn với Pydantic"""
        global _llm_available
        
        if not _llm_available or not self.llm:
            return self._fallback_balance_update(user_message)
        
        # Create Pydantic parser
        parser = PydanticOutputParser(pydantic_object=BalanceUpdate)
        
        system_prompt = """
        Bạn là chuyên gia phân tích câu lệnh cập nhật số dư tài chính.
        
        CÓ 2 LOẠI THAO TÁC:
        1. THIẾT LẬP (SET): Đặt số dư về một giá trị cụ thể
        2. CỘNG/TRỪ (ADD): Cộng/trừ vào số dư hiện tại
        
        PHÂN LOẠI THEO TỪ KHÓA:
        - SET: "cập nhật lại", "chỉ có", "là", "thành", "đặt lại", "reset"
        - ADD: "lãnh lương", "nhận tiền", "thu nhập", "chi tiêu", "mất tiền"
        
        {format_instructions}
        """
        
        prompt_template = PromptTemplate(
            template=system_prompt + "\n\nCâu chat: '{user_message}'\n\nPhân tích:",
            input_variables=["user_message"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        try:
            # Gọi LLM với timeout ngắn
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("LLM timeout")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            
            # Timeout khác nhau cho từng provider
            current_model = get_current_model()
            model_settings = get_model_settings(current_model)
            provider = model_settings["provider"]
            
            if provider == "ollama":
                signal.alarm(15)  # 15 giây cho Ollama
            else:
                signal.alarm(5)   # 5 giây cho Google API
            
            try:
                # Create chain
                chain = prompt_template | self.llm | parser
                
                # Invoke chain
                response = chain.invoke({"user_message": user_message})
                signal.alarm(0)
                
                # Convert to dict format expected by the rest of the system
                if response.is_balance_update:
                    return {
                        'operation_type': response.operation_type,
                        'cash_balance': response.cash_balance,
                        'account_balance': response.account_balance,
                        'cash_amount': response.cash_amount,
                        'account_amount': response.account_amount,
                        'description': response.description
                    }
                else:
                    return None
                    
            finally:
                signal.alarm(0)
                
        except Exception as e:
            error_msg = str(e)
            
            # Handle quota errors quietly (consistent với expense handling)
            if "quota" in error_msg.lower() or "429" in error_msg:
                if _llm_available:  # Only show once per session
                    print("⚠️ LLM quota exceeded")
                _llm_available = False
            elif "timeout" in error_msg.lower():
                # Handle timeout specifically
                if _llm_available:
                    print("⚠️ LLM timeout - chuyển sang fallback")
                _llm_available = False
            else:
                print(f"⚠️ Lỗi xử lý balance update: {error_msg[:50]}...")
                
            return self._fallback_balance_update(user_message)
    
    def _fallback_balance_update(self, message: str) -> Optional[Dict[str, float]]:
        """Fallback xử lý balance update cho chế độ offline"""
        message_lower = message.lower()
        
        # Kiểm tra có phải balance update không
        balance_keywords = ['cập nhật', 'update', 'tiền mặt', 'tài khoản', 'lãnh lương', 'nhận tiền', 'chi tiêu']
        if not any(keyword in message_lower for keyword in balance_keywords):
            return None
        
        # Phân loại operation type
        set_keywords = ['cập nhật lại', 'chỉ có', 'là', 'thành', 'đặt lại', 'reset', 'thiết lập']
        add_keywords = ['lãnh', 'lương', 'nhận', 'thu', 'được', 'thưởng', 'chi', 'tiêu', 'mất', 'trả']
        
        is_set_operation = any(keyword in message_lower for keyword in set_keywords)
        is_add_operation = any(keyword in message_lower for keyword in add_keywords)
        
        # Tìm số tiền
        import re
        amount = 0
        price_patterns = [r'(\d+)k\b', r'(\d+)000\b', r'(\d+)\s*nghìn\b', r'(\d+)\s*triệu\b']
        for pattern in price_patterns:
            match = re.search(pattern, message_lower)
            if match:
                amount_str = match.group(1)
                if 'triệu' in pattern:
                    amount = float(amount_str) * 1000000
                elif 'k' in pattern or 'nghìn' in pattern:
                    amount = float(amount_str) * 1000
                else:
                    amount = float(amount_str)
                break
        
        if amount <= 0:
            return None
        
        # Xác định loại tài khoản
        account_keywords = ['tài khoản', 'ngân hàng', 'account', 'atm', 'vào tài khoản']
        cash_keywords = ['tiền mặt', 'cash', 'tiền lẻ', 'tiền túi']
        
        is_account = any(keyword in message_lower for keyword in account_keywords)
        is_cash = any(keyword in message_lower for keyword in cash_keywords)
        
        balance_update = {}
        
        if is_set_operation:
            # Thiết lập số dư (SET)
            if is_account and not is_cash:
                balance_update['account_balance'] = amount
            elif is_cash and not is_account:
                balance_update['cash_balance'] = amount
            else:
                # Mặc định là tiền mặt nếu không rõ
                balance_update['cash_balance'] = amount
        else:
            # Cộng/trừ số dư (ADD)
            # Xác định cộng hay trừ
            income_keywords = ['lãnh', 'lương', 'nhận', 'thu', 'được', 'thưởng', 'cập nhật', 'còn', 'có']
            expense_keywords = ['chi', 'tiêu', 'mất', 'trả', 'spend']
            
            is_income = any(keyword in message_lower for keyword in income_keywords)
            is_expense = any(keyword in message_lower for keyword in expense_keywords)
            
            if is_expense and not is_income:
                amount = -amount  # Chi tiêu thì âm
            
            if is_account and not is_cash:
                balance_update['account_amount'] = amount
            elif is_cash and not is_account:
                balance_update['cash_amount'] = amount
            else:
                # Mặc định là tiền mặt nếu không rõ
                balance_update['cash_amount'] = amount
        
        return balance_update if balance_update else None
    
    def extract_statistics_info(self, user_message: str) -> Dict[str, Any]:
        """
        Trích xuất thông tin yêu cầu thống kê với Pydantic
        Returns: Dict với keys: period, specific_date, confidence
        """
        
        if not self.llm:
            return self._fallback_statistics_extraction(user_message)
        
        # Create Pydantic parser
        parser = PydanticOutputParser(pydantic_object=StatisticsInfo)
        
        system_prompt = """
        Bạn là chuyên gia trích xuất thông tin yêu cầu thống kê chi tiêu.
        
        Phân tích câu chat và xác định:
        1. Khoảng thời gian thống kê: daily, weekly, monthly
        2. Ngày cụ thể nếu có (định dạng YYYY-MM-DD)
        
        Từ khóa nhận biết:
        - "hôm nay", "today" → daily
        - "tuần", "week" → weekly  
        - "tháng", "month" → monthly
        
        {format_instructions}
        """
        
        prompt_template = PromptTemplate(
            template=system_prompt + "\n\nCâu chat: '{user_message}'\n\nPhân tích:",
            input_variables=["user_message"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        try:
            # Gọi LLM với timeout
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("LLM timeout")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            
            # Timeout khác nhau cho từng provider
            current_model = get_current_model()
            model_settings = get_model_settings(current_model)
            provider = model_settings["provider"]
            
            if provider == "ollama":
                signal.alarm(15)  # 15 giây cho Ollama
            else:
                signal.alarm(5)   # 5 giây cho Google API
            
            try:
                # Create chain
                chain = prompt_template | self.llm | parser
                
                # Invoke chain
                response = chain.invoke({"user_message": user_message})
                signal.alarm(0)
                
                # Convert to expected format
                result = {
                    'period': response.period,
                    'specific_date': response.specific_date,
                    'confidence': response.confidence,
                    'offline_mode': False
                }
                
                return result
                
            finally:
                signal.alarm(0)
            
        except Exception as e:
            error_msg = str(e)
            print(f"⚠️ Lỗi statistics extraction: {error_msg[:50]}...")
            return self._fallback_statistics_extraction(user_message)
    
    def _fallback_statistics_extraction(self, message: str) -> Dict[str, Any]:
        """Rule-based fallback cho statistics extraction"""
        message_lower = message.lower().strip()
        
        # Detect period
        if any(word in message_lower for word in ['hôm nay', 'today', 'daily']):
            period = 'daily'
            confidence = 0.8
        elif any(word in message_lower for word in ['tuần', 'week', 'weekly']):
            period = 'weekly' 
            confidence = 0.8
        elif any(word in message_lower for word in ['tháng', 'month', 'monthly']):
            period = 'monthly'
            confidence = 0.8
        else:
            period = 'daily'  # Default
            confidence = 0.5
        
        return {
            'period': period,
            'specific_date': None,
            'confidence': confidence,
            'offline_mode': True
        } 