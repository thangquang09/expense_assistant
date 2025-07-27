import os
import sys
from typing import Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from rich.prompt import Prompt
from rich.layout import Layout
from rich.align import Align
from expense_tracker import ExpenseTracker


class ExpenseChatbot:
    def __init__(self):
        """Khởi tạo chatbot interface"""
        self.console = Console()
        self.tracker = ExpenseTracker()
        self.running = True
        
    def start(self):
        """Bắt đầu chatbot"""
        self.clear_screen()
        self.show_welcome()
        
        while self.running:
            try:
                self.show_menu()
                choice = self.get_user_input("Lựa chọn của bạn")
                
                if choice == "1":
                    self.chat_mode()
                elif choice == "2":
                    self.show_spending_report()
                elif choice == "3":
                    self.show_recent_transactions()
                elif choice == "4":
                    self.show_balance()
                elif choice == "5":
                    self.show_google_sheets_menu()
                elif choice == "6":
                    self.show_help()
                elif choice == "0":
                    self.exit_app()
                else:
                    self.console.print("[red]❌ Lựa chọn không hợp lệ![/red]")
                    self.pause()
                    
            except KeyboardInterrupt:
                self.exit_app()
            except Exception as e:
                self.console.print(f"[red]❌ Lỗi: {str(e)}[/red]")
                self.pause()
    
    def clear_screen(self):
        """Xóa màn hình"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def show_welcome(self):
        """Hiển thị thông điệp chào mừng"""
        welcome_text = Text("🤖 EXPENSE TRACKER ASSISTANT", style="bold magenta")
        welcome_panel = Panel(
            Align.center(welcome_text),
            box=box.DOUBLE,
            border_style="magenta"
        )
        self.console.print(welcome_panel)
        self.console.print("")
    
    def show_menu(self):
        """Hiển thị menu chính"""
        menu_table = Table(show_header=False, box=box.SIMPLE)
        menu_table.add_column("", style="cyan", width=50)
        
        menu_table.add_row("🎯 MENU CHÍNH")
        menu_table.add_row("━" * 40)
        menu_table.add_row("1. 💬 Chat để ghi chi tiêu")
        menu_table.add_row("2. 📊 Thống kê chi tiêu")
        menu_table.add_row("3. 📝 Giao dịch gần đây") 
        menu_table.add_row("4. 💰 Quản lý số dư")
        menu_table.add_row("5. 📋 Google Sheets")
        menu_table.add_row("6. ❓ Hướng dẫn")
        menu_table.add_row("0. 🚪 Thoát")
        
        self.console.print(Panel(menu_table, border_style="cyan"))
        self.console.print("")
    
    def get_user_input(self, prompt_text: str) -> str:
        """Lấy input từ người dùng"""
        return Prompt.ask(f"[yellow]🤔 {prompt_text}[/yellow]").strip()
    
    def chat_mode(self):
        """Chế độ chat để ghi chi tiêu"""
        self.clear_screen()
        
        chat_panel = Panel(
            "💬 CHẾ độ CHAT\n\n"
            "Hãy nhập câu mô tả chi tiêu của bạn!\n"
            "VD: 'trưa ăn phở 35k', 'mua cà phê 25000', 'cập nhật tiền mặt 500k'\n\n"
            "Gõ 'exit' để quay về menu chính",
            title="Chat Mode",
            border_style="green"
        )
        self.console.print(chat_panel)
        self.console.print("")
        
        while True:
            user_message = self.get_user_input("Bạn")
            
            if user_message.lower() in ['exit', 'quit', 'back', 'quay về']:
                break
            
            if not user_message:
                continue
            
            # Xử lý tin nhắn
            with self.console.status("[yellow]🤖 Đang xử lý...[/yellow]"):
                result = self.tracker.process_user_message(user_message)
            
            self.display_chat_result(result)
            self.console.print("")
    
    def show_google_sheets_menu(self):
        """Hiển thị menu Google Sheets"""
        self.clear_screen()
        
        # Kiểm tra trạng thái sync
        sheets_sync = self.tracker.sheets_sync
        
        status_table = Table(show_header=True, header_style="bold cyan", box=box.DOUBLE)
        status_table.add_column("📋 Google Sheets Status", style="cyan", width=25)
        status_table.add_column("Trạng thái", style="green", width=20)
        
        if sheets_sync.enabled:
            status_table.add_row("🔗 Kết nối", "[green]✅ Đã kích hoạt[/green]")
            if sheets_sync.spreadsheet:
                status_table.add_row("📊 Spreadsheet", sheets_sync.spreadsheet.title)
                url = sheets_sync.get_spreadsheet_url()
                if url:
                    # Truncate URL for display
                    display_url = url if len(url) < 40 else url[:37] + "..."
                    status_table.add_row("🔗 URL", display_url)
        else:
            status_table.add_row("🔗 Kết nối", "[red]❌ Chưa kích hoạt[/red]")
            status_table.add_row("📝 Cần thiết", "credentials.json")
        
        self.console.print(Panel(status_table, title="📋 GOOGLE SHEETS", border_style="cyan"))
        self.console.print("")
        
        # Menu options
        if sheets_sync.enabled:
            options = [
                "1. 📤 Export toàn bộ dữ liệu",
                "2. 🔄 Test kết nối", 
                "3. 📊 Mở Spreadsheet (URL)",
                "4. ℹ️  Hướng dẫn sử dụng",
                "0. 🔙 Quay về menu chính"
            ]
        else:
            options = [
                "1. 📝 Hướng dẫn setup",
                "2. 🔄 Thử kết nối lại",
                "0. 🔙 Quay về menu chính"
            ]
        
        for option in options:
            self.console.print(f"[cyan]{option}[/cyan]")
        
        self.console.print("")
        choice = self.get_user_input("Lựa chọn của bạn")
        
        if sheets_sync.enabled:
            if choice == "1":
                self.export_to_sheets()
            elif choice == "2":
                self.test_sheets_connection()
            elif choice == "3":
                self.show_spreadsheet_url()
            elif choice == "4":
                self.show_sheets_help()
            elif choice == "0":
                return
        else:
            if choice == "1":
                self.show_sheets_setup_guide()
            elif choice == "2":
                self.retry_sheets_connection()
            elif choice == "0":
                return
        
        if choice != "0":
            self.pause()
    
    def export_to_sheets(self):
        """Export dữ liệu lên Google Sheets"""
        with self.console.status("[yellow]📤 Đang export dữ liệu...[/yellow]"):
            result = self.tracker.export_to_sheets()
        
        if result['success']:
            self.console.print(f"[green]{result['message']}[/green]")
            if result.get('spreadsheet_url'):
                self.console.print(f"[cyan]🔗 URL: {result['spreadsheet_url']}[/cyan]")
        else:
            self.console.print(f"[red]❌ {result['message']}[/red]")
            if result.get('suggestion'):
                self.console.print(f"[yellow]💡 {result['suggestion']}[/yellow]")
    
    def test_sheets_connection(self):
        """Test kết nối Google Sheets"""
        with self.console.status("[yellow]🔄 Đang test kết nối...[/yellow]"):
            success = self.tracker.sheets_sync.test_connection()
        
        if success:
            self.console.print("[green]✅ Kết nối Google Sheets thành công![/green]")
        else:
            self.console.print("[red]❌ Kết nối thất bại![/red]")
            self.console.print("[yellow]💡 Kiểm tra credentials.json và internet[/yellow]")
    
    def show_spreadsheet_url(self):
        """Hiển thị URL của spreadsheet"""
        url = self.tracker.sheets_sync.get_spreadsheet_url()
        if url:
            self.console.print(f"[cyan]📊 Spreadsheet URL:[/cyan]")
            self.console.print(f"[blue]{url}[/blue]")
            self.console.print("\n[yellow]💡 Copy URL này để mở trong browser[/yellow]")
        else:
            self.console.print("[red]❌ Không thể lấy URL[/red]")
    
    def show_sheets_setup_guide(self):
        """Hiển thị hướng dẫn setup Google Sheets"""
        self.clear_screen()
        
        guide_text = """
[bold cyan]📋 HƯỚNG DẪN SETUP GOOGLE SHEETS[/bold cyan]

[yellow]Bước 1: Tạo Google Cloud Project[/yellow]
• Truy cập: https://console.developers.google.com/
• Tạo project mới hoặc chọn existing project
• Enable Google Sheets API và Google Drive API

[yellow]Bước 2: Tạo Service Account[/yellow]
• Vào IAM & Admin > Service Accounts
• Tạo Service Account mới
• Download credentials JSON file
• Đổi tên thành "credentials.json"

[yellow]Bước 3: Cài đặt file[/yellow]
• Copy credentials.json vào folder app này
• Restart ứng dụng

[yellow]Bước 4: Chia sẻ quyền (tùy chọn)[/yellow]
• Nếu muốn access spreadsheet từ Google account khác
• Share spreadsheet với email trong credentials.json

[yellow]📝 File cần thiết:[/yellow]
• credentials.json (trong folder app)

[yellow]🔗 Links hữu ích:[/yellow]
• Google Cloud Console: https://console.developers.google.com/
• Google Sheets API: https://developers.google.com/sheets/api
        """
        
        guide_panel = Panel(guide_text, title="📋 SETUP GUIDE", border_style="yellow")
        self.console.print(guide_panel)
    
    def retry_sheets_connection(self):
        """Thử kết nối lại Google Sheets"""
        with self.console.status("[yellow]🔄 Đang thử kết nối lại...[/yellow]"):
            # Re-initialize sheets sync
            from google_sheets_sync import GoogleSheetsSync
            self.tracker.sheets_sync = GoogleSheetsSync()
        
        if self.tracker.sheets_sync.enabled:
            self.console.print("[green]✅ Kết nối thành công![/green]")
        else:
            self.console.print("[red]❌ Vẫn không thể kết nối[/red]")
            self.console.print("[yellow]💡 Kiểm tra credentials.json file[/yellow]")
    
    def show_sheets_help(self):
        """Hiển thị hướng dẫn sử dụng Google Sheets"""
        self.clear_screen()
        
        help_text = """
[bold cyan]📋 SỬ DỤNG GOOGLE SHEETS[/bold cyan]

[yellow]🔄 Auto Sync:[/yellow]
• Mỗi giao dịch mới sẽ tự động sync lên Sheets
• Balance updates cũng được sync
• Statistics được sync khi xem báo cáo

[yellow]📊 Worksheets được tạo:[/yellow]
• "Transactions": Danh sách tất cả giao dịch
• "Balance": Lịch sử số dư theo thời gian  
• "Statistics": Báo cáo thống kê định kỳ

[yellow]📤 Export Manual:[/yellow]
• Dùng "Export toàn bộ dữ liệu" để sync tất cả
• Hữu ích sau khi xóa giao dịch
• Hoặc khi muốn backup toàn bộ

[yellow]📈 Phân tích dữ liệu:[/yellow]
• Tạo charts/graphs trong Google Sheets
• Pivot tables để phân tích trend
• Chia sẻ báo cáo với người khác

[yellow]💡 Tips:[/yellow]
• Không sửa trực tiếp trên Sheets (có thể bị ghi đè)
• Dùng Sheets để view và analyze
• App vẫn là source of truth chính
        """
        
        help_panel = Panel(help_text, title="📋 GOOGLE SHEETS HELP", border_style="cyan")
        self.console.print(help_panel)
    
    def display_chat_result(self, result: Dict[str, Any]):
        """Hiển thị kết quả xử lý chat"""
        
        # Hiển thị cảnh báo offline mode nếu có
        if result.get('offline_mode', False):
            offline_panel = Panel(
                "🔴 CHẾ ĐỘ OFFLINE\n"
                "🌐 Không có kết nối internet hoặc API\n"
                "💡 Vui lòng nhập rõ ràng: 'ăn phở 30k', 'xóa phở', 'thống kê hôm nay'",
                title="⚠️ Offline Mode",
                border_style="red"
            )
            self.console.print(offline_panel)
            self.console.print("")
        
        if result['success']:
            # Hiển thị thông báo thành công
            message = result['message']
            if result.get('synced_to_sheets', False):
                message += " 📋"  # Indicator cho sync
            self.console.print(f"[green]{message}[/green]")
            
            # Hiển thị sync status nếu có
            if result.get('synced_to_sheets', False):
                self.console.print("[dim]📋 Đã sync lên Google Sheets[/dim]")
            elif result.get('note'):
                self.console.print(f"[yellow]💡 {result['note']}[/yellow]")
            
            # Hiển thị thống kê chi tiêu nếu có
            if 'statistics' in result:
                stats = result['statistics']
                
                stats_table = Table(show_header=True, header_style="bold cyan", box=box.SIMPLE)
                stats_table.add_column("📊 Thống kê", style="cyan", width=20)
                stats_table.add_column("Giá trị", style="yellow", justify="right", width=15)
                
                # Kiểm tra xem có phải là kết quả xóa không
                if 'deleted_amount' in stats:
                    stats_table.add_row("🗑️ Đã xóa", f"{stats['deleted_amount']:,.0f}đ")
                    stats_table.add_row("📅 Hôm nay còn", f"{stats['today_total']:,.0f}đ ({stats['today_count']} lần)")
                    stats_table.add_row("📆 Tuần này còn", f"{stats['week_total']:,.0f}đ ({stats['week_count']} lần)")
                    border_color = "red"
                    title = "🗑️ Thống kê sau khi xóa"
                else:
                    stats_table.add_row("🎯 Giao dịch này", f"{stats['this_transaction']:,.0f}đ")
                    stats_table.add_row("📅 Hôm nay", f"{stats['today_total']:,.0f}đ ({stats['today_count']} lần)")
                    stats_table.add_row("📆 Tuần này", f"{stats['week_total']:,.0f}đ ({stats['week_count']} lần)")
                    border_color = "cyan"
                    title = "📊 Thống kê chi tiêu"
                
                self.console.print(Panel(stats_table, title=title, border_style=border_color))
            
            # Hiển thị thống kê chi tiết nếu có
            if 'statistics_detailed' in result:
                stats = result['statistics_detailed']
                
                # Bảng thống kê chi tiết
                detail_table = Table(show_header=True, header_style="bold magenta", box=box.DOUBLE)
                detail_table.add_column("📋 Chi tiết", style="magenta", width=20)
                detail_table.add_column("Giá trị", style="cyan", justify="right", width=20)
                
                detail_table.add_row("📅 Thời gian", stats['period'])
                detail_table.add_row("💸 Tổng chi tiêu", f"{stats['total_spent']:,.0f}đ")
                detail_table.add_row("🔢 Số giao dịch", f"{stats['transaction_count']} lần")
                
                if stats['transaction_count'] > 0:
                    detail_table.add_row("📊 Trung bình/lần", f"{stats['avg_spent']:,.0f}đ")
                    detail_table.add_row("📉 Thấp nhất", f"{stats['min_spent']:,.0f}đ")
                    detail_table.add_row("📈 Cao nhất", f"{stats['max_spent']:,.0f}đ")
                
                # Thêm indicator cho offline mode và sync status
                indicators = []
                if result.get('offline_mode', False):
                    indicators.append("offline")
                if result.get('synced_to_sheets', False):
                    indicators.append("📋 synced")
                
                title = "📊 Thống kê chi tiết"
                if indicators:
                    title += f" ({', '.join(indicators)})"
                
                self.console.print(Panel(detail_table, title=title, border_style="magenta"))
                
                # Hiển thị giao dịch gần đây nếu có
                if stats['recent_transactions']:
                    recent_table = Table(show_header=True, header_style="bold yellow", box=box.SIMPLE)
                    recent_table.add_column("🕐 Ngày", style="yellow", width=12)
                    recent_table.add_column("🍽️ Món", style="green", width=15)
                    recent_table.add_column("💰 Giá", style="cyan", justify="right", width=12)
                    
                    for trans in stats['recent_transactions']:
                        recent_table.add_row(
                            trans['transaction_date'],
                            trans['food_item'],
                            f"{trans['price']:,.0f}đ"
                        )
                    
                    self.console.print(Panel(recent_table, title="🕐 Giao dịch gần đây", border_style="yellow"))
            
            # Hiển thị thông tin cập nhật số dư nếu có 
            if 'balance' in result:
                balance = result['balance']
                balance_text = f"💰 Số dư hiện tại: Tiền mặt {balance['cash_balance']:,.0f}đ | Tài khoản {balance['account_balance']:,.0f}đ"
                self.console.print(f"[green]{balance_text}[/green]")
                
        else:
            # Hiển thị lỗi
            self.console.print(f"[red]{result['message']}[/red]")
            if 'suggestion' in result:
                self.console.print(f"[yellow]💡 {result['suggestion']}[/yellow]")
    
    def show_balance(self):
        """Hiển thị số dư hiện tại"""
        self.clear_screen()
        
        balance = self.tracker.get_balance_summary()
        
        balance_table = Table(show_header=True, header_style="bold cyan", box=box.DOUBLE)
        balance_table.add_column("Loại tài khoản", style="cyan", width=20)
        balance_table.add_column("Số dư", style="green", justify="right", width=15)
        
        balance_table.add_row("💵 Tiền mặt", f"{balance['cash_balance']:,.0f}đ")
        balance_table.add_row("🏦 Tài khoản ngân hàng", f"{balance['account_balance']:,.0f}đ")
        balance_table.add_row("━" * 20, "━" * 15)
        balance_table.add_row("💰 TỔNG CỘNG", f"[bold green]{balance['total_balance']:,.0f}đ[/bold green]")
        
        panel = Panel(balance_table, title="💰 SỐ DƯ HIỆN TẠI", border_style="cyan")
        self.console.print(panel)
        
        self.pause()
    
    def show_spending_report(self):
        """Hiển thị báo cáo chi tiêu"""
        self.clear_screen()
        
        days = self.get_user_input("Số ngày muốn xem báo cáo (mặc định 7)")
        if not days or not days.isdigit():
            days = 7
        else:
            days = int(days)
        
        report = self.tracker.get_spending_report(days)
        summary = report['summary']
        
        # Bảng tổng quan
        summary_table = Table(show_header=True, header_style="bold cyan")
        summary_table.add_column("Thống kê", style="cyan")
        summary_table.add_column("Giá trị", style="green", justify="right")
        
        summary_table.add_row("📅 Khoảng thời gian", f"{days} ngày")
        summary_table.add_row("🔢 Số giao dịch", f"{summary['transaction_count']}")
        summary_table.add_row("💸 Tổng chi tiêu", f"{summary['total_spent']:,.0f}đ" if summary['total_spent'] else "0đ")
        summary_table.add_row("📊 Chi tiêu trung bình", f"{summary['avg_spent']:,.0f}đ" if summary['avg_spent'] else "0đ")
        summary_table.add_row("📉 Chi tiêu thấp nhất", f"{summary['min_spent']:,.0f}đ" if summary['min_spent'] else "0đ")
        summary_table.add_row("📈 Chi tiêu cao nhất", f"{summary['max_spent']:,.0f}đ" if summary['max_spent'] else "0đ")
        
        self.console.print(Panel(summary_table, title=f"📊 BÁO CÁO CHI TIÊU {days} NGÀY", border_style="cyan"))
        
        # Số dư hiện tại
        balance = report['balance']
        balance_text = f"💰 Số dư hiện tại: {balance['total_balance']:,.0f}đ"
        self.console.print(f"\n[green]{balance_text}[/green]")
        
        self.pause()
    
    def show_recent_transactions(self):
        """Hiển thị giao dịch gần đây"""
        self.clear_screen()
        
        transactions = self.tracker.get_recent_transactions(10)
        
        if not transactions:
            self.console.print("[yellow]📝 Chưa có giao dịch nào![/yellow]")
            self.pause()
            return
        
        trans_table = Table(show_header=True, header_style="bold cyan", box=box.SIMPLE)
        trans_table.add_column("STT", style="dim", width=4)
        trans_table.add_column("Ngày", style="cyan", width=12)
        trans_table.add_column("Món ăn", style="green", width=20)
        trans_table.add_column("Giá", style="yellow", justify="right", width=12)
        trans_table.add_column("Bữa", style="magenta", width=8)
        
        for i, trans in enumerate(transactions, 1):
            trans_table.add_row(
                str(i),
                trans['transaction_date'],
                trans['food_item'],
                f"{trans['price']:,.0f}đ",
                trans['meal_time'] or ""
            )
        
        panel = Panel(trans_table, title="📝 GIAO DỊCH GẦN ĐÂY", border_style="cyan")
        self.console.print(panel)
        
        self.pause()
    
    def show_help(self):
        """Hiển thị hướng dẫn sử dụng"""
        self.clear_screen()
        
        help_text = """
[bold cyan]🎯 HƯỚNG DẪN SỬ DỤNG[/bold cyan]

 [yellow]💬 Ghi chi tiêu:[/yellow]
 • "trưa ăn phở 35k" - Ghi chi tiêu có thời gian
 • "mua cà phê 25000" - Ghi chi tiêu không có thời gian  
 • "ăn bún chả 40 nghìn" - Số tiền bằng chữ
 • "tối ăn cơm 50k" - Bữa ăn + món + giá

 [yellow]🗑️ Xóa giao dịch:[/yellow]
 • "xóa giao dịch phở" - Xóa giao dịch gần nhất có phở
 • "xóa phở 30k" - Xóa giao dịch phở với giá cụ thể
 • "hủy ăn bánh" - Xóa giao dịch ăn bánh

 [yellow]📊 Xem thống kê:[/yellow]
 • "thống kê hôm nay" - Xem chi tiêu hôm nay
 • "chi tiêu tuần này" - Xem chi tiêu 7 ngày
 • "báo cáo 5 ngày" - Xem chi tiêu 5 ngày qua
 • "tổng chi tiêu" - Xem tổng quan (mặc định tuần)

 [yellow]💰 Cập nhật số dư:[/yellow]  
 • "cập nhật tiền mặt 500k" - Cập nhật tiền mặt
 • "tài khoản còn 2 triệu" - Cập nhật tài khoản ngân hàng

 [yellow]📊 Xem thông tin:[/yellow]
 • Menu 2: Thống kê chi tiêu theo thời gian
 • Menu 3: Danh sách giao dịch gần đây
 • Menu 4: Quản lý số dư (tùy chọn)

 [yellow]💡 Mẹo:[/yellow]
 • Có thể viết "35k", "35000", "35 nghìn" đều được
 • Ứng dụng tập trung vào thống kê chi tiêu, không tự động trừ số dư
 • Dữ liệu được lưu tự động trong file SQLite để phân tích
        """
        
        help_panel = Panel(help_text, title="❓ HƯỚNG DẪN", border_style="yellow")
        self.console.print(help_panel)
        
        self.pause()
    
    def pause(self):
        """Tạm dừng chờ người dùng nhấn Enter"""
        self.console.print("")
        Prompt.ask("[dim]Nhấn Enter để tiếp tục...[/dim]", default="")
        self.clear_screen()
    
    def exit_app(self):
        """Thoát ứng dụng"""
        self.clear_screen()
        goodbye_text = Text("👋 Cảm ơn bạn đã sử dụng Expense Tracker!", style="bold green")
        goodbye_panel = Panel(
            Align.center(goodbye_text),
            box=box.DOUBLE,
            border_style="green"
        )
        self.console.print(goodbye_panel)
        self.running = False
        sys.exit(0) 