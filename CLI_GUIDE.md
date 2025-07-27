# 🤖 Expense Tracker CLI Guide

## 🚀 Setup Nhanh

### 1. **Thêm alias cơ bản (đã làm):**
```bash
echo 'alias expense="~/CODE/ThangQ_Assistant/run_app.sh"' >> ~/.bashrc
source ~/.bashrc
```

### 2. **Thêm tất cả aliases nâng cao (khuyến nghị):**
```bash
echo 'source ~/CODE/ThangQ_Assistant/expense_aliases.sh' >> ~/.bashrc
source ~/.bashrc
```

---

## 📖 Cách Sử Dụng

### 🎯 **Interactive Mode (Như Cũ)**
```bash
expense                    # Mở ứng dụng giao diện
```

### ➕ **Quick Add - Thêm Chi Tiêu Nhanh**

#### **Cách 1: Dùng flag -a**
```bash
expense -a "trưa ăn phở 30k"
expense -a "sáng uống cà phê 25k" 
expense -a "chiều mua bánh mì 15000"
expense -a "tối ăn cơm 45 nghìn"
```

#### **Cách 2: Dùng alias ngắn**
```bash
ea "trưa ăn phở 30k"       # ea = expense add
eadd "sáng cà phê 25k"     # alternative
```

#### **Cách 3: Dùng function (không cần quotes)**
```bash
expense_add trưa ăn phở 30k
expense_add sáng uống cà phê 25k
```

### 🗑️ **Quick Delete - Xóa Giao Dịch Nhanh**

#### **Cách 1: Dùng flag -d**
```bash
expense -d "xóa phở"       # Xóa giao dịch phở gần nhất
expense -d "xóa phở 30k"   # Xóa phở với giá cụ thể
expense -d                 # Xóa giao dịch gần nhất (mới!)
expense -d "xóa"           # Xóa giao dịch gần nhất
expense -d "gần nhất"      # Xóa giao dịch gần nhất
```

#### **Cách 2: Dùng alias ngắn**
```bash
ed "xóa phở"               # ed = expense delete
ed                         # Xóa giao dịch gần nhất (siêu nhanh!)
edel "xóa cà phê 25k"      # alternative
```

#### **Cách 3: Dùng function (không cần quotes)**
```bash
expense_delete xóa phở     # Function tiện lợi
expense_delete phở         # Có thể bỏ từ "xóa"
expense_delete ""          # Xóa giao dịch gần nhất
```

### 📊 **Statistics - Xem Thống Kê Nhanh**

#### **Cách 1: Dùng flags**
```bash
expense -sd                # Stats Daily (hôm nay)
expense -sw                # Stats Weekly (tuần này)  
expense -sm                # Stats Monthly (tháng này)
```

#### **Cách 2: Dùng aliases ngắn**
```bash
esd                        # Hôm nay
esw                        # Tuần này
esm                        # Tháng này
```

#### **Cách 3: Dùng function với từ khóa**
```bash
expense_stats today        # Hôm nay
expense_stats week         # Tuần này
expense_stats month        # Tháng này

# Hoặc với từ tiếng Việt
expense_stats "hôm nay"
expense_stats tuần
expense_stats tháng

# Hoặc với ký tự ngắn
expense_stats d            # day
expense_stats w            # week
expense_stats m            # month
```

---

## 🎪 **Workflow Thực Tế**

### **🌅 Buổi Sáng:**
```bash
ea "sáng ăn phở 35k"
esd                        # Check chi tiêu hôm nay
```

### **🌆 Cuối Ngày:**
```bash
ea "tối ăn cơm 50k"
esd                        # Xem tổng chi tiêu hôm nay
```

### **🗑️ Khi Cần Sửa/Xóa:**
```bash
ed                         # Xóa giao dịch gần nhất (siêu nhanh!)
ea "trưa ăn bún 40k"       # Thêm lại đúng
esd                        # Check lại thống kê

# Hoặc xóa cụ thể:
ed "xóa phở"               # Xóa giao dịch sai cụ thể
```

### **📅 Cuối Tuần:**
```bash
esw                        # Review chi tiêu tuần
```

### **📊 Cuối Tháng:**
```bash
esm                        # Review chi tiêu tháng
```

---

## 💡 **Tips & Tricks**

### **1. Batch Add (Thêm nhiều cùng lúc):**
```bash
ea "sáng ăn phở 35k" && ea "trưa uống cà phê 25k" && ea "chiều ăn bánh 15k"
```

### **2. Quick Check:**
```bash
# Thêm và xem ngay
ea "trưa ăn cơm 40k" && esd
```

### **3. Offline Mode Support:**
- ✅ Hoạt động ngay cả khi không có internet
- ✅ Nhận diện format chuẩn: `[thời gian] ăn/uống [món] [giá]`
- ✅ Hỗ trợ giá tiền: `30k`, `30000`, `30 nghìn`

### **4. Flexible Input:**
```bash
ea "phở 35k"               # Không cần thời gian
ea "trưa phở 35k"          # Không cần "ăn"
ea "trưa ăn phở 35000"     # Số đầy đủ
ea "trưa ăn phở 35 nghìn"  # Bằng chữ

# Delete shortcuts:
ed                         # Xóa giao dịch gần nhất
ed "xóa"                   # Tương tự như trên
ed "gần nhất"              # Tương tự như trên
```

---

## ⚠️ **Format Guide**

### **✅ ĐÚNG:**
```bash
ea "sáng ăn phở 30k"
ea "trưa uống cà phê 25000"
ea "chiều mua bánh mì 15k"
ea "tối ăn cơm 45 nghìn"
ea "phở 30k"                # Tối giản
```

### **❌ SAI:**
```bash
ea sáng ăn phở 30k          # Thiếu quotes
ea "ăn phở"                 # Thiếu giá
ea "30k phở"                # Sai thứ tự
```

---

## 🆘 **Help Commands**

```bash
expense_help               # Hướng dẫn đầy đủ
expense -h                 # CLI help
expense --help             # CLI help chi tiết
```

---

## 🎮 **Examples Thực Tế**

```bash
# Thêm bữa sáng
ea "sáng ăn phở bò 40k"

# Check ngay
esd

# Thêm bữa trưa
expense_add trưa ăn cơm gà 55k

# Thêm cafe chiều
ea "chiều uống cà phê 30k"

# Xem thống kê tuần
esw

# Thêm bữa tối và check luôn
ea "tối ăn bún riêu 45k" && esd
```

---

## 🚀 **Keyboard Shortcuts (sau khi setup aliases)**

| Command | Shortcut | Chức năng |
|---------|----------|-----------|
| `expense` | `expense` | Interactive mode |
| `expense -a "..."` | `ea "..."` | Quick add |
| `expense -d "..."` | `ed "..."` | Quick delete |
| `expense -sd` | `esd` | Stats daily |
| `expense -sw` | `esw` | Stats weekly |
| `expense -sm` | `esm` | Stats monthly |
| `expense_help` | `expense_help` | Help |

---

## 🎯 **Tính Năng Nổi Bật**

- ⚡ **Siêu nhanh**: Thêm chi tiêu trong < 2 giây
- 🔄 **Offline support**: Hoạt động không cần internet
- 📊 **Stats instant**: Xem thống kê ngay lập tức  
- 📋 **Auto sync**: Tự động sync Google Sheets (nếu có)
- 🎨 **Beautiful UI**: Giao diện đẹp với Rich library
- 🛡️ **Error handling**: Xử lý lỗi thông minh
- 💬 **Flexible input**: Nhận nhiều format khác nhau

---

Enjoy your supercharged expense tracking! 🚀✨ 