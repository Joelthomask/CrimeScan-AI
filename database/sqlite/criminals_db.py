import sqlite3
import numpy as np
import os
import shutil
from utils.logger import get_logger
LOG = get_logger()

# =========================================================
# Global singleton instance
# =========================================================

_DB_INSTANCE = None


def get_db():
    global _DB_INSTANCE
    if _DB_INSTANCE is None:
        LOG.info("[DB] Initializing global database connection...")
        _DB_INSTANCE = DatabaseHandler(_internal=True)
        LOG.info("[DB] Database ready.")
    return _DB_INSTANCE


# =========================================================
# Database Handler
# =========================================================

class DatabaseHandler:
    _initialized = False

    def __init__(self, db_path=None, _internal=False):
        global _DB_INSTANCE

        # 🔒 If already initialized, reuse existing instance state
        if DatabaseHandler._initialized:
            if _DB_INSTANCE is not None:
                self.__dict__ = _DB_INSTANCE.__dict__
            return

        DatabaseHandler._initialized = True

        # Always resolve from project root
        BASE_DIR = os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
        )

        if db_path is None:
            self.db_path = os.path.join(BASE_DIR, "database", "sqlite", "criminals.db")
        else:
            self.db_path = db_path

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

        _DB_INSTANCE = self
        LOG.info(f"USING DATABASE: {self.db_path}")


    # ---------------- Table setup ----------------

    def create_tables(self):
        cursor = self.conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS criminals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            age INTEGER,
            gender TEXT,
            height TEXT,
            address TEXT,
            crime TEXT,
            location TEXT,
            dob TEXT,
            other_info TEXT,
            image_folder TEXT
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            criminal_id INTEGER,
            embedding BLOB,
            FOREIGN KEY (criminal_id) REFERENCES criminals(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS forensic_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT UNIQUE,
            image_id TEXT,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        self.conn.commit()

    # ---------------- Criminal operations ----------------

    def insert_criminal(
        self,
        name=None,
        age=None,
        gender=None,
        height=None,
        address=None,
        crime=None,
        location=None,
        dob=None,
        other_info=None,
        image_folder=None
    ):
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO criminals
                    (name, age, gender, height, address, crime, location, dob, other_info, image_folder)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, age, gender, height, address, crime, location, dob, other_info, image_folder))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            cursor.execute("SELECT id FROM criminals WHERE name=?", (name,))
            row = cursor.fetchone()
            return row["id"] if row else None

    def fetch_all_criminals(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM criminals")
        return [dict(row) for row in cursor.fetchall()]

    def fetch_criminal_by_id(self, criminal_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM criminals WHERE id=?", (criminal_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_criminal_by_name(self, name):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name FROM criminals WHERE name=?", (name,))
        return cursor.fetchone()

    def delete_criminal(self, name):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, image_folder FROM criminals WHERE name=?", (name,))
        row = cursor.fetchone()

        if not row:
            return False

        criminal_id, folder = row

        cursor.execute("DELETE FROM embeddings WHERE criminal_id=?", (criminal_id,))
        cursor.execute("DELETE FROM criminals WHERE id=?", (criminal_id,))
        self.conn.commit()

        if folder and os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)

        return True

    def clear_all_criminals(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT image_folder FROM criminals")
        rows = cursor.fetchall()

        cursor.execute("DELETE FROM embeddings")
        cursor.execute("DELETE FROM criminals")
        self.conn.commit()

        for (folder,) in rows:
            if folder and os.path.exists(folder):
                shutil.rmtree(folder, ignore_errors=True)

    # ---------------- Embedding operations ----------------

    def insert_embedding(self, criminal_id, embedding: np.ndarray):
        cursor = self.conn.cursor()
        emb_bytes = embedding.astype(np.float32).tobytes()
        cursor.execute(
            "INSERT INTO embeddings (criminal_id, embedding) VALUES (?, ?)",
            (criminal_id, emb_bytes),
        )
        self.conn.commit()
        return cursor.lastrowid

    def fetch_embeddings_by_criminal(self, criminal_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT embedding FROM embeddings WHERE criminal_id=?", (criminal_id,))
        rows = cursor.fetchall()
        return [np.frombuffer(row["embedding"], dtype=np.float32) for row in rows]

    def fetch_all_embeddings(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT criminal_id, embedding FROM embeddings")
        rows = cursor.fetchall()
        result = []
        for row in rows:
            emb = np.frombuffer(row["embedding"], dtype=np.float32)
            result.append((row["criminal_id"], emb))
        return result

    def close(self):
        self.conn.close()

def create_case(conn, image_path):
    cursor = conn.cursor()

    image_id = os.path.basename(image_path)

    # get last case number
    cursor.execute("SELECT MAX(id) FROM forensic_cases")
    row = cursor.fetchone()

    next_id = (row[0] or 0) + 1
    case_id = f"CASE_{next_id:04d}"

    cursor.execute("""
        INSERT INTO forensic_cases (case_id, image_id, image_path)
        VALUES (?, ?, ?)
    """, (case_id, image_id, image_path))

    conn.commit()

    return case_id, image_id
