import sqlite3

try:
    conn = sqlite3.connect("smart_village.db")
    print("Database opened successfully!")

    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )

    tables = cursor.fetchall()
    print("Tables found:", tables)

    conn.close()

except sqlite3.Error as e:
    print("Database error:", e)