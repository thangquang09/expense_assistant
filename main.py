#!/usr/bin/env python3
"""
Expense Tracker Assistant - CLI + Interactive Mode
Usage:
  python main.py                          # Interactive mode
  python main.py -a "trưa ăn phở 30k"     # Quick add expense
  python main.py --append "..."           # Quick add expense
  python main.py -sd                      # Statistics daily
  python main.py -sw                      # Statistics weekly  
  python main.py -sm                      # Statistics monthly
"""

import sys
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from chatbot import ExpenseChatbot
from expense_tracker import ExpenseTracker


def create_parser():
    """Tạo argument parser cho CLI"""
    parser = argparse.ArgumentParser(
        description="🤖 Expense Tracker Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Interactive mode
  %(prog)s -a "trưa ăn phở 30k"         # Quick add expense
  %(prog)s --append "sáng uống cà phê 25k"
  %(prog)s -d "xóa phở"                 # Quick delete transaction
  %(prog)s -d                           # Delete most recent transaction
  %(prog)s --delete "xóa phở 30k"       # Delete with specific price
  %(prog)s -sd                          # Today's statistics
  %(prog)s -sw                          # This week's statistics
  %(prog)s -sm                          # This month's statistics
        """
    )
    
    # Quick operations group
    group = parser.add_mutually_exclusive_group()
    
    group.add_argument(
        '-a', '--append',
        metavar='EXPENSE',
        help='Quickly add an expense (e.g., "trưa ăn phở 30k")'
    )
    
    group.add_argument(
        '-d', '--delete',
        metavar='DELETE_QUERY',
        nargs='?',  # Make argument optional
        const='xóa',  # Default value when -d is used without argument
        help='Quickly delete a transaction (e.g., "xóa phở", "xóa phở 30k", or just -d to delete most recent)'
    )
    
    group.add_argument(
        '-sd', '--stats-daily',
        action='store_true',
        help='Show today\'s spending statistics'
    )
    
    group.add_argument(
        '-sw', '--stats-weekly', 
        action='store_true',
        help='Show this week\'s spending statistics'
    )
    
    group.add_argument(
        '-sm', '--stats-monthly',
        action='store_true', 
        help='Show this month\'s spending statistics'
    )
    
    return parser


def quick_delete_transaction(delete_query: str):
    """Xóa transaction nhanh từ command line"""
    console = Console()
    tracker = ExpenseTracker()
    
    # Xử lý trường hợp empty string hoặc chỉ có whitespace
    if not delete_query.strip():
        delete_query = "xóa"  # Convert empty to "xóa" keyword
        console.print("[yellow]🗑️ Xóa giao dịch gần nhất...[/yellow]")
    else:
        console.print(f"[yellow]🗑️ Đang xóa: {delete_query}[/yellow]")
    
    # Process the delete request
    result = tracker.process_user_message(delete_query)
    
    if result['success']:
        # Show success message
        message = result['message']
        console.print(f"[green]✅ {message}[/green]")
        
        # Show updated statistics if available
        if 'statistics' in result:
            stats = result['statistics']
            
            stats_table = Table(show_header=False, box=box.SIMPLE, border_style="red")
            stats_table.add_column("", style="red", width=20)
            stats_table.add_column("", style="yellow", justify="right", width=15)
            
            stats_table.add_row("🗑️ Đã xóa", f"{stats['deleted_amount']:,.0f}đ")
            stats_table.add_row("📅 Hôm nay còn", f"{stats['today_total']:,.0f}đ ({stats['today_count']} lần)")
            stats_table.add_row("📆 Tuần này còn", f"{stats['week_total']:,.0f}đ ({stats['week_count']} lần)")
            
            console.print(Panel(stats_table, title="🗑️ Thống kê sau khi xóa", border_style="red"))
        
        # Show deleted transaction info if available
        if 'deleted_transaction' in result:
            deleted = result['deleted_transaction']
            console.print(f"[dim]🗑️ Đã xóa: {deleted['food_item']} - {deleted['price']:,.0f}đ ({deleted.get('meal_time', 'N/A')})[/dim]")
        
        # Show sync/note info
        if result.get('note'):
            console.print(f"[yellow]💡 {result['note']}[/yellow]")
        elif result.get('offline_mode', False):
            console.print("[dim]🔴 Offline mode - Chưa sync[/dim]")
            
    else:
        # Show error
        console.print(f"[red]❌ {result['message']}[/red]")
        if 'suggestion' in result:
            console.print(f"[yellow]💡 {result['suggestion']}[/yellow]")
        
        # Show offline warning if applicable
        if result.get('offline_mode', False):
            console.print("[red]🔴 Chế độ offline - Vui lòng nhập rõ ràng hơn[/red]")


def quick_add_expense(expense_text: str):
    """Thêm expense nhanh từ command line"""
    console = Console()
    tracker = ExpenseTracker()
    
    console.print(f"[yellow]🔄 Đang thêm: {expense_text}[/yellow]")
    
    # Process the expense
    result = tracker.process_user_message(expense_text)
    
    if result['success']:
        # Show success message
        message = result['message']
        if result.get('synced_to_sheets', False):
            message += " 📋"
        console.print(f"[green]✅ {message}[/green]")
        
        # Show quick statistics if available
        if 'statistics' in result:
            stats = result['statistics']
            
            stats_table = Table(show_header=False, box=box.SIMPLE, border_style="cyan")
            stats_table.add_column("", style="cyan", width=20)
            stats_table.add_column("", style="yellow", justify="right", width=15)
            
            stats_table.add_row("🎯 Giao dịch này", f"{stats['this_transaction']:,.0f}đ")
            stats_table.add_row("📅 Hôm nay", f"{stats['today_total']:,.0f}đ ({stats['today_count']} lần)")
            stats_table.add_row("📆 Tuần này", f"{stats['week_total']:,.0f}đ ({stats['week_count']} lần)")
            
            console.print(Panel(stats_table, title="📊 Thống kê nhanh", border_style="cyan"))
        
        # Show sync info
        if result.get('synced_to_sheets', False):
            console.print("[dim]📋 Đã sync lên Google Sheets[/dim]")
        elif result.get('offline_mode', False):
            console.print("[dim]🔴 Offline mode - Chưa sync[/dim]")
            
    else:
        # Show error
        console.print(f"[red]❌ {result['message']}[/red]")
        if 'suggestion' in result:
            console.print(f"[yellow]💡 {result['suggestion']}[/yellow]")
        
        # Show offline warning if applicable
        if result.get('offline_mode', False):
            console.print("[red]🔴 Chế độ offline - Vui lòng nhập rõ ràng hơn[/red]")


def show_statistics(period: str):
    """Hiển thị thống kê nhanh"""
    console = Console()
    tracker = ExpenseTracker()
    
    # Map period to days and message
    period_config = {
        'daily': {'days': 1, 'title': 'HÔM NAY', 'emoji': '📅'},
        'weekly': {'days': 7, 'title': 'TUẦN NÀY', 'emoji': '📆'}, 
        'monthly': {'days': 30, 'title': 'THÁNG NÀY', 'emoji': '📊'}
    }
    
    config = period_config[period]
    console.print(f"[yellow]🔍 Lấy thống kê {config['title'].lower()}...[/yellow]")
    
    # Get statistics
    summary = tracker.db.get_spending_summary(tracker.current_user_id, config['days'])
    recent_transactions = tracker.db.get_recent_transactions(tracker.current_user_id, 5)
    balance = tracker.get_balance_summary()
    
    # Create main statistics table
    stats_table = Table(show_header=True, header_style="bold cyan", box=box.DOUBLE)
    stats_table.add_column(f"{config['emoji']} Thống kê", style="cyan", width=25)
    stats_table.add_column("Giá trị", style="green", justify="right", width=20)
    
    stats_table.add_row("📅 Thời gian", config['title'])
    stats_table.add_row("💸 Tổng chi tiêu", f"{summary['total_spent'] or 0:,.0f}đ")
    stats_table.add_row("🔢 Số giao dịch", f"{summary['transaction_count']} lần")
    
    if summary['transaction_count'] > 0:
        stats_table.add_row("📊 Trung bình/lần", f"{summary['avg_spent'] or 0:,.0f}đ")
        stats_table.add_row("📉 Thấp nhất", f"{summary['min_spent'] or 0:,.0f}đ")
        stats_table.add_row("📈 Cao nhất", f"{summary['max_spent'] or 0:,.0f}đ")
    
    console.print(Panel(stats_table, title=f"📊 THỐNG KÊ {config['title']}", border_style="cyan"))
    
    # Show balance
    balance_table = Table(show_header=False, box=box.SIMPLE, border_style="green")
    balance_table.add_column("", style="green", width=20)
    balance_table.add_column("", style="yellow", justify="right", width=15)
    
    balance_table.add_row("💵 Tiền mặt", f"{balance['cash_balance']:,.0f}đ")
    balance_table.add_row("🏦 Tài khoản", f"{balance['account_balance']:,.0f}đ")
    balance_table.add_row("💰 Tổng cộng", f"[bold]{balance['total_balance']:,.0f}đ[/bold]")
    
    console.print(Panel(balance_table, title="💰 SỐ DƯ HIỆN TẠI", border_style="green"))
    
    # Show recent transactions if any
    if recent_transactions and summary['transaction_count'] > 0:
        recent_table = Table(show_header=True, header_style="bold yellow", box=box.SIMPLE)
        recent_table.add_column("Ngày", style="yellow", width=12)
        recent_table.add_column("Món", style="green", width=15)
        recent_table.add_column("Giá", style="cyan", justify="right", width=12)
        recent_table.add_column("Bữa", style="magenta", width=8)
        
        # Show max 3 recent transactions
        for trans in recent_transactions[:3]:
            recent_table.add_row(
                trans['transaction_date'],
                trans['food_item'],
                f"{trans['price']:,.0f}đ",
                trans['meal_time'] or ""
            )
        
        console.print(Panel(recent_table, title="🕐 GIAO DỊCH GẦN ĐÂY", border_style="yellow"))


def main():
    """Main function với CLI support"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Handle CLI operations
    if args.append:
        quick_add_expense(args.append)
        return
    
    if args.delete:
        quick_delete_transaction(args.delete)
        return
    
    if args.stats_daily:
        show_statistics('daily')
        return
        
    if args.stats_weekly:
        show_statistics('weekly')
        return
        
    if args.stats_monthly:
        show_statistics('monthly') 
        return
    
    # Default: Start interactive mode
    try:
        chatbot = ExpenseChatbot()
        chatbot.start()
    except KeyboardInterrupt:
        console = Console()
        console.print("\n[yellow]👋 Đã thoát ứng dụng![/yellow]")
        sys.exit(0)
    except Exception as e:
        console = Console()
        console.print(f"[red]❌ Lỗi: {str(e)}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main() 