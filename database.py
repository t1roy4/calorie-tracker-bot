import sqlite3
from datetime import date

DB_NAME = "diary.db"


def init_db():
    """Создаёт таблицы, если их ещё нет. Вызывается один раз при старте бота."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            food_name TEXT NOT NULL,
            grams REAL NOT NULL,
            calories REAL NOT NULL,
            protein REAL NOT NULL,
            fat REAL NOT NULL,
            carbs REAL NOT NULL,
            entry_date TEXT NOT NULL
        )
    """)

    # Дневная норма калорий и БЖУ для каждого пользователя
    cur.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            user_id INTEGER PRIMARY KEY,
            calories REAL NOT NULL,
            protein REAL,
            fat REAL,
            carbs REAL
        )
    """)

    # Продукты, добавленные пользователями вручную (бренды, готовая еда)
    # или один раз распознанные через ИИ и сохранённые для повторного использования
    cur.execute("""
        CREATE TABLE IF NOT EXISTS custom_foods (
            name TEXT PRIMARY KEY,
            calories REAL NOT NULL,
            protein REAL NOT NULL,
            fat REAL NOT NULL,
            carbs REAL NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def add_entry(user_id, food_name, grams, calories, protein, fat, carbs):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO entries (user_id, food_name, grams, calories, protein, fat, carbs, entry_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, food_name, grams, calories, protein, fat, carbs, str(date.today())))
    conn.commit()
    conn.close()


def get_today_summary(user_id):
    """Возвращает список записей и суммы калорий/БЖУ за сегодня."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT food_name, grams, calories, protein, fat, carbs
        FROM entries
        WHERE user_id = ? AND entry_date = ?
    """, (user_id, str(date.today())))
    rows = cur.fetchall()
    conn.close()

    total_cal = sum(r[2] for r in rows)
    total_protein = sum(r[3] for r in rows)
    total_fat = sum(r[4] for r in rows)
    total_carbs = sum(r[5] for r in rows)

    return rows, total_cal, total_protein, total_fat, total_carbs


def set_goal(user_id, calories, protein=None, fat=None, carbs=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO goals (user_id, calories, protein, fat, carbs)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            calories = excluded.calories,
            protein = excluded.protein,
            fat = excluded.fat,
            carbs = excluded.carbs
    """, (user_id, calories, protein, fat, carbs))
    conn.commit()
    conn.close()


def get_goal(user_id):
    """Возвращает (calories, protein, fat, carbs) или None, если норма не задана."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT calories, protein, fat, carbs FROM goals WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row


def add_custom_food(name, calories, protein, fat, carbs):
    """Добавляет или обновляет продукт в пользовательской базе (бренды, готовая еда, из ИИ)."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO custom_foods (name, calories, protein, fat, carbs)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            calories = excluded.calories,
            protein = excluded.protein,
            fat = excluded.fat,
            carbs = excluded.carbs
    """, (name.lower().strip(), calories, protein, fat, carbs))
    conn.commit()
    conn.close()


def find_custom_food(name):
    """Ищет продукт в пользовательской базе (точное и частичное совпадение)."""
    name = name.lower().strip()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT name, calories, protein, fat, carbs FROM custom_foods WHERE name = ?", (name,))
    row = cur.fetchone()
    if not row:
        cur.execute("SELECT name, calories, protein, fat, carbs FROM custom_foods")
        for r in cur.fetchall():
            if name in r[0] or r[0] in name:
                row = r
                break
    conn.close()
    if row:
        return row[0], (row[1], row[2], row[3], row[4])
    return None, None
