# 📋 Google Sheets Setup Guide

## Bước 1: Cài đặt Dependencies

```bash
pip install gspread google-auth oauth2client
```

## Bước 2: Tạo Google Cloud Project

1. **Truy cập Google Cloud Console:**
   - Vào: https://console.developers.google.com/
   
2. **Tạo Project mới:**
   - Click "New Project"
   - Đặt tên project (VD: "Expense Tracker")
   - Click "Create"

3. **Enable APIs:**
   - Vào "API & Services" > "Library"
   - Tìm và enable "Google Sheets API"
   - Tìm và enable "Google Drive API"

## Bước 3: Tạo Service Account

1. **Vào IAM & Admin:**
   - "IAM & Admin" > "Service Accounts"
   
2. **Tạo Service Account:**
   - Click "Create Service Account"
   - Đặt tên: "expense-tracker-bot"
   - Mô tả: "Bot để sync dữ liệu expense tracker"
   - Click "Create and Continue"

3. **Thêm Role (tùy chọn):**
   - Có thể skip bước này cho app cá nhân
   - Click "Continue" > "Done"

## Bước 4: Tạo và Download Key

1. **Tạo Key:**
   - Click vào Service Account vừa tạo
   - Vào tab "Keys"
   - Click "Add Key" > "Create new key"
   - Chọn type "JSON"
   - Click "Create"

2. **Download và Setup:**
   - File JSON sẽ được download tự động
   - **Đổi tên file thành `credentials.json`**
   - **Copy vào folder app** (cùng thư mục với main.py)

## Bước 5: Test Connection

1. **Chạy app:**
   ```bash
   uv run main.py
   ```

2. **Kiểm tra status:**
   - Vào Menu 5 (Google Sheets)
   - Sẽ thấy trạng thái "✅ Đã kích hoạt"

3. **Test connection:**
   - Chọn "Test kết nối" để verify

## Bước 6: Sử dụng

### Auto Sync:
- Mỗi giao dịch mới tự động sync
- Balance updates tự động sync
- Statistics tự động sync

### Manual Export:
- Menu 5 > "Export toàn bộ dữ liệu"
- Backup toàn bộ database lên Sheets

### Xem Spreadsheet:
- Menu 5 > "Mở Spreadsheet (URL)"
- Copy URL để mở trong browser

## 📊 Worksheets Structure

### Transactions Sheet:
| ID | Date | Time | Food Item | Price | Meal Time | Created At | Sync Date |

### Balance Sheet:
| Date | Cash Balance | Account Balance | Total | Notes |

### Statistics Sheet:
| Date | Period | Transaction Count | Total Spent | Avg Spent | Min Spent | Max Spent | Generated At |

## 🔒 Security Notes

- **credentials.json** chứa thông tin nhạy cảm
- **Không share** file này với ai
- **Thêm vào .gitignore** nếu push code lên Git
- Service Account chỉ có thể access spreadsheet nó tạo

## 🛠️ Troubleshooting

### Lỗi "Không tìm thấy credentials.json":
- Kiểm tra file có đúng tên không
- Kiểm tra file có trong folder app không

### Lỗi "Permission denied":
- Kiểm tra APIs đã enable chưa
- Kiểm tra credentials file có đúng format không

### Lỗi "Quotas exceeded":
- Google Sheets API có giới hạn
- Đợi một lúc rồi thử lại

### Sync không hoạt động:
- Kiểm tra internet connection
- Test connection trong menu
- Restart app

## 🎯 Best Practices

1. **Backup định kỳ:**
   - Export manual hàng tuần
   
2. **Không edit trực tiếp trên Sheets:**
   - App là source of truth
   - Dùng Sheets để view/analyze
   
3. **Share với team:**
   - Share spreadsheet với email khác để collaborative
   
4. **Charts/Analytics:**
   - Tạo charts trong Sheets để visualize data
   - Pivot tables để phân tích trend 