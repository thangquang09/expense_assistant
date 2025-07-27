#!/bin/bash

# Script để chạy Expense Tracker Assistant với CLI support
# Sử dụng: 
#   ./run_app.sh                        # Interactive mode
#   ./run_app.sh -a "trưa ăn phở 30k"   # Quick add
#   ./run_app.sh -d "xóa phở"           # Quick delete
#   ./run_app.sh -sd                    # Stats daily
#   ./run_app.sh -sw                    # Stats weekly
#   ./run_app.sh -sm                    # Stats monthly

# Lấy đường dẫn thư mục hiện tại của script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Chuyển vào thư mục project
cd "$SCRIPT_DIR"

# Kiểm tra xem uv đã được cài đặt chưa
if ! command -v uv &> /dev/null; then
    echo "❌ uv chưa được cài đặt. Vui lòng cài đặt uv trước:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Kiểm tra file pyproject.toml
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Không tìm thấy pyproject.toml trong thư mục này"
    exit 1
fi

# Nếu không có arguments, hiển thị startup message
if [ $# -eq 0 ]; then
    echo "🚀 Khởi động Expense Tracker Assistant..."
    echo "📁 Thư mục hiện tại: $(pwd)"
    echo "✅ uv đã sẵn sàng"
    echo "✅ Project configuration OK"
    
    # Sync dependencies nếu cần cho interactive mode
    echo "🔄 Đang sync dependencies..."
    uv sync --quiet
    
    echo "🎯 Khởi động ứng dụng..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi

# Chạy ứng dụng với tất cả arguments được truyền vào
uv run main.py "$@" 