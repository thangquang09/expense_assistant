import os
import json
import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Load environment
load_dotenv()

try:
    import gspread
    from google.oauth2.service_account import Credentials
    from gspread.exceptions import APIError, SpreadsheetNotFound
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    print("⚠️ Google Sheets dependencies không có. Cài đặt: uv add gspread google-auth")


class GoogleSheetsSync:
    def __init__(self):
        """Khởi tạo Google Sheets sync với support cho GOOGLE_APPLICATION_CREDENTIALS"""
        self.gc = None
        self.spreadsheet = None
        self.enabled = False
        self.credentials_source = None
        
        if GSPREAD_AVAILABLE:
            self._initialize_client()
    
    def _get_credentials_path(self) -> Optional[str]:
        """Lấy đường dẫn credentials với ưu tiên: GOOGLE_APPLICATION_CREDENTIALS > credentials.json"""
        
        # Option 1: Từ environment variable
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if creds_path and os.path.exists(creds_path):
            return creds_path
        
        # Option 2: File credentials.json trong project
        local_creds = "credentials.json"
        if os.path.exists(local_creds):
            return local_creds
        
        return None
    
    def _initialize_client(self):
        """Khởi tạo Google Sheets client"""
        try:
            # Tìm credentials file
            credentials_path = self._get_credentials_path()
            
            if not credentials_path:
                print("⚠️ Không tìm thấy Google Sheets credentials")
                print("💡 Cấu hình một trong các cách sau:")
                print("   1. Set GOOGLE_APPLICATION_CREDENTIALS trong .env")
                print("   2. Hoặc đặt credentials.json trong thư mục project")
                print("   3. Xem hướng dẫn trong GOOGLE_SHEETS_SETUP.md")
                return
            
            self.credentials_source = credentials_path
            
            # Setup credentials scope
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Load credentials
            credentials = Credentials.from_service_account_file(
                credentials_path, 
                scopes=scope
            )
            
            self.gc = gspread.authorize(credentials)
            
            # Test connection và tạo spreadsheet
            self._setup_spreadsheet()
            
            if self.spreadsheet:
                self.enabled = True
                print(f"✅ Google Sheets sync đã kích hoạt")
                print(f"📁 Credentials: {credentials_path}")
                print(f"📊 Spreadsheet: {self.spreadsheet.title}")
            
        except Exception as e:
            print(f"⚠️ Lỗi khởi tạo Google Sheets: {e}")
            print("💡 Kiểm tra:")
            print("   - Credentials file có đúng không?")
            print("   - Service account có quyền Google Sheets API?")
            print("   - Có kết nối internet không?")
            self.enabled = False
    
    def _setup_spreadsheet(self):
        """Setup spreadsheet và worksheets"""
        try:
            spreadsheet_name = "Expense Tracker Data"
            
            # Thử mở spreadsheet hiện có
            try:
                self.spreadsheet = self.gc.open(spreadsheet_name)
                print(f"📊 Đã kết nối với spreadsheet: {spreadsheet_name}")
            except SpreadsheetNotFound:
                # Tạo mới nếu chưa có
                print(f"📊 Tạo spreadsheet mới: {spreadsheet_name}")
                self.spreadsheet = self.gc.create(spreadsheet_name)
                
                # Make it shareable (optional)
                print("🔗 Spreadsheet đã tạo - có thể share với email khác nếu cần")
            
            # Setup worksheets
            self._setup_worksheets()
            
        except Exception as e:
            print(f"⚠️ Lỗi setup spreadsheet: {e}")
            self.spreadsheet = None
    
    def _setup_worksheets(self):
        """Tạo các worksheet cần thiết"""
        try:
            worksheets_created = []
            
            # Worksheet cho transactions
            try:
                transactions_ws = self.spreadsheet.worksheet("Transactions")
            except:
                transactions_ws = self.spreadsheet.add_worksheet(
                    title="Transactions", 
                    rows=1000, 
                    cols=10
                )
                # Thêm headers với formatting
                headers = [
                    "ID", "Date", "Time", "Food Item", "Price (VND)", 
                    "Meal Time", "Created At", "Sync Date"
                ]
                transactions_ws.append_row(headers)
                
                # Format header row
                transactions_ws.format('A1:H1', {
                    'textFormat': {'bold': True},
                    'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 1.0}
                })
                worksheets_created.append("Transactions")
            
            # Worksheet cho user balance
            try:
                balance_ws = self.spreadsheet.worksheet("Balance")
            except:
                balance_ws = self.spreadsheet.add_worksheet(
                    title="Balance",
                    rows=100,
                    cols=6
                )
                headers = ["Date", "Cash Balance (VND)", "Account Balance (VND)", "Total (VND)", "Notes", "Updated At"]
                balance_ws.append_row(headers)
                
                # Format header
                balance_ws.format('A1:F1', {
                    'textFormat': {'bold': True},
                    'backgroundColor': {'red': 0.9, 'green': 1.0, 'blue': 0.9}
                })
                worksheets_created.append("Balance")
            
            # Worksheet cho statistics summary
            try:
                stats_ws = self.spreadsheet.worksheet("Statistics")
            except:
                stats_ws = self.spreadsheet.add_worksheet(
                    title="Statistics",
                    rows=500,
                    cols=9
                )
                headers = [
                    "Date", "Period", "Transaction Count", "Total Spent (VND)", 
                    "Avg Spent (VND)", "Min Spent (VND)", "Max Spent (VND)", "Generated At", "Notes"
                ]
                stats_ws.append_row(headers)
                
                # Format header
                stats_ws.format('A1:I1', {
                    'textFormat': {'bold': True},
                    'backgroundColor': {'red': 1.0, 'green': 0.9, 'blue': 0.9}
                })
                worksheets_created.append("Statistics")
            
            # Worksheet cho daily summary (bonus)
            try:
                daily_ws = self.spreadsheet.worksheet("Daily Summary")
            except:
                daily_ws = self.spreadsheet.add_worksheet(
                    title="Daily Summary",
                    rows=366,  # Một năm
                    cols=8
                )
                headers = [
                    "Date", "Breakfast", "Lunch", "Dinner", "Other", "Total", "Transaction Count", "Avg per Meal"
                ]
                daily_ws.append_row(headers)
                
                # Format header
                daily_ws.format('A1:H1', {
                    'textFormat': {'bold': True},
                    'backgroundColor': {'red': 1.0, 'green': 1.0, 'blue': 0.9}
                })
                worksheets_created.append("Daily Summary")
            
            if worksheets_created:
                print(f"📝 Đã tạo worksheets: {', '.join(worksheets_created)}")
                
        except Exception as e:
            print(f"⚠️ Lỗi setup worksheets: {e}")
    
    def sync_transactions(self, transactions: List[Dict[str, Any]]) -> bool:
        """Sync transactions lên Google Sheets"""
        if not self.enabled or not self.spreadsheet:
            return False
        
        try:
            ws = self.spreadsheet.worksheet("Transactions")
            
            # Lấy existing data để tránh duplicate
            existing_data = ws.get_all_records()
            existing_ids = {str(row.get('ID', '')) for row in existing_data}
            
            # Filter transactions chưa sync
            new_transactions = [
                t for t in transactions 
                if str(t.get('id', '')) not in existing_ids
            ]
            
            if not new_transactions:
                return True  # Không có gì để sync nhưng vẫn thành công
            
            # Prepare data for batch update
            sync_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            rows_to_add = []
            
            for trans in new_transactions:
                row = [
                    trans.get('id', ''),
                    trans.get('transaction_date', ''),
                    trans.get('transaction_time', ''),
                    trans.get('food_item', ''),
                    trans.get('price', 0),
                    trans.get('meal_time', ''),
                    trans.get('created_at', ''),
                    sync_date
                ]
                rows_to_add.append(row)
            
            # Batch append
            if rows_to_add:
                ws.append_rows(rows_to_add)
                print(f"📊 Đã sync {len(rows_to_add)} transactions mới lên Google Sheets")
            
            return True
            
        except Exception as e:
            print(f"⚠️ Lỗi sync transactions: {e}")
            return False
    
    def sync_balance(self, balance_data: Dict[str, float]) -> bool:
        """Sync balance lên Google Sheets"""
        if not self.enabled or not self.spreadsheet:
            return False
        
        try:
            ws = self.spreadsheet.worksheet("Balance")
            
            today = datetime.date.today().isoformat()
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            total = balance_data.get('cash_balance', 0) + balance_data.get('account_balance', 0)
            
            row = [
                today,
                balance_data.get('cash_balance', 0),
                balance_data.get('account_balance', 0),
                total,
                f"Auto sync from Expense Tracker",
                now
            ]
            
            ws.append_row(row)
            return True
            
        except Exception as e:
            print(f"⚠️ Lỗi sync balance: {e}")
            return False
    
    def sync_statistics(self, stats_data: Dict[str, Any]) -> bool:
        """Sync statistics lên Google Sheets"""
        if not self.enabled or not self.spreadsheet:
            return False
        
        try:
            ws = self.spreadsheet.worksheet("Statistics")
            
            today = datetime.date.today().isoformat()
            generated_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Determine period description
            days = stats_data.get('days', 7)
            if days == 1:
                period_desc = "Daily"
            elif days == 7:
                period_desc = "Weekly"
            elif days == 30:
                period_desc = "Monthly"
            else:
                period_desc = f"{days} days"
            
            row = [
                today,
                period_desc,
                stats_data.get('transaction_count', 0),
                stats_data.get('total_spent', 0),
                stats_data.get('avg_spent', 0),
                stats_data.get('min_spent', 0),
                stats_data.get('max_spent', 0),
                generated_at,
                f"Auto generated via CLI/App"
            ]
            
            ws.append_row(row)
            return True
            
        except Exception as e:
            print(f"⚠️ Lỗi sync statistics: {e}")
            return False
    
    def export_full_data(self, db_instance) -> bool:
        """Export toàn bộ dữ liệu từ database lên Sheets"""
        if not self.enabled or not self.spreadsheet:
            return False
        
        try:
            print("📤 Bắt đầu export toàn bộ dữ liệu...")
            
            # Export transactions
            all_transactions = db_instance.get_recent_transactions(user_id=1, limit=1000)
            if all_transactions:
                success = self.sync_transactions(all_transactions)
                if success:
                    print(f"✅ Đã export {len(all_transactions)} transactions")
            
            # Export balance
            balance = db_instance.get_user_balance(user_id=1)
            if balance:
                self.sync_balance(balance)
                print("✅ Đã export balance")
            
            # Export statistics for different periods
            for days, period_name in [(1, "hôm nay"), (7, "tuần này"), (30, "tháng này")]:
                stats = db_instance.get_spending_summary(user_id=1, days=days)
                if stats and stats.get('transaction_count', 0) > 0:
                    stats['days'] = days
                    self.sync_statistics(stats)
                    print(f"✅ Đã export thống kê {period_name}")
            
            print("🎉 Hoàn thành export toàn bộ dữ liệu lên Google Sheets")
            print(f"🔗 URL: {self.get_spreadsheet_url()}")
            return True
            
        except Exception as e:
            print(f"⚠️ Lỗi export full data: {e}")
            return False
    
    def get_spreadsheet_url(self) -> Optional[str]:
        """Lấy URL của spreadsheet"""
        if self.spreadsheet:
            return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet.id}/edit"
        return None
    
    def test_connection(self) -> bool:
        """Test kết nối với Google Sheets"""
        if not self.enabled:
            return False
        
        try:
            # Thử đọc một cell đơn giản
            ws = self.spreadsheet.worksheet("Transactions")
            ws.acell('A1')
            print("✅ Test connection thành công")
            return True
        except Exception as e:
            print(f"⚠️ Test connection thất bại: {e}")
            return False
    
    def get_status_info(self) -> Dict[str, Any]:
        """Lấy thông tin trạng thái chi tiết"""
        return {
            'enabled': self.enabled,
            'credentials_source': self.credentials_source,
            'spreadsheet_title': self.spreadsheet.title if self.spreadsheet else None,
            'spreadsheet_url': self.get_spreadsheet_url(),
            'gspread_available': GSPREAD_AVAILABLE
        }


# Singleton instance
_sheets_sync = None

def get_sheets_sync() -> GoogleSheetsSync:
    """Get singleton instance của GoogleSheetsSync"""
    global _sheets_sync
    if _sheets_sync is None:
        _sheets_sync = GoogleSheetsSync()
    return _sheets_sync 