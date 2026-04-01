import sqlite3
import json

class Database:
    def __init__(self, db_name = 'syncmark.db'):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_table()
        
    def create_table(self):
        with self.conn:
            self.conn.execute("""CREATE TABLE IF NOT EXISTS carts (user_id INTEGER PRIMARY KEY, items_json TEXT)""")
    
    def get_cart(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT items_json FROM carts WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else []
    
    def save_cart(self, user_id, new_items):
        with self.conn:
            # 1. Получаем то, что уже лежит в базе
            current_items = self.get_cart(user_id)
            
            # 2. Добавляем новые элементы к списку
            # Если new_items это список — объединяем, если один объект — добавляем
            if isinstance(new_items, list):
                current_items.extend(new_items)
            else:
                current_items.append(new_items)
            
            # 3. Сохраняем обновленный полный список
            json_data = json.dumps(current_items, ensure_ascii=False)
            self.conn.execute('INSERT OR REPLACE INTO carts VALUES (?, ?)', (user_id, json_data))
    
    def clear_cart(self, user_id):
        with self.conn:
            self.conn.execute('DELETE FROM carts WHERE user_id = ?', (user_id, ))