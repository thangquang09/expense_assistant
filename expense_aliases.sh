#!/bin/bash

# Expense Tracker Aliases
# Thêm vào ~/.bashrc để sử dụng:
# source ~/CODE/ThangQ_Assistant/expense_aliases.sh

# Lấy đường dẫn thư mục script
EXPENSE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Alias chính
alias expense="$EXPENSE_DIR/run_app.sh"

# Quick add aliases
alias ea="$EXPENSE_DIR/run_app.sh -a"          # expense add
alias eadd="$EXPENSE_DIR/run_app.sh -a"        # expense add (alternative)

# Quick delete aliases
alias ed="$EXPENSE_DIR/run_app.sh -d"          # expense delete
alias edel="$EXPENSE_DIR/run_app.sh -d"        # expense delete (alternative)

# Statistics aliases  
alias esd="$EXPENSE_DIR/run_app.sh -sd"        # expense stats daily
alias esw="$EXPENSE_DIR/run_app.sh -sw"        # expense stats weekly
alias esm="$EXPENSE_DIR/run_app.sh -sm"        # expense stats monthly

# Functions for more convenient usage
function expense_add() {
    if [ $# -eq 0 ]; then
        echo "Usage: expense_add \"trưa ăn phở 30k\""
        return 1
    fi
    "$EXPENSE_DIR/run_app.sh" -a "$*"
}

function expense_delete() {
    if [ $# -eq 0 ]; then
        echo "Usage: expense_delete \"xóa phở\" hoặc \"phở\""
        return 1
    fi
    "$EXPENSE_DIR/run_app.sh" -d "$*"
}

function expense_stats() {
    case "$1" in
        "today"|"hôm nay"|"day"|"d")
            "$EXPENSE_DIR/run_app.sh" -sd
            ;;
        "week"|"tuần"|"w")
            "$EXPENSE_DIR/run_app.sh" -sw
            ;;
        "month"|"tháng"|"m")
            "$EXPENSE_DIR/run_app.sh" -sm
            ;;
        *)
            echo "Usage: expense_stats [today/week/month]"
            echo "       expense_stats [d/w/m]"
            echo "       expense_stats [hôm nay/tuần/tháng]"
            ;;
    esac
}

# Help function
function expense_help() {
    echo "🤖 EXPENSE TRACKER CLI COMMANDS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "📱 INTERACTIVE MODE:"
    echo "  expense                     # Mở ứng dụng interactive"
    echo ""
    echo "➕ QUICK ADD:"
    echo "  expense -a \"trưa ăn phở 30k\"  # Thêm chi tiêu nhanh"
    echo "  ea \"sáng uống cà phê 25k\"     # Alias ngắn gọn"
    echo "  expense_add trưa ăn cơm 40k   # Function (không cần quotes)"
    echo ""
    echo "🗑️ QUICK DELETE:"
    echo "  expense -d \"xóa phở\"          # Xóa giao dịch nhanh"
    echo "  expense -d                    # Xóa giao dịch gần nhất"
    echo "  ed \"xóa phở 30k\"              # Alias ngắn gọn"
    echo "  ed                            # Xóa giao dịch gần nhất"
    echo "  expense_delete phở            # Function (không cần quotes)"
    echo ""
    echo "📊 STATISTICS:"
    echo "  expense -sd                 # Thống kê hôm nay"
    echo "  expense -sw                 # Thống kê tuần này"
    echo "  expense -sm                 # Thống kê tháng này"
    echo "  esd / esw / esm            # Aliases ngắn"
    echo "  expense_stats today        # Function với từ khóa"
    echo "  expense_stats w            # Function với ký tự"
    echo ""
    echo "❓ HELP:"
    echo "  expense_help               # Hiển thị hướng dẫn này"
    echo ""
    echo "💡 EXAMPLES:"
    echo "  ea \"trưa ăn phở 35k\""
    echo "  expense_add chiều uống trà sữa 30k"
    echo "  ed \"xóa phở\""
    echo "  ed                            # Xóa giao dịch gần nhất"
    echo "  expense_delete cà phê"
    echo "  esd"
    echo "  expense_stats tuần"
    echo ""
}

echo "✅ Expense Tracker aliases loaded!"
echo "💡 Gõ 'expense_help' để xem hướng dẫn" 