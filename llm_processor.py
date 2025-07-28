#!/usr/bin/env python3
"""
LLM Processor for Expense Tracker
Handles LLM-based parsing with Pydantic schemas
"""

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
                    temperature=0.1
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
        """Khởi tạo LLM processor"""
        global _llm_available
        
        # Kiểm tra global flag trước
        if not _llm_available:
            self.llm = None
            return
            
        try:
            # Test connection nhanh trước khi khởi tạo LLM
            if not self._test_connection():
                print("⚠️ Không có kết nối internet - chuyển sang chế độ offline")
                _llm_available = False
                self.llm = None
                return
            
            # Sử dụng hàm create_llm_instance chung
            self.llm = create_llm_instance()
            
            if self.llm is None:
                _llm_available = False
                
        except Exception as e:
            print(f"⚠️ Lỗi khởi tạo QueryAnalyzer: {e} - chuyển sang chế độ offline")
            _llm_available = False
            self.llm = None
    
    def _test_connection(self) -> bool:
        """Test kết nối internet nhanh"""
        try:
            import requests
            requests.get("https://www.google.com", timeout=2)
            return True
        except:
            return False
    
    def analyze_intent(self, user_message: str) -> Dict[str, Any]:
        """
        Phân tích intent của user message với LLM
        Returns: Dict với keys: intent, confidence, analysis
        """
        global _llm_available
        
        if not _llm_available or not self.llm:
            return self._fallback_intent_analysis(user_message)
        
        # Create Pydantic parser
        parser = PydanticOutputParser(pydantic_object=IntentAnalysis)
        
        system_prompt = """
        Bạn là chuyên gia phân tích intent từ câu chat tiếng Việt.
        
        Phân loại intent:
        - "add_expense": thêm chi tiêu, ăn, uống, mua, chi tiêu, trả tiền
        - "delete_expense": xóa, hủy, xoá giao dịch
        - "update_balance": cập nhật số dư, set balance, thêm tiền vào tài khoản
        - "view_statistics": thống kê, xem báo cáo, tổng kết
        - "unknown": không rõ ràng
        
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
            
            # Invoke chain - NO timeout
            response = chain.invoke({"user_message": user_message})
            
            # Convert Pydantic model to dict
            result = {
                'intent': response.intent,
                'confidence': response.confidence,
                'analysis': response.analysis,
                'offline_mode': False
            }
            
            return result
                
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
            return self._fallback_intent_analysis(user_message)
    
    def _fallback_intent_analysis(self, message: str) -> Dict[str, Any]:
        """Fallback rule-based intent analysis khi LLM thất bại"""
        message_lower = message.lower()
        
        # Simple keyword-based intent detection
        if any(word in message_lower for word in ['xóa', 'xoá', 'hủy', 'delete']):
            intent = 'delete_expense'
            confidence = 0.8
        elif any(word in message_lower for word in ['thống kê', 'statistic', 'báo cáo', 'tổng kết']):
            intent = 'view_statistics'
            confidence = 0.8
        elif any(word in message_lower for word in ['số dư', 'balance', 'tài khoản', 'set']):
            intent = 'update_balance'
            confidence = 0.7
        elif any(word in message_lower for word in ['ăn', 'uống', 'mua', 'chi tiêu', 'trả tiền']):
            intent = 'add_expense'
            confidence = 0.9
        else:
            intent = 'add_expense'  # Default to expense
            confidence = 0.5
        
        return {
            'intent': intent,
            'confidence': confidence,
            'analysis': f'Rule-based detection: {intent}',
            'offline_mode': True
        }

class ExpenseExtractor:
    def __init__(self):
        """Khởi tạo LLM processor"""
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
            # Create chain
            chain = prompt_template | self.llm | parser
            
            # Invoke chain - NO timeout
            response = chain.invoke({"user_message": user_message})
            
            # Convert Pydantic model to dict
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
            # Create chain
            chain = prompt_template | self.llm | parser
            
            # Invoke chain - NO timeout
            response = chain.invoke({"user_message": user_message})
            
            # Convert Pydantic model to dict
            result = {
                'food_item': response.food_item,
                'price': response.price,
                'meal_time': response.meal_time,
                'delete_recent': response.delete_recent,
                'confidence': response.confidence,
                'offline_mode': False
            }
            
            return result
                
        except Exception as e:
            error_msg = str(e)
            print(f"⚠️ Lỗi khi gọi LLM: {error_msg[:50]}...")
            return self._fallback_delete_extraction(user_message)
    
    def _fallback_delete_extraction(self, message: str) -> Dict[str, Any]:
        """Fallback rule-based delete extraction khi LLM thất bại"""
        message_lower = message.lower()
        
        # Simple keyword-based detection
        if any(word in message_lower for word in ['xóa', 'xoá', 'hủy', 'delete']):
            if any(word in message_lower for word in ['gần nhất', 'recent', 'cuối']):
                return {
                    'food_item': None,
                    'price': None,
                    'meal_time': None,
                    'delete_recent': True,
                    'confidence': 0.8,
                    'offline_mode': True
                }
            else:
                # Try to extract specific info
                return {
                    'food_item': None,
                    'price': None,
                    'meal_time': None,
                    'delete_recent': True,  # Default to recent
                    'confidence': 0.6,
                    'offline_mode': True
                }
        
        return {
            'food_item': None,
            'price': None,
            'meal_time': None,
            'delete_recent': False,
            'confidence': 0.3,
            'offline_mode': True
        }
    
    def _validate_and_fix_llm_result(self, result: Dict[str, Any], original_message: str) -> Dict[str, Any]:
        """Validate và fix kết quả từ LLM"""
        
        # Validate price (xử lý đơn vị k)
        if 'price' in result:
            price = result['price']
            # Nếu price quá nhỏ và message chứa 'k', có thể LLM đã miss đơn vị
            if price < 1000 and ('k' in original_message.lower() or 'K' in original_message):
                # Tìm số có 'k' trong message
                price_match = re.search(r'(\d+)k', original_message.lower())
                if price_match:
                    result['price'] = float(price_match.group(1)) * 1000
                    print(f"🔧 Fixed price: {price} → {result['price']}")
        
        # Validate account_type for "ck" keyword
        if 'account_type' in result and 'ck' in original_message.lower():
            if result['account_type'] != 'account':
                result['account_type'] = 'account'
                print(f"🔧 Fixed account_type: {result['account_type']} → account (ck detected)")
        
        return result
    
    def _fallback_extraction(self, message: str) -> Dict[str, Any]:
        """Fallback rule-based extraction khi LLM thất bại"""
        result = {
            'food_item': '',
            'price': 0.0,
            'meal_time': None,
            'transaction_type': 'expense',
            'account_type': 'cash',
            'confidence': 0.3,
            'offline_mode': True
        }
        
        message_lower = message.lower()
        confidence_boost = 0.0
        
        # Phân tích transaction_type
        income_keywords = ['lãnh lương', 'nhận tiền', 'thu nhập', 'được trả', 'tiền thưởng', 'tiền lương']
        if any(keyword in message_lower for keyword in income_keywords):
            result['transaction_type'] = 'income'
            confidence_boost += 0.2
        
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
        
        # Tìm món ăn/mô tả giao dịch
        words = message.split()
        for word in words:
            word_clean = re.sub(r'\d+k?', '', word.lower()).strip()
            # Loại bỏ các từ thời gian và action
            skip_words = ['sáng', 'trưa', 'chiều', 'tối', 'ăn', 'uống', 'mua', 'ck', 'bank', 'cash']
            if word_clean not in skip_words and len(word_clean) > 2:
                result['food_item'] = word_clean
                confidence_boost += 0.1
                break
        
        if not result['food_item']:
            if result['transaction_type'] == 'income':
                result['food_item'] = 'lương'
            else:
                result['food_item'] = 'chi tiêu'
        
        # Phân tích meal_time
        meal_time_keywords = {
            'sáng': 'sáng',
            'trưa': 'trưa', 
            'chiều': 'chiều',
            'tối': 'tối'
        }
        
        for keyword, meal_time in meal_time_keywords.items():
            if keyword in message_lower:
                result['meal_time'] = meal_time
                confidence_boost += 0.1
                break
        
        # Cập nhật confidence
        result['confidence'] = min(0.9, 0.3 + confidence_boost)
        
        return result
    
    def _extract_balance_update_info(self, user_message: str) -> Optional[Dict[str, Any]]:
        """
        Trích xuất thông tin cập nhật số dư với Pydantic
        Returns: Dict với balance info hoặc None
        """
        
        if not self.llm:
            return self._fallback_balance_update(user_message)
        
        # Create Pydantic parser
        parser = PydanticOutputParser(pydantic_object=BalanceUpdate)
        
        system_prompt = """
        Bạn là chuyên gia trích xuất thông tin cập nhật số dư từ câu chat.
        
        Phân tích:
        1. Có phải muốn cập nhật số dư không
        2. Loại operation: SET (đặt số dư cụ thể) hoặc ADD (thêm/bớt)
        3. Số tiền cho cash và account
        
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
            
            # Invoke chain - NO timeout
            response = chain.invoke({"user_message": user_message})
            
            # Convert Pydantic model to dict
            result = {
                'is_balance_update': response.is_balance_update,
                'operation_type': response.operation_type,
                'cash_balance': response.cash_balance,
                'account_balance': response.account_balance,
                'cash_amount': response.cash_amount,
                'account_amount': response.account_amount,
                'description': response.description,
                'offline_mode': False
            }
            
            return result if result['is_balance_update'] else None
                
        except Exception as e:
            error_msg = str(e)
            print(f"⚠️ Lỗi khi gọi LLM: {error_msg[:50]}...")
            return self._fallback_balance_update(user_message)
    
    def _fallback_balance_update(self, message: str) -> Optional[Dict[str, float]]:
        """Fallback rule-based balance update extraction"""
        message_lower = message.lower()
        
        # Simple keyword detection
        balance_keywords = ['số dư', 'balance', 'tài khoản', 'set']
        if not any(keyword in message_lower for keyword in balance_keywords):
            return None
        
        # Try to extract amounts
        import re
        amounts = re.findall(r'(\d+)k', message_lower)
        if amounts:
            amount = float(amounts[0]) * 1000
            return {
                'is_balance_update': True,
                'operation_type': 'set',
                'cash_balance': amount,
                'account_balance': None,
                'cash_amount': None,
                'account_amount': None,
                'description': f'Set balance to {amount}',
                'offline_mode': True
            }
        
        return None
    
    def extract_statistics_info(self, user_message: str) -> Dict[str, Any]:
        """
        Trích xuất thông tin thống kê với Pydantic
        Returns: Dict với period và specific_date
        """
        
        if not self.llm:
            return self._fallback_statistics_extraction(user_message)
        
        # Create Pydantic parser
        parser = PydanticOutputParser(pydantic_object=StatisticsInfo)
        
        system_prompt = """
        Bạn là chuyên gia trích xuất thông tin thống kê từ câu chat.
        
        Phân tích:
        1. Period: daily, weekly, monthly
        2. Specific date nếu có
        
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
            
            # Invoke chain - NO timeout
            response = chain.invoke({"user_message": user_message})
            
            # Convert Pydantic model to dict
            result = {
                'period': response.period,
                'specific_date': response.specific_date,
                'confidence': response.confidence,
                'offline_mode': False
            }
            
            return result
                
        except Exception as e:
            error_msg = str(e)
            print(f"⚠️ Lỗi khi gọi LLM: {error_msg[:50]}...")
            return self._fallback_statistics_extraction(user_message)
    
    def _fallback_statistics_extraction(self, message: str) -> Dict[str, Any]:
        """Fallback rule-based statistics extraction"""
        message_lower = message.lower()
        
        # Simple keyword detection
        if 'tuần' in message_lower or 'week' in message_lower:
            period = 'weekly'
        elif 'tháng' in message_lower or 'month' in message_lower:
            period = 'monthly'
        else:
            period = 'daily'  # Default
        
        return {
            'period': period,
            'specific_date': None,
            'confidence': 0.7,
            'offline_mode': True
        } 