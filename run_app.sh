#!/bin/bash

# Script để chạy Expense Tracker Assistant
# Sử dụng: ./run_app.sh

echo "🚀 Khởi động Expense Tracker Assistant..."

# Lấy đường dẫn thư mục hiện tại của script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Chuyển vào thư mục project
cd "$SCRIPT_DIR"

echo "📁 Thư mục hiện tại: $(pwd)"

# Kiểm tra xem uv đã được cài đặt chưa
if ! command -v uv &> /dev/null; then
    echo "❌ uv chưa được cài đặt. Vui lòng cài đặt uv trước:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ uv đã sẵn sàng"

# Kiểm tra file pyproject.toml
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Không tìm thấy pyproject.toml trong thư mục này"
    exit 1
fi

echo "✅ Project configuration OK"

# Sync dependencies nếu cần
echo "🔄 Đang sync dependencies..."
uv sync

# Chạy ứng dụng
echo "🎯 Khởi động ứng dụng..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
uv run main.py 