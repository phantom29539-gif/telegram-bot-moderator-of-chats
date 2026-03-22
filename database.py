import sqlite3
from config import DB_NAME


class Database:
    """Класс для работы с базой данных SQLite"""

    def __init__(self):
        """Инициализация и создание таблиц при первом запуске"""
        self.conn = sqlite3.connect(DB_NAME)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """Создание всех необходимых таблиц"""

        # Таблица чатов (настройки)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                chat_id INTEGER PRIMARY KEY,
                anti_flood_enabled INTEGER DEFAULT 1,
                welcome_enabled INTEGER DEFAULT 1,
                filter_words_enabled INTEGER DEFAULT 1
            )
        ''')

        # Таблица пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER,
                chat_id INTEGER,
                username TEXT,
                warns INTEGER DEFAULT 0,
                balance INTEGER DEFAULT 100,
                is_muted INTEGER DEFAULT 0,
                mute_until INTEGER DEFAULT 0,
                last_message_time INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, chat_id)
            )
        ''')

        # Таблица предупреждений (история)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS warns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_id INTEGER,
                admin_id INTEGER,
                reason TEXT,
                date INTEGER
            )
        ''')

        # Таблица запрещенных слов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS banned_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                word TEXT
            )
        ''')

        # Таблица администраторов бота (доверенные пользователи)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                chat_id INTEGER
            )
        ''')

        self.conn.commit()

    # ========== РАБОТА С ПОЛЬЗОВАТЕЛЯМИ ==========

    def get_user(self, user_id, chat_id, username=""):
        """Получить пользователя или создать нового"""
        self.cursor.execute(
            "SELECT * FROM users WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id)
        )
        user = self.cursor.fetchone()

        if not user:
            # Создаем нового пользователя
            self.cursor.execute(
                "INSERT INTO users (user_id, chat_id, username, warns, balance) VALUES (?, ?, ?, 0, 100)",
                (user_id, chat_id, username)
            )
            self.conn.commit()
            return self.get_user(user_id, chat_id, username)
        return user

    def update_username(self, user_id, chat_id, username):
        """Обновить имя пользователя"""
        self.cursor.execute(
            "UPDATE users SET username = ? WHERE user_id = ? AND chat_id = ?",
            (username, user_id, chat_id)
        )
        self.conn.commit()

    # ========== СИСТЕМА ВАРНОВ ==========

    def add_warn(self, user_id, chat_id, admin_id, reason=""):
        """Добавить варн пользователю"""
        import time

        # Получаем текущее количество варнов
        user = self.get_user(user_id, chat_id)
        current_warns = user[4]  # warns это 4-й индекс (считаем с 0)
        new_warns = current_warns + 1

        # Обновляем количество варнов
        self.cursor.execute(
            "UPDATE users SET warns = ? WHERE user_id = ? AND chat_id = ?",
            (new_warns, user_id, chat_id)
        )

        # Сохраняем в историю
        self.cursor.execute(
            "INSERT INTO warns (user_id, chat_id, admin_id, reason, date) VALUES (?, ?, ?, ?, ?)",
            (user_id, chat_id, admin_id, reason, int(time.time()))
        )

        self.conn.commit()
        return new_warns

    def get_warns(self, user_id, chat_id):
        """Получить количество варнов пользователя"""
        user = self.get_user(user_id, chat_id)
        return user[4]  # warns это 4-й индекс

    def clear_warns(self, user_id, chat_id):
        """Очистить варны пользователя"""
        self.cursor.execute(
            "UPDATE users SET warns = 0 WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id)
        )
        self.conn.commit()

    # ========== БАН И МУТ ==========

    def ban_user(self, user_id, chat_id):
        """Пометить пользователя как забаненного в БД"""
        self.cursor.execute(
            "UPDATE users SET warns = -1 WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id)
        )
        self.conn.commit()

    def mute_user(self, user_id, chat_id, duration):
        """Замутить пользователя на duration секунд"""
        import time
        mute_until = int(time.time()) + duration
        self.cursor.execute(
            "UPDATE users SET is_muted = 1, mute_until = ? WHERE user_id = ? AND chat_id = ?",
            (mute_until, user_id, chat_id)
        )
        self.conn.commit()

    def unmute_user(self, user_id, chat_id):
        """Размутить пользователя"""
        self.cursor.execute(
            "UPDATE users SET is_muted = 0, mute_until = 0 WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id)
        )
        self.conn.commit()

    def is_muted(self, user_id, chat_id):
        """Проверить, замучен ли пользователь"""
        import time
        user = self.get_user(user_id, chat_id)
        if user[6] == 1 and user[7] > int(time.time()):
            return True
        elif user[6] == 1 and user[7] <= int(time.time()):
            self.unmute_user(user_id, chat_id)
            return False
        return False

    # ========== ЭКОНОМИКА ==========

    def get_balance(self, user_id, chat_id):
        """Получить баланс пользователя"""
        user = self.get_user(user_id, chat_id)
        return user[5]  # balance это 5-й индекс

    def update_balance(self, user_id, chat_id, amount):
        """Изменить баланс (положительное или отрицательное число)"""
        current = self.get_balance(user_id, chat_id)
        new_balance = current + amount
        self.cursor.execute(
            "UPDATE users SET balance = ? WHERE user_id = ? AND chat_id = ?",
            (new_balance, user_id, chat_id)
        )
        self.conn.commit()
        return new_balance

    # ========== ЗАПРЕЩЕННЫЕ СЛОВА ==========

    def add_banned_word(self, chat_id, word):
        """Добавить запрещенное слово"""
        self.cursor.execute(
            "INSERT INTO banned_words (chat_id, word) VALUES (?, ?)",
            (chat_id, word.lower())
        )
        self.conn.commit()

    def get_banned_words(self, chat_id):
        """Получить список запрещенных слов для чата"""
        self.cursor.execute(
            "SELECT word FROM banned_words WHERE chat_id = ?",
            (chat_id,)
        )
        words = self.cursor.fetchall()
        return [word[0] for word in words]

    def remove_banned_word(self, chat_id, word):
        """Удалить запрещенное слово"""
        self.cursor.execute(
            "DELETE FROM banned_words WHERE chat_id = ? AND word = ?",
            (chat_id, word.lower())
        )
        self.conn.commit()

    # ========== АДМИНИСТРАТОРЫ БОТА ==========

    def add_admin(self, user_id, chat_id):
        """Сделать пользователя администратором бота"""
        self.cursor.execute(
            "INSERT OR IGNORE INTO admins (user_id, chat_id) VALUES (?, ?)",
            (user_id, chat_id)
        )
        self.conn.commit()

    def remove_admin(self, user_id, chat_id):
        """Удалить пользователя из администраторов"""
        self.cursor.execute(
            "DELETE FROM admins WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id)
        )
        self.conn.commit()

    def is_admin(self, user_id, chat_id):
        """Проверить, является ли пользователь администратором бота"""
        self.cursor.execute(
            "SELECT * FROM admins WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id)
        )
        return self.cursor.fetchone() is not None

    # ========== АНТИФЛУД ==========

    def update_last_message_time(self, user_id, chat_id, timestamp):
        """Обновить время последнего сообщения"""
        self.cursor.execute(
            "UPDATE users SET last_message_time = ? WHERE user_id = ? AND chat_id = ?",
            (timestamp, user_id, chat_id)
        )
        self.conn.commit()

    def get_last_message_time(self, user_id, chat_id):
        """Получить время последнего сообщения"""
        user = self.get_user(user_id, chat_id)
        return user[8]  # last_message_time это 8-й индекс

    def close(self):
        """Закрыть соединение с БД"""
        self.conn.close()