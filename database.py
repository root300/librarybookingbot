import sqlite3
import datetime
from contextlib import contextmanager


class Database:
    def __init__(self, db_name='library.db'):
        self.db_name = db_name
        self.init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def init_db(self):
        with self.get_connection() as conn:
            # Таблица пользователей
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    group_name TEXT,
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица бронирований
            conn.execute('''
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    room_id INTEGER,
                    date DATE,
                    start_time TEXT,
                    end_time TEXT,
                    group_name TEXT,
                    status TEXT DEFAULT 'active',
                    booking_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')

    def add_user(self, user_id, username, full_name, group_name):
        with self.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO users (user_id, username, full_name, group_name)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, full_name, group_name))

    def create_booking(self, user_id, room_id, date, start_time, end_time, group_name):
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO bookings (user_id, room_id, date, start_time, end_time, group_name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, room_id, date, start_time, end_time, group_name))
            return cursor.lastrowid

    def get_user_bookings(self, user_id):
        with self.get_connection() as conn:
            return conn.execute('''
                SELECT * FROM bookings 
                WHERE user_id = ? AND status = 'active' AND date >= date('now')
                ORDER BY date, start_time
            ''', (user_id,)).fetchall()

    def cancel_booking(self, booking_id, user_id):
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE bookings 
                SET status = 'cancelled' 
                WHERE id = ? AND user_id = ?
            ''', (booking_id, user_id))

    def get_available_slots(self, room_id, date):
        with self.get_connection() as conn:
            # Включаем group_name в запрос
            bookings = conn.execute('''
                SELECT start_time, end_time, group_name FROM bookings 
                WHERE room_id = ? AND date = ? AND status = 'active'
                ORDER BY start_time
            ''', (room_id, date)).fetchall()
            return bookings

    def check_group_limit(self, group_name, date):
        with self.get_connection() as conn:
            result = conn.execute('''
                SELECT 
                    SUM(
                        (CAST(substr(end_time, 1, 2) AS INTEGER) * 60 + CAST(substr(end_time, 4, 2) AS INTEGER) -
                        CAST(substr(start_time, 1, 2) AS INTEGER) * 60 - CAST(substr(start_time, 4, 2) AS INTEGER)
                        ) / 60.0
                    ) as total_hours
                FROM bookings 
                WHERE group_name = ? AND date = ? AND status = 'active'
            ''', (group_name, date)).fetchone()

            return result['total_hours'] or 0


# Создаем глобальный экземпляр базы данных
db = Database()