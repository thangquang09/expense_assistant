#!/usr/bin/env python3
"""
Expense Tracker Assistant
Ứng dụng trợ lý theo dõi chi tiêu với AI
"""

import sys
import os
from chatbot import ExpenseChatbot
from dotenv import load_dotenv

def main():
    """Main function để chạy ứng dụng"""
    try:
        # Kiểm tra file .env
        load_dotenv()
        if not os.path.exists('.env'):
            print("❌ Không tìm thấy file .env!")
            print("📝 Vui lòng tạo file .env với nội dung:")
            print("GEMINI_API_KEY=your_gemini_api_key_here")
            print("\n🔗 Lấy API key tại: https://makersuite.google.com/app/apikey")
            return
        
        # Khởi tạo và chạy chatbot

        chatbot = ExpenseChatbot()
        chatbot.start()
        
    except KeyboardInterrupt:
        print("\n👋 Đã hủy chương trình!")
    except Exception as e:
        print(f"❌ Lỗi khởi động: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 