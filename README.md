# 🤖 Expense Tracker Assistant

Ứng dụng trợ lý theo dõi chi tiêu thông minh sử dụng AI để trích xuất thông tin từ câu chat tự nhiên.

## ✨ Tính năng

- 💬 **Chat tự nhiên**: Ghi chi tiêu bằng cách chat như "trưa ăn phở 35k"
- 🧠 **AI thông minh**: Sử dụng Google Gemini để trích xuất thông tin chi tiêu
- 💰 **Quản lý số dư**: Theo dõi tiền mặt và tài khoản ngân hàng riêng biệt
- 📊 **Báo cáo**: Thống kê chi tiêu theo thời gian
- 🗄️ **Lưu trữ local**: Dữ liệu lưu trong SQLite, bảo mật và nhanh chóng
- 🎨 **Giao diện đẹp**: Terminal UI với màu sắc và bố cục đẹp mắt

## 🚀 Cài đặt

### 1. Clone repository
```bash
git clone <repository-url>
cd ThangQ_Assistant
```

### 2. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 3. Thiết lập API key
Tạo file `.env` với nội dung:
```
GEMINI_API_KEY=your_gemini_api_key_here
```

**Lấy API key tại**: https://makersuite.google.com/app/apikey

### 4. Chạy ứng dụng
```bash
python main.py
```

## 📖 Hướng dẫn sử dụng

### 💬 Ghi chi tiêu
Sử dụng ngôn ngữ tự nhiên để ghi chi tiêu:

- `"trưa ăn phở 35k"` - Ghi chi tiêu có thời gian
- `"mua cà phê 25000"` - Ghi chi tiêu không có thời gian
- `"ăn bún chả 40 nghìn"` - Số tiền bằng chữ
- `"tối ăn cơm 50k"` - Bữa ăn + món + giá

### 💰 Cập nhật số dư
- `"cập nhật tiền mặt 500k"` - Cập nhật tiền mặt
- `"tài khoản còn 2 triệu"` - Cập nhật tài khoản ngân hàng
- `"tiền mặt 100k, tài khoản 1 triệu"` - Cập nhật cả hai

### 📊 Xem thông tin
- **Menu 2**: Xem số dư hiện tại
- **Menu 3**: Báo cáo chi tiêu theo thời gian
- **Menu 4**: Danh sách giao dịch gần đây

## 🏗️ Cấu trúc project

```
ThangQ_Assistant/
├── main.py              # File chính để chạy ứng dụng
├── chatbot.py           # Giao diện chatbot terminal
├── expense_tracker.py   # Logic xử lý chi tiêu
├── llm_processor.py     # Xử lý AI với Gemini
├── database.py          # Quản lý SQLite database
├── requirements.txt     # Dependencies
├── README.md           # Hướng dẫn
└── .env                # API keys (tạo thủ công)
```

## 🗄️ Database Schema

### Bảng `users`
- `id`: ID người dùng
- `name`: Tên người dùng
- `cash_balance`: Số dư tiền mặt
- `account_balance`: Số dư tài khoản
- `created_at`, `updated_at`: Timestamps

### Bảng `transactions`
- `id`: ID giao dịch
- `user_id`: ID người dùng
- `food_item`: Tên món ăn/uống
- `price`: Giá tiền
- `meal_time`: Thời gian ăn (sáng/trưa/chiều/tối)
- `transaction_date`: Ngày giao dịch
- `transaction_time`: Giờ giao dịch
- `created_at`: Timestamp tạo

## 🤖 AI Features

Ứng dụng sử dụng Google Gemini để:
- Trích xuất tên món ăn từ text tự nhiên
- Nhận diện giá tiền với nhiều format (35k, 35000, 35 nghìn)
- Xác định thời gian ăn (sáng, trưa, chiều, tối)
- Phân biệt lệnh cập nhật số dư vs ghi chi tiêu
- Fallback về rule-based parsing khi AI thất bại

## 💡 Tips

- Có thể viết "35k", "35000", "35 nghìn" đều được nhận diện
- Hệ thống tự động trừ tiền từ tài khoản trước, sau đó tiền mặt
- Dữ liệu được lưu tự động trong file SQLite
- Ứng dụng hoạt động offline sau khi cài đặt (chỉ cần internet cho AI calls)

## 🛠️ Phát triển tương lai

- [ ] Web interface với React/Vue
- [ ] Export báo cáo PDF/Excel
- [ ] Phân loại chi tiêu tự động
- [ ] Đồng bộ với nhiều thiết bị
- [ ] Nhắc nhở chi tiêu theo ngân sách
- [ ] Tích hợp với banking APIs

## 📝 License

MIT License - Xem file LICENSE để biết thêm chi tiết. 