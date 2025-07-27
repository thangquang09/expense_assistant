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
import datetime


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
    """Hiển thị thống kê theo thời gian với giao diện cải tiến"""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    
    console = Console()
    
    try:
        tracker = ExpenseTracker()
        balance = tracker.db.get_user_balance()
        
        if period == "daily":
            console.print("🔍 Lấy thống kê hôm nay...")
            
            # Lấy tổng thống kê ngày
            summary = tracker.db.get_spending_summary(1, 1)
            
            # Lấy TẤT CẢ giao dịch trong ngày
            daily_transactions = tracker.db.get_daily_transactions()
            
            # Tạo bảng thống kê tổng quan
            stats_table = Table(box=box.DOUBLE_EDGE)
            stats_table.add_column("📅 Thống kê", style="cyan")
            stats_table.add_column("Giá trị", style="green", justify="right")
            
            stats_table.add_row("📅 Thời gian", "HÔM NAY")
            stats_table.add_row("💸 Tổng chi tiêu", f"{summary['total_spent']:,.0f}đ" if summary['total_spent'] else "0đ")
            stats_table.add_row("🔢 Số giao dịch", f"{summary['transaction_count']} lần")
            
            if summary['transaction_count'] > 0:
                avg = summary['total_spent'] / summary['transaction_count']
                stats_table.add_row("📊 Trung bình/lần", f"{avg:,.0f}đ")
                stats_table.add_row("📉 Thấp nhất", f"{summary['min_spent']:,.0f}đ")
                stats_table.add_row("📈 Cao nhất", f"{summary['max_spent']:,.0f}đ")
            
            console.print(Panel(stats_table, title="📊 THỐNG KÊ HÔM NAY", padding=(1, 2)))
            
            # Hiển thị số dư
            balance_content = f"""💵 Tiền mặt                 {balance['cash_balance']:,.0f}đ
🏦 Tài khoản                {balance['account_balance']:,.0f}đ
💰 Tổng cộng                {balance['cash_balance'] + balance['account_balance']:,.0f}đ"""
            
            console.print(Panel(balance_content, title="💰 SỐ DƯ HIỆN TẠI", padding=(1, 3)))
            
            # Hiển thị TẤT CẢ giao dịch trong ngày
            if daily_transactions:
                transaction_table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
                transaction_table.add_column("Thời gian", style="dim")
                transaction_table.add_column("Món", style="cyan")
                transaction_table.add_column("Giá", style="green", justify="right")
                transaction_table.add_column("Bữa", style="yellow")
                transaction_table.add_column("Loại", style="blue")
                
                for trans in daily_transactions:
                    meal_time = trans['meal_time'] if trans['meal_time'] else ""
                    trans_type = "💰" if trans['transaction_type'] == 'income' else "💸"
                    account_type = "🏦" if trans['account_type'] == 'account' else "💵"
                    
                    transaction_table.add_row(
                        trans['transaction_time'][:5] if trans['transaction_time'] else "",  # HH:MM
                        trans['food_item'],
                        f"{trans['price']:,.0f}đ",
                        meal_time,
                        f"{trans_type}{account_type}"
                    )
                
                console.print(Panel(transaction_table, title="🕐 TẤT CẢ GIAO DỊCH HÔM NAY", padding=(1, 2)))
            else:
                console.print(Panel("Chưa có giao dịch nào hôm nay", title="🕐 GIAO DỊCH HÔM NAY", padding=(1, 2)))
                
        elif period == "weekly":
            console.print("📅 Lấy thống kê tuần...")
            
            # Lấy tổng thống kê tuần
            summary = tracker.db.get_spending_summary(1, 7)
            weekly_data = tracker.db.get_weekly_summary_by_days(1, 7)
            
            # Bảng tổng quan
            stats_table = Table(box=box.DOUBLE_EDGE)
            stats_table.add_column("📅 Thống kê", style="cyan")
            stats_table.add_column("Giá trị", style="green", justify="right")
            
            stats_table.add_row("📅 Thời gian", "7 NGÀY QUA")
            stats_table.add_row("💸 Tổng chi tiêu", f"{summary['total_spent']:,.0f}đ" if summary['total_spent'] else "0đ")
            stats_table.add_row("🔢 Số giao dịch", f"{summary['transaction_count']} lần")
            
            if summary['transaction_count'] > 0:
                avg = summary['total_spent'] / summary['transaction_count']
                stats_table.add_row("📊 Trung bình/lần", f"{avg:,.0f}đ")
            
            console.print(Panel(stats_table, title="📊 THỐNG KÊ TUẦN", padding=(1, 2)))
            
            # Bảng chi tiết theo từng ngày
            daily_table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
            daily_table.add_column("Ngày", style="cyan")
            daily_table.add_column("Chi tiêu", style="red", justify="right")
            daily_table.add_column("Thu nhập", style="green", justify="right")
            daily_table.add_column("Giao dịch", style="blue", justify="center")
            
            for day_data in weekly_data:
                date_obj = datetime.datetime.strptime(day_data['date'], '%Y-%m-%d')
                date_display = date_obj.strftime('%d/%m (%a)')
                
                daily_table.add_row(
                    date_display,
                    f"{day_data['total_expense']:,.0f}đ" if day_data['total_expense'] > 0 else "-",
                    f"{day_data['total_income']:,.0f}đ" if day_data['total_income'] > 0 else "-",
                    f"{day_data['transaction_count']} lần"
                )
            
            console.print(Panel(daily_table, title="📈 CHI TIẾT THEO NGÀY", padding=(1, 2)))
            
            # Hiển thị số dư
            balance_content = f"""💵 Tiền mặt                 {balance['cash_balance']:,.0f}đ
🏦 Tài khoản                {balance['account_balance']:,.0f}đ
💰 Tổng cộng                {balance['cash_balance'] + balance['account_balance']:,.0f}đ"""
            
            console.print(Panel(balance_content, title="💰 SỐ DƯ HIỆN TẠI", padding=(1, 3)))
            
        elif period == "monthly":
            console.print("📅 Lấy thống kê tháng...")
            
            # Lấy tổng thống kê tháng
            summary = tracker.db.get_spending_summary(1, 30)
            weekly_data = tracker.db.get_monthly_summary_by_weeks()
            
            # Bảng tổng quan
            stats_table = Table(box=box.DOUBLE_EDGE)
            stats_table.add_column("📅 Thống kê", style="cyan")
            stats_table.add_column("Giá trị", style="green", justify="right")
            
            stats_table.add_row("📅 Thời gian", "30 NGÀY QUA")
            stats_table.add_row("💸 Tổng chi tiêu", f"{summary['total_spent']:,.0f}đ" if summary['total_spent'] else "0đ")
            stats_table.add_row("🔢 Số giao dịch", f"{summary['transaction_count']} lần")
            
            if summary['transaction_count'] > 0:
                avg = summary['total_spent'] / summary['transaction_count']
                stats_table.add_row("📊 Trung bình/lần", f"{avg:,.0f}đ")
            
            console.print(Panel(stats_table, title="📊 THỐNG KÊ THÁNG", padding=(1, 2)))
            
            # Bảng theo tuần
            weekly_table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
            weekly_table.add_column("Tuần", style="cyan")
            weekly_table.add_column("Khoảng thời gian", style="dim")
            weekly_table.add_column("Chi tiêu", style="red", justify="right")
            weekly_table.add_column("Thu nhập", style="green", justify="right")
            weekly_table.add_column("Giao dịch", style="blue", justify="center")
            
            for week_data in weekly_data:
                start_date = datetime.datetime.strptime(week_data['start_date'], '%Y-%m-%d').strftime('%d/%m')
                end_date = datetime.datetime.strptime(week_data['end_date'], '%Y-%m-%d').strftime('%d/%m')
                
                weekly_table.add_row(
                    f"Tuần {week_data['week_num']}",
                    f"{start_date} - {end_date}",
                    f"{week_data['total_expense']:,.0f}đ" if week_data['total_expense'] > 0 else "-",
                    f"{week_data['total_income']:,.0f}đ" if week_data['total_income'] > 0 else "-",
                    f"{week_data['transaction_count']} lần"
                )
            
            console.print(Panel(weekly_table, title="📈 CHI TIẾT THEO TUẦN", padding=(1, 2)))
            
            # Hỏi có muốn xem chi tiết 30 ngày + biểu đồ không
            try:
                choice = input("\n📊 Bạn có muốn xem chi tiết 30 ngày + biểu đồ không? (y/n): ").strip().lower()
                
                if choice in ['y', 'yes', 'có']:
                    console.print("📊 Đang tạo biểu đồ chi tiết...")
                    show_monthly_chart(tracker)
                    
                    # Hiển thị chi tiết tháng hiện tại
                    monthly_data = tracker.db.get_current_month_summary_by_days(1)
                    
                    console.print(f"\n📅 Chi tiết từng ngày trong tháng {datetime.datetime.now().month}/{datetime.datetime.now().year}:")
                    
                    # Hiển thị 10 ngày một lần để không quá dài
                    for i in range(0, len(monthly_data), 10):
                        chunk = monthly_data[i:i+10]
                        
                        daily_table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
                        daily_table.add_column("Ngày", style="cyan")
                        daily_table.add_column("Chi tiêu", style="red", justify="right")
                        daily_table.add_column("Thu nhập", style="green", justify="right")
                        daily_table.add_column("GD", style="blue", justify="center")
                        
                        for day_data in chunk:
                            date_obj = datetime.datetime.strptime(day_data['date'], '%Y-%m-%d')
                            date_display = date_obj.strftime('%d/%m (%a)')
                            
                            daily_table.add_row(
                                date_display,
                                f"{day_data['total_expense']:,.0f}đ" if day_data['total_expense'] > 0 else "-",
                                f"{day_data['total_income']:,.0f}đ" if day_data['total_income'] > 0 else "-",
                                str(day_data['transaction_count']) if day_data['transaction_count'] > 0 else "-"
                            )
                        
                        start_day = i + 1
                        end_day = min(i + 10, len(monthly_data))
                        title = f"📅 NGÀY {start_day}-{end_day} TRONG THÁNG"
                        console.print(Panel(daily_table, title=title, padding=(1, 2)))
                
            except (EOFError, KeyboardInterrupt):
                console.print("\n💡 Đã bỏ qua chi tiết 30 ngày")
            
            # Hiển thị số dư
            balance_content = f"""💵 Tiền mặt                 {balance['cash_balance']:,.0f}đ
🏦 Tài khoản                {balance['account_balance']:,.0f}đ
💰 Tổng cộng                {balance['cash_balance'] + balance['account_balance']:,.0f}đ"""
            
            console.print(Panel(balance_content, title="💰 SỐ DƯ HIỆN TẠI", padding=(1, 3)))
            
    except Exception as e:
        console.print(f"❌ Lỗi: {e}")

def show_monthly_chart(tracker):
    """Tạo và hiển thị biểu đồ chi tiêu theo ngày trong tháng hiện tại"""
    try:
        import matplotlib
        matplotlib.use('Agg')  # Backend không cần GUI, chỉ để save file
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from datetime import datetime, timedelta
        import os
        import subprocess
        
        print("📊 Đang tạo biểu đồ...")
        
        # Tạo folder để lưu charts
        charts_folder = "expense_charts"
        if not os.path.exists(charts_folder):
            os.makedirs(charts_folder)
        
        # Lấy dữ liệu tháng hiện tại
        monthly_data = tracker.db.get_current_month_summary_by_days(1)
        
        # Chuẩn bị dữ liệu cho biểu đồ
        dates = []
        expenses = []
        incomes = []
        
        for day_data in monthly_data:
            date_obj = datetime.strptime(day_data['date'], '%Y-%m-%d')
            dates.append(date_obj)
            expenses.append(day_data['total_expense'])
            incomes.append(day_data['total_income'])
        
        # Tạo tên file với tháng/năm
        current_month = datetime.now()
        month_year = current_month.strftime('%Y-%m')
        chart_filename = f"spending_chart_{month_year}.png"
        chart_path = os.path.join(charts_folder, chart_filename)
        
        # Title với tháng/năm cụ thể
        month_name_vn = {
            1: "Tháng 1", 2: "Tháng 2", 3: "Tháng 3", 4: "Tháng 4",
            5: "Tháng 5", 6: "Tháng 6", 7: "Tháng 7", 8: "Tháng 8", 
            9: "Tháng 9", 10: "Tháng 10", 11: "Tháng 11", 12: "Tháng 12"
        }
        month_vn = month_name_vn[current_month.month]
        
        # Tạo biểu đồ với kích thước lớn hơn
        fig = plt.figure(figsize=(16, 10))
        
        # Subplot cho chi tiêu
        plt.subplot(2, 1, 1)
        plt.plot(dates, expenses, 'r-', linewidth=2, label='Chi tiêu', marker='o', markersize=4)
        plt.title(f'Chi tiêu theo Ngày - {month_vn}/{current_month.year}', fontsize=16, fontweight='bold')
        plt.ylabel('Số tiền (VNĐ)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Format trục x - hiển thị ngày trong tháng
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d'))
        plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=2))  # Mỗi 2 ngày
        plt.xticks(rotation=45)
        
        # Format trục y để hiển thị số tiền đẹp
        plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}đ'))
        
        # Subplot cho thu nhập
        plt.subplot(2, 1, 2)
        plt.plot(dates, incomes, 'g-', linewidth=2, label='Thu nhập', marker='s', markersize=4)
        plt.title(f'Thu nhập theo Ngày - {month_vn}/{current_month.year}', fontsize=16, fontweight='bold')
        plt.xlabel('Ngày trong tháng', fontsize=12)
        plt.ylabel('Số tiền (VNĐ)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Format trục x
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d'))
        plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=2))
        plt.xticks(rotation=45)
        
        # Format trục y
        plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}đ'))
        
        plt.tight_layout(pad=3.0)
        
        # Lưu biểu đồ với DPI cao
        plt.savefig(chart_path, dpi=200, bbox_inches='tight', facecolor='white')
        plt.close()  # Đóng figure để tiết kiệm memory
        
        # Mở biểu đồ bằng image viewer mặc định của hệ thống
        print(f"📊 Mở biểu đồ {month_vn}/{current_month.year}...")
        try:
            subprocess.run(['xdg-open', chart_path], check=True)
            print("✅ Đã mở biểu đồ thành công!")
        except subprocess.CalledProcessError:
            print("❌ Không thể mở biểu đồ, hãy mở file manually")
        except FileNotFoundError:
            # Fallback cho hệ thống không có xdg-open
            try:
                subprocess.run(['open', chart_path], check=True)  # macOS
                print("✅ Đã mở biểu đồ thành công! (macOS)")
            except:
                print("❌ Không thể mở biểu đồ tự động")
        
        # Thông báo đường dẫn file
        print(f"\n✅ Biểu đồ {month_vn}/{current_month.year} đã được lưu tại: {chart_path}")
        print(f"📁 Thư mục charts: {os.path.abspath(charts_folder)}")
        
        # Hiển thị thông tin tóm tắt
        total_expense = sum(expenses)
        total_income = sum(incomes) 
        days_with_expense = len([e for e in expenses if e > 0])
        days_with_income = len([i for i in incomes if i > 0])
        
        print(f"\n📈 Tóm tắt {month_vn}/{current_month.year}:")
        print(f"   💸 Tổng chi tiêu: {total_expense:,.0f}đ")
        print(f"   💰 Tổng thu nhập: {total_income:,.0f}đ")
        print(f"   📅 Ngày có chi tiêu: {days_with_expense}/{len(dates)} ngày")
        print(f"   📅 Ngày có thu nhập: {days_with_income}/{len(dates)} ngày")
        
    except ImportError:
        print("⚠️ Cần cài đặt matplotlib: uv add matplotlib")
    except Exception as e:
        print(f"❌ Lỗi tạo biểu đồ: {e}")
        import traceback
        traceback.print_exc()


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