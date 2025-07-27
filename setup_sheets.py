#!/usr/bin/env python3
"""
Google Sheets Setup & Test Tool
Giúp kiểm tra và setup Google Sheets integration
"""

import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from dotenv import load_dotenv

# Load environment
load_dotenv()

def main():
    console = Console()
    
    console.print(Panel(
        "🔧 GOOGLE SHEETS SETUP & TEST TOOL",
        subtitle="Kiểm tra và setup Google Sheets integration",
        border_style="cyan"
    ))
    
    # Bước 1: Kiểm tra dependencies
    console.print("\n[yellow]📦 Bước 1: Kiểm tra dependencies...[/yellow]")
    
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        console.print("✅ Google Sheets dependencies đã cài đặt")
    except ImportError:
        console.print("[red]❌ Thiếu dependencies[/red]")
        console.print("[yellow]💡 Chạy: uv add gspread google-auth[/yellow]")
        return
    
    # Bước 2: Kiểm tra credentials
    console.print("\n[yellow]📁 Bước 2: Kiểm tra credentials...[/yellow]")
    
    # Kiểm tra GOOGLE_APPLICATION_CREDENTIALS
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if creds_path:
        if os.path.exists(creds_path):
            console.print(f"✅ GOOGLE_APPLICATION_CREDENTIALS: {creds_path}")
        else:
            console.print(f"[red]❌ File không tồn tại: {creds_path}[/red]")
            console.print("[yellow]💡 Kiểm tra đường dẫn trong file .env[/yellow]")
            return
    else:
        # Kiểm tra credentials.json
        if os.path.exists('credentials.json'):
            console.print("✅ Tìm thấy credentials.json")
            creds_path = 'credentials.json'
        else:
            console.print("[red]❌ Không tìm thấy credentials[/red]")
            show_setup_guide(console)
            return
    
    # Bước 3: Test connection
    console.print("\n[yellow]🔗 Bước 3: Test kết nối Google Sheets...[/yellow]")
    
    try:
        # Setup credentials
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials = Credentials.from_service_account_file(creds_path, scopes=scope)
        gc = gspread.authorize(credentials)
        
        console.print("✅ Credentials hợp lệ")
        
        # Test tạo/mở spreadsheet
        spreadsheet_name = "Expense Tracker Test"
        
        try:
            spreadsheet = gc.open(spreadsheet_name)
            console.print(f"✅ Đã kết nối với spreadsheet: {spreadsheet_name}")
        except:
            # Thử tạo mới
            try:
                spreadsheet = gc.create(spreadsheet_name)
                console.print(f"✅ Đã tạo spreadsheet test: {spreadsheet_name}")
                
                # Xóa test spreadsheet sau khi tạo thành công
                import time
                time.sleep(1)
                gc.del_spreadsheet_by_key(spreadsheet.id)
                console.print("✅ Đã xóa spreadsheet test")
                
            except Exception as e:
                console.print(f"[red]❌ Lỗi tạo spreadsheet: {e}[/red]")
                
                # Kiểm tra specific errors
                if "403" in str(e) and "Google Drive API" in str(e):
                    show_drive_api_guide(console)
                else:
                    console.print(f"[red]Lỗi: {e}[/red]")
                return
        
        console.print("\n[green]🎉 Google Sheets integration hoạt động hoàn hảo![/green]")
        
        # Hiển thị thông tin spreadsheet sẽ được tạo
        show_success_info(console)
        
    except Exception as e:
        console.print(f"[red]❌ Lỗi kết nối: {e}[/red]")
        
        if "403" in str(e) and "Google Drive API" in str(e):
            show_drive_api_guide(console)
        elif "404" in str(e):
            console.print("[yellow]💡 Có thể service account không có quyền truy cập[/yellow]")
        else:
            console.print("[yellow]💡 Kiểm tra internet connection và credentials[/yellow]")


def show_setup_guide(console):
    """Hiển thị hướng dẫn setup credentials"""
    guide = """
[bold cyan]📋 HƯỚNG DẪN SETUP CREDENTIALS[/bold cyan]

[yellow]🔗 Bước 1: Tạo Google Cloud Project[/yellow]
1. Truy cập: https://console.cloud.google.com/
2. Tạo project mới hoặc chọn existing project

[yellow]🔧 Bước 2: Enable APIs[/yellow]
1. Enable Google Sheets API
2. Enable Google Drive API

[yellow]👤 Bước 3: Tạo Service Account[/yellow]
1. IAM & Admin > Service Accounts
2. Create Service Account
3. Download JSON key file

[yellow]⚙️ Bước 4: Cấu hình[/yellow]
1. Đặt JSON file vào thư mục project
2. Cập nhật .env:
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/key.json

[yellow]🔗 Links hữu ích:[/yellow]
• Google Cloud Console: https://console.cloud.google.com/
• Sheets API: https://console.cloud.google.com/apis/library/sheets.googleapis.com
• Drive API: https://console.cloud.google.com/apis/library/drive.googleapis.com
    """
    
    console.print(Panel(guide, title="📋 SETUP GUIDE", border_style="yellow"))


def show_drive_api_guide(console):
    """Hiển thị hướng dẫn enable Google Drive API"""
    guide = """
[bold red]⚠️  GOOGLE DRIVE API CHƯA ĐƯỢC KÍCH HOẠT[/bold red]

[yellow]🔧 Cách khắc phục:[/yellow]

1. Truy cập Google Cloud Console:
   https://console.cloud.google.com/apis/library/drive.googleapis.com

2. Chọn project đúng (có thể cần switch project)

3. Click "ENABLE" để kích hoạt Google Drive API

4. Đợi vài phút để API được activated

5. Chạy lại test này

[yellow]💡 Lưu ý:[/yellow]
• Cần cả Google Sheets API và Google Drive API
• Có thể mất 1-2 phút để propagate
• Đảm bảo chọn đúng project ID
    """
    
    console.print(Panel(guide, title="🔧 DRIVE API SETUP", border_style="red"))


def show_success_info(console):
    """Hiển thị thông tin sau khi setup thành công"""
    info = """
[bold green]🎉 GOOGLE SHEETS ĐÃ SẴN SÀNG![/bold green]

[yellow]📊 Các worksheet sẽ được tạo:[/yellow]
• Transactions - Danh sách tất cả giao dịch
• Balance - Lịch sử số dư
• Statistics - Báo cáo thống kê
• Daily Summary - Tổng hợp theo ngày

[yellow]🔄 Auto Sync:[/yellow]
• Mỗi transaction mới sẽ tự động sync
• Statistics sync khi xem báo cáo
• Balance sync khi cập nhật

[yellow]🚀 Test ngay:[/yellow]
• ea "test sheets hoạt động 25k"
• expense (interactive mode)
    """
    
    console.print(Panel(info, title="✅ SUCCESS", border_style="green"))


if __name__ == "__main__":
    main() 