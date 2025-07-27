import sqlite3
import datetime
from typing import Optional, Dict, Any, List


class Database:
    def __init__(self, db_path: str = "expense_tracker.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Khởi tạo database và tạo các bảng cần thiết"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tạo bảng người dùng
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL DEFAULT 'default_user',
                cash_balance REAL DEFAULT 0.0,
                account_balance REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tạo bảng giao dịch
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                food_item TEXT NOT NULL,
                price REAL NOT NULL,
                meal_time TEXT,
                transaction_type TEXT DEFAULT 'expense',
                account_type TEXT DEFAULT 'cash',
                transaction_date DATE NOT NULL,
                transaction_time TIME NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Migration: Add new columns if they don't exist
        try:
            cursor.execute("ALTER TABLE transactions ADD COLUMN transaction_type TEXT DEFAULT 'expense'")
        except sqlite3.OperationalError:
            pass  # Column already exists
            
        try:
            cursor.execute("ALTER TABLE transactions ADD COLUMN account_type TEXT DEFAULT 'cash'")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Tạo user mặc định nếu chưa có
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO users (name, cash_balance, account_balance) VALUES (?, ?, ?)",
                ("default_user", 0.0, 0.0)
            )
        
        conn.commit()
        conn.close()
    
    def add_transaction(self, user_id: int, food_item: str, price: float, 
                       meal_time: Optional[str] = None, 
                       transaction_type: str = 'expense',
                       account_type: str = 'cash') -> int:
        """
        Thêm giao dịch mới
        transaction_type: 'expense' (chi tiêu) hoặc 'income' (thu nhập)
        account_type: 'cash' (tiền mặt) hoặc 'account' (tài khoản ngân hàng)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.datetime.now()
        today = now.date().isoformat()  # Convert to string
        current_time = now.time().isoformat()  # Convert to string
        
        cursor.execute("""
            INSERT INTO transactions (user_id, food_item, price, meal_time, 
                                    transaction_type, account_type, transaction_date, transaction_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, food_item, price, meal_time, transaction_type, account_type, today, current_time))
        
        transaction_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return transaction_id
    
    def update_balance_by_amount(self, user_id: int, 
                                cash_amount: Optional[float] = None,
                                account_amount: Optional[float] = None) -> bool:
        """
        Cộng/trừ số dư (thay vì thay thế)
        cash_amount: số tiền cộng/trừ vào tiền mặt (có thể âm)
        account_amount: số tiền cộng/trừ vào tài khoản (có thể âm)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Lấy số dư hiện tại
            current_balance = self.get_user_balance(user_id)
            
            # Tính số dư mới
            new_cash = current_balance['cash_balance']
            new_account = current_balance['account_balance']
            
            if cash_amount is not None:
                new_cash += cash_amount
                
            if account_amount is not None:
                new_account += account_amount
            
            # Cập nhật số dư
            cursor.execute("""
                UPDATE users 
                SET cash_balance = ?, account_balance = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_cash, new_account, user_id))
            
            affected_rows = cursor.rowcount
            conn.commit()
            
            return affected_rows > 0
            
        except Exception as e:
            print(f"Lỗi cập nhật số dư: {e}")
            return False
        finally:
            conn.close()
    
    def get_user_balance(self, user_id: int = 1) -> Dict[str, float]:
        """Lấy số dư của người dùng"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT cash_balance, account_balance FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {"cash_balance": result[0], "account_balance": result[1]}
        return {"cash_balance": 0.0, "account_balance": 0.0}
    
    def update_user_balance(self, user_id: int, cash_balance: Optional[float] = None, 
                           account_balance: Optional[float] = None) -> bool:
        """Cập nhật số dư người dùng"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if cash_balance is not None:
            updates.append("cash_balance = ?")
            params.append(cash_balance)
        
        if account_balance is not None:
            updates.append("account_balance = ?")
            params.append(account_balance)
        
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(user_id)
            
            query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            
            affected_rows = cursor.rowcount
            conn.commit()
            conn.close()
            
            return affected_rows > 0
        
        conn.close()
        return False
    
    def get_recent_transactions(self, user_id: int = 1, limit: int = 10) -> List[Dict[str, Any]]:
        """Lấy các giao dịch gần đây"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, food_item, price, meal_time, transaction_date, transaction_time, created_at
            FROM transactions 
            WHERE user_id = ?
            ORDER BY transaction_date DESC, transaction_time DESC
            LIMIT ?
        """, (user_id, limit))
        
        columns = [desc[0] for desc in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        conn.close()
        return results
    
    def get_spending_summary(self, user_id: int = 1, days: int = 7) -> Dict[str, Any]:
        """Lấy tổng kết chi tiêu trong số ngày gần đây"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        date_threshold = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as transaction_count,
                SUM(price) as total_spent,
                AVG(price) as avg_spent,
                MIN(price) as min_spent,
                MAX(price) as max_spent
            FROM transactions 
            WHERE user_id = ? AND transaction_date >= ?
        """, (user_id, date_threshold))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            columns = ['transaction_count', 'total_spent', 'avg_spent', 'min_spent', 'max_spent']
            return dict(zip(columns, result))
        
        return {
            'transaction_count': 0,
            'total_spent': 0.0,
            'avg_spent': 0.0,
            'min_spent': 0.0,
            'max_spent': 0.0
        }
    
    def find_transactions(self, user_id: int, food_item: str, 
                         price: Optional[float] = None, 
                         meal_time: Optional[str] = None,
                         limit: int = 5) -> List[Dict[str, Any]]:
        """
        Tìm giao dịch theo tiêu chí
        Returns: List các giao dịch phù hợp (sắp xếp theo thời gian gần nhất)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Xây dựng query động
        where_conditions = ["user_id = ?"]
        params = [user_id]
        
        # Tìm kiếm food_item (fuzzy matching)
        where_conditions.append("LOWER(food_item) LIKE ?")
        params.append(f"%{food_item.lower()}%")
        
        # Thêm điều kiện giá nếu có
        if price is not None:
            where_conditions.append("price = ?")
            params.append(price)
        
        # Thêm điều kiện meal_time nếu có
        if meal_time is not None:
            where_conditions.append("meal_time = ?")
            params.append(meal_time)
        
        query = f"""
            SELECT id, food_item, price, meal_time, transaction_date, transaction_time, created_at
            FROM transactions 
            WHERE {' AND '.join(where_conditions)}
            ORDER BY transaction_date DESC, transaction_time DESC
            LIMIT ?
        """
        params.append(limit)
        
        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        
        conn.close()
        return results
    
    def delete_transaction(self, transaction_id: int, user_id: int = 1) -> bool:
        """
        Xóa giao dịch theo ID
        Returns: True nếu xóa thành công, False nếu không tìm thấy
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Kiểm tra giao dịch tồn tại và thuộc về user
        cursor.execute("SELECT id FROM transactions WHERE id = ? AND user_id = ?", 
                      (transaction_id, user_id))
        
        if not cursor.fetchone():
            conn.close()
            return False
        
        # Xóa giao dịch
        cursor.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", 
                      (transaction_id, user_id))
        
        affected_rows = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected_rows > 0
    
    def delete_transaction_by_criteria(self, user_id: int, food_item: str,
                                     price: Optional[float] = None,
                                     meal_time: Optional[str] = None) -> Dict[str, Any]:
        """
        Xóa giao dịch đầu tiên (gần nhất) phù hợp với tiêu chí
        Returns: Dict với thông tin kết quả
        """
        # Tìm giao dịch phù hợp
        matching_transactions = self.find_transactions(
            user_id=user_id,
            food_item=food_item,
            price=price,
            meal_time=meal_time,
            limit=1
        )
        
        if not matching_transactions:
            return {
                'success': False,
                'message': f'Không tìm thấy giao dịch phù hợp với "{food_item}"',
                'deleted_transaction': None
            }
        
        # Xóa giao dịch đầu tiên
        transaction_to_delete = matching_transactions[0]
        success = self.delete_transaction(transaction_to_delete['id'], user_id)
        
        if success:
            return {
                'success': True,
                'message': f'Đã xóa giao dịch: {transaction_to_delete["food_item"]} - {transaction_to_delete["price"]:,.0f}đ',
                'deleted_transaction': transaction_to_delete
            }
        else:
            return {
                'success': False,
                'message': 'Lỗi khi xóa giao dịch',
                'deleted_transaction': None
            }
    
    def delete_most_recent_transaction(self, user_id: int = 1) -> Dict[str, Any]:
        """
        Xóa giao dịch gần nhất của user
        Returns: Dict với thông tin kết quả
        """
        # Lấy giao dịch gần nhất
        recent_transactions = self.get_recent_transactions(user_id=user_id, limit=1)
        
        if not recent_transactions:
            return {
                'success': False,
                'message': 'Không có giao dịch nào để xóa',
                'deleted_transaction': None
            }
        
        # Xóa giao dịch gần nhất
        transaction_to_delete = recent_transactions[0]
        success = self.delete_transaction(transaction_to_delete['id'], user_id)
        
        if success:
            return {
                'success': True,
                'message': f'Đã xóa giao dịch gần nhất: {transaction_to_delete["food_item"]} - {transaction_to_delete["price"]:,.0f}đ',
                'deleted_transaction': transaction_to_delete
            }
        else:
            return {
                'success': False,
                'message': 'Lỗi khi xóa giao dịch gần nhất',
                'deleted_transaction': None
            } 

    def get_transaction_with_details(self, transaction_id: int) -> Optional[Dict[str, Any]]:
        """Lấy thông tin chi tiết giao dịch bao gồm transaction_type và account_type"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, user_id, food_item, price, meal_time, transaction_type, account_type,
                   transaction_date, transaction_time, created_at
            FROM transactions 
            WHERE id = ?
        """, (transaction_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'user_id': row[1], 
                'food_item': row[2],
                'price': row[3],
                'meal_time': row[4],
                'transaction_type': row[5] or 'expense',
                'account_type': row[6] or 'cash',
                'transaction_date': row[7],
                'transaction_time': row[8],
                'created_at': row[9]
            }
        
        return None 

    def get_daily_transactions(self, user_id: int = 1, target_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lấy TẤT CẢ giao dịch trong một ngày cụ thể"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if not target_date:
            target_date = datetime.date.today().isoformat()
        
        cursor.execute("""
            SELECT id, food_item, price, meal_time, transaction_type, account_type,
                   transaction_date, transaction_time, created_at
            FROM transactions 
            WHERE user_id = ? AND transaction_date = ?
            ORDER BY transaction_time DESC
        """, (user_id, target_date))
        
        rows = cursor.fetchall()
        conn.close()
        
        transactions = []
        for row in rows:
            transactions.append({
                'id': row[0],
                'food_item': row[1],
                'price': row[2],
                'meal_time': row[3],
                'transaction_type': row[4] or 'expense',
                'account_type': row[5] or 'cash',
                'transaction_date': row[6],
                'transaction_time': row[7],
                'created_at': row[8]
            })
        
        return transactions
    
    def get_weekly_summary_by_days(self, user_id: int = 1, days: int = 7) -> List[Dict[str, Any]]:
        """Lấy tổng chi tiêu theo từng ngày trong tuần qua"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Lấy days ngày gần nhất
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days-1)
        
        cursor.execute("""
            SELECT transaction_date, 
                   SUM(CASE WHEN transaction_type = 'expense' THEN price ELSE 0 END) as total_expense,
                   SUM(CASE WHEN transaction_type = 'income' THEN price ELSE 0 END) as total_income,
                   COUNT(*) as transaction_count
            FROM transactions 
            WHERE user_id = ? AND transaction_date BETWEEN ? AND ?
            GROUP BY transaction_date
            ORDER BY transaction_date DESC
        """, (user_id, start_date.isoformat(), end_date.isoformat()))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Tạo dict để dễ lookup
        data_by_date = {}
        for row in rows:
            data_by_date[row[0]] = {
                'date': row[0],
                'total_expense': row[1] or 0,
                'total_income': row[2] or 0,
                'transaction_count': row[3]
            }
        
        # Đảm bảo có đủ days ngày (kể cả ngày không có giao dịch)
        result = []
        for i in range(days):
            check_date = end_date - datetime.timedelta(days=i)
            date_str = check_date.isoformat()
            
            if date_str in data_by_date:
                result.append(data_by_date[date_str])
            else:
                result.append({
                    'date': date_str,
                    'total_expense': 0,
                    'total_income': 0,
                    'transaction_count': 0
                })
        
        return result
    
    def get_monthly_summary_by_weeks(self, user_id: int = 1) -> List[Dict[str, Any]]:
        """Lấy tổng chi tiêu theo từng tuần trong tháng"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Lấy 4 tuần gần nhất (28 ngày)
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=27)  # 4 tuần = 28 ngày
        
        cursor.execute("""
            SELECT transaction_date,
                   SUM(CASE WHEN transaction_type = 'expense' THEN price ELSE 0 END) as total_expense,
                   SUM(CASE WHEN transaction_type = 'income' THEN price ELSE 0 END) as total_income,
                   COUNT(*) as transaction_count
            FROM transactions 
            WHERE user_id = ? AND transaction_date BETWEEN ? AND ?
            GROUP BY transaction_date
            ORDER BY transaction_date
        """, (user_id, start_date.isoformat(), end_date.isoformat()))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Nhóm theo tuần
        weeks = []
        current_week = {'start_date': None, 'end_date': None, 'total_expense': 0, 'total_income': 0, 'transaction_count': 0}
        
        for i in range(4):  # 4 tuần
            week_start = start_date + datetime.timedelta(days=i*7)
            week_end = week_start + datetime.timedelta(days=6)
            
            week_expense = 0
            week_income = 0 
            week_count = 0
            
            for row in rows:
                row_date = datetime.datetime.strptime(row[0], '%Y-%m-%d').date()
                if week_start <= row_date <= week_end:
                    week_expense += row[1]
                    week_income += row[2]
                    week_count += row[3]
            
            weeks.append({
                'week_num': i + 1,
                'start_date': week_start.isoformat(),
                'end_date': week_end.isoformat(),
                'total_expense': week_expense,
                'total_income': week_income,
                'transaction_count': week_count
            })
        
        return weeks
    
    def get_monthly_summary_by_days(self, user_id: int = 1, days: int = 30) -> List[Dict[str, Any]]:
        """Lấy tổng chi tiêu theo từng ngày trong tháng (cho biểu đồ)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days-1)
        
        cursor.execute("""
            SELECT transaction_date,
                   SUM(CASE WHEN transaction_type = 'expense' THEN price ELSE 0 END) as total_expense,
                   SUM(CASE WHEN transaction_type = 'income' THEN price ELSE 0 END) as total_income,
                   COUNT(*) as transaction_count
            FROM transactions 
            WHERE user_id = ? AND transaction_date BETWEEN ? AND ?
            GROUP BY transaction_date
            ORDER BY transaction_date
        """, (user_id, start_date.isoformat(), end_date.isoformat()))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Tạo dict để dễ lookup
        data_by_date = {}
        for row in rows:
            data_by_date[row[0]] = {
                'date': row[0],
                'total_expense': row[1] or 0,
                'total_income': row[2] or 0,
                'transaction_count': row[3]
            }
        
        # Đảm bảo có đủ days ngày
        result = []
        for i in range(days):
            check_date = start_date + datetime.timedelta(days=i)
            date_str = check_date.isoformat()
            
            if date_str in data_by_date:
                result.append(data_by_date[date_str])
            else:
                result.append({
                    'date': date_str,
                    'total_expense': 0,
                    'total_income': 0,
                    'transaction_count': 0
                })
        
        return result 

    def get_current_month_summary_by_days(self, user_id: int = 1) -> List[Dict[str, Any]]:
        """Lấy tổng chi tiêu theo từng ngày trong THÁNG HIỆN TẠI (từ ngày 1 đến cuối tháng)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Lấy ngày đầu và cuối tháng hiện tại
        today = datetime.date.today()
        start_date = today.replace(day=1)  # Ngày 1 của tháng hiện tại
        
        # Tìm ngày cuối tháng
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)
        end_date = next_month - datetime.timedelta(days=1)  # Ngày cuối tháng hiện tại
        
        cursor.execute("""
            SELECT transaction_date,
                   SUM(CASE WHEN transaction_type = 'expense' THEN price ELSE 0 END) as total_expense,
                   SUM(CASE WHEN transaction_type = 'income' THEN price ELSE 0 END) as total_income,
                   COUNT(*) as transaction_count
            FROM transactions 
            WHERE user_id = ? AND transaction_date BETWEEN ? AND ?
            GROUP BY transaction_date
            ORDER BY transaction_date
        """, (user_id, start_date.isoformat(), end_date.isoformat()))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Tạo dict để dễ lookup
        data_by_date = {}
        for row in rows:
            data_by_date[row[0]] = {
                'date': row[0],
                'total_expense': row[1] or 0,
                'total_income': row[2] or 0,
                'transaction_count': row[3]
            }
        
        # Đảm bảo có đủ tất cả ngày trong tháng
        result = []
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.isoformat()
            
            if date_str in data_by_date:
                result.append(data_by_date[date_str])
            else:
                result.append({
                    'date': date_str,
                    'total_expense': 0,
                    'total_income': 0,
                    'transaction_count': 0
                })
            
            current_date += datetime.timedelta(days=1)
        
        return result 