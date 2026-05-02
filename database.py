import sqlite3

def create_database():
    conn = sqlite3.connect("company.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY,
            name TEXT,
            department TEXT,
            salary INTEGER,
            city TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY,
            employee_id INTEGER,
            product TEXT,
            amount INTEGER,
            sale_date TEXT
        )
    """)

    employees = [
        (1, "Rahul Sharma", "Engineering", 75000, "Indore"),
        (2, "Priya Patel", "Marketing", 55000, "Mumbai"),
        (3, "Amit Verma", "Engineering", 80000, "Indore"),
        (4, "Sneha Joshi", "HR", 45000, "Pune"),
        (5, "Rohan Gupta", "Marketing", 60000, "Delhi"),
    ]

    sales = [
        (1, 1, "Software License", 120000, "2024-01-15"),
        (2, 2, "Ad Campaign", 85000, "2024-01-20"),
        (3, 1, "Consulting", 95000, "2024-02-10"),
        (4, 3, "Software License", 110000, "2024-02-14"),
        (5, 5, "Ad Campaign", 70000, "2024-03-01"),
    ]

    cursor.executemany(
        "INSERT OR IGNORE INTO employees VALUES (?,?,?,?,?)", employees
    )
    cursor.executemany(
        "INSERT OR IGNORE INTO sales VALUES (?,?,?,?,?)", sales
    )

    conn.commit()
    conn.close()
    print("Database created successfully!")

if __name__ == "__main__":
    create_database()