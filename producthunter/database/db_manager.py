import sqlite3
import os


class DBManager:
    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self.db_path = os.path.join("data", "products.db")
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            category TEXT,
            price REAL,
            rating REAL,
            reviews INTEGER,
            sold_count INTEGER,
            source TEXT,
            trend_score REAL DEFAULT 0,
            demand_score REAL DEFAULT 0,
            competition_score REAL DEFAULT 0,
            profit_estimate REAL DEFAULT 0,
            ai_verdict TEXT
        )
        """)

        self.conn.commit()

    def insert_product(self, product):
        cursor = self.conn.cursor()

        cursor.execute("""
        INSERT INTO products (
            title, category, price, rating,
            reviews, sold_count, source
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            product.get("title", ""),
            product.get("category", ""),
            product.get("price", 0),
            product.get("rating", 0),
            product.get("reviews", 0),
            product.get("sold_count", 0),
            product.get("source", "")
        ))

        self.conn.commit()

    def get_all_products(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM products")
        return [dict(row) for row in cursor.fetchall()]

    def search_products(self, keyword):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM products WHERE title LIKE ?",
            (f"%{keyword}%",)
        )
        return [dict(row) for row in cursor.fetchall()]

    def clear_all_products(self):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM products")
        self.conn.commit()

    def get_stats(self):
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM products")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT category) FROM products")
        categories = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM products WHERE demand_score > 0"
        )
        analysed = cursor.fetchone()[0]

        return {
            "total_products": total,
            "categories": categories,
            "analysed": analysed,
            "reports": 0
        }

    def update_product_scores(self, product_id, scores):
        cursor = self.conn.cursor()

        cursor.execute("""
        UPDATE products
        SET demand_score=?,
            competition_score=?,
            profit_estimate=?,
            trend_score=?,
            ai_verdict=?
        WHERE id=?
        """, (
            scores.get("demand_score", 0),
            scores.get("competition_score", 0),
            scores.get("profit_estimate", 0),
            scores.get("trend_score", 0),
            scores.get("ai_verdict", ""),
            product_id
        ))

        self.conn.commit()