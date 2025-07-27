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
        menu_table.add_row("5. ❓ Hướng dẫn")
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
    
    def display_chat_result(self, result: Dict[str, Any]):
        """Hiển thị kết quả xử lý chat"""
        if result['success']:
            # Hiển thị thông báo thành công
            self.console.print(f"[green]{result['message']}[/green]")
            
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

[yellow]💰 Cập nhật số dư:[/yellow]  
• "cập nhật tiền mặt 500k" - Cập nhật tiền mặt
• "tài khoản còn 2 triệu" - Cập nhật tài khoản ngân hàng
• "tiền mặt 100k, tài khoản 1 triệu" - Cập nhật cả hai

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