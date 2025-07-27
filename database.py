import sqlite3
import datetime
from typing import Optional, List, Dict, Any


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