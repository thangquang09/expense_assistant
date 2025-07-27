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
    print("⚠️ Google Sheets dependencies không có. Cài đặt: pip install gspread google-auth")


class GoogleSheetsSync:
    def __init__(self, credentials_file: str = "credentials.json"):
        """Khởi tạo Google Sheets sync"""
        self.credentials_file = credentials_file
        self.gc = None
        self.spreadsheet = None
        self.enabled = False
        
        if GSPREAD_AVAILABLE:
            self._initialize_client()
    
    def _initialize_client(self):
        """Khởi tạo Google Sheets client"""
        try:
            # Kiểm tra file credentials
            if not os.path.exists(self.credentials_file):
                print(f"⚠️ Không tìm thấy {self.credentials_file}")
                print("💡 Tạo Service Account tại: https://console.developers.google.com/")
                return
            
            # Setup credentials
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            credentials = Credentials.from_service_account_file(
                self.credentials_file, 
                scopes=scope
            )
            
            self.gc = gspread.authorize(credentials)
            
            # Tạo hoặc mở spreadsheet
            self._setup_spreadsheet()
            
            if self.spreadsheet:
                self.enabled = True
                print("✅ Google Sheets sync đã kích hoạt")
            
        except Exception as e:
            print(f"⚠️ Lỗi khởi tạo Google Sheets: {e}")
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
                self.spreadsheet = self.gc.create(spreadsheet_name)
                print(f"📊 Đã tạo spreadsheet mới: {spreadsheet_name}")
            
            # Setup worksheets
            self._setup_worksheets()
            
        except Exception as e:
            print(f"⚠️ Lỗi setup spreadsheet: {e}")
            self.spreadsheet = None
    
    def _setup_worksheets(self):
        """Tạo các worksheet cần thiết"""
        try:
            # Worksheet cho transactions
            try:
                transactions_ws = self.spreadsheet.worksheet("Transactions")
            except:
                transactions_ws = self.spreadsheet.add_worksheet(
                    title="Transactions", 
                    rows=1000, 
                    cols=10
                )
                # Thêm headers
                headers = [
                    "ID", "Date", "Time", "Food Item", "Price", 
                    "Meal Time", "Created At", "Sync Date"
                ]
                transactions_ws.append_row(headers)
            
            # Worksheet cho user balance
            try:
                balance_ws = self.spreadsheet.worksheet("Balance")
            except:
                balance_ws = self.spreadsheet.add_worksheet(
                    title="Balance",
                    rows=100,
                    cols=5
                )
                headers = ["Date", "Cash Balance", "Account Balance", "Total", "Notes"]
                balance_ws.append_row(headers)
            
            # Worksheet cho statistics summary
            try:
                stats_ws = self.spreadsheet.worksheet("Statistics")
            except:
                stats_ws = self.spreadsheet.add_worksheet(
                    title="Statistics",
                    rows=500,
                    cols=8
                )
                headers = [
                    "Date", "Period", "Transaction Count", "Total Spent", 
                    "Avg Spent", "Min Spent", "Max Spent", "Generated At"
                ]
                stats_ws.append_row(headers)
                
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
                print("📊 Không có transaction mới để sync")
                return True
            
            # Prepare data for batch update
            sync_date = datetime.datetime.now().isoformat()
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
                print(f"📊 Đã sync {len(rows_to_add)} transactions lên Google Sheets")
            
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
            total = balance_data.get('cash_balance', 0) + balance_data.get('account_balance', 0)
            
            row = [
                today,
                balance_data.get('cash_balance', 0),
                balance_data.get('account_balance', 0),
                total,
                f"Auto sync at {datetime.datetime.now().strftime('%H:%M:%S')}"
            ]
            
            ws.append_row(row)
            print("💰 Đã sync balance lên Google Sheets")
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
            generated_at = datetime.datetime.now().isoformat()
            
            row = [
                today,
                f"{stats_data.get('days', 7)} days",
                stats_data.get('transaction_count', 0),
                stats_data.get('total_spent', 0),
                stats_data.get('avg_spent', 0),
                stats_data.get('min_spent', 0),
                stats_data.get('max_spent', 0),
                generated_at
            ]
            
            ws.append_row(row)
            print("📊 Đã sync statistics lên Google Sheets")
            return True
            
        except Exception as e:
            print(f"⚠️ Lỗi sync statistics: {e}")
            return False
    
    def export_full_data(self, db_instance) -> bool:
        """Export toàn bộ dữ liệu từ database lên Sheets"""
        if not self.enabled or not self.spreadsheet:
            return False
        
        try:
            # Export transactions
            all_transactions = db_instance.get_recent_transactions(user_id=1, limit=1000)
            if all_transactions:
                self.sync_transactions(all_transactions)
            
            # Export balance
            balance = db_instance.get_user_balance(user_id=1)
            if balance:
                self.sync_balance(balance)
            
            # Export statistics for different periods
            for days in [1, 7, 30]:
                stats = db_instance.get_spending_summary(user_id=1, days=days)
                if stats:
                    stats['days'] = days
                    self.sync_statistics(stats)
            
            print("🎉 Đã export toàn bộ dữ liệu lên Google Sheets")
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
            return True
        except Exception as e:
            print(f"⚠️ Test connection failed: {e}")
            return False


# Singleton instance
_sheets_sync = None

def get_sheets_sync() -> GoogleSheetsSync:
    """Get singleton instance của GoogleSheetsSync"""
    global _sheets_sync
    if _sheets_sync is None:
        _sheets_sync = GoogleSheetsSync()
    return _sheets_sync 