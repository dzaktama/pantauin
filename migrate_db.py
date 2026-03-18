import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'pantauin.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

try:
    c.execute("ALTER TABLE transaksi ADD COLUMN nama_produk VARCHAR(100)")
    print("Added nama_produk column.")
except Exception as e:
    print(f"Error adding nama_produk: {e}")

try:
    c.execute("ALTER TABLE transaksi ADD COLUMN kuantitas INTEGER DEFAULT 0")
    print("Added kuantitas column.")
except Exception as e:
    print(f"Error adding kuantitas: {e}")

conn.commit()
conn.close()
print("Migration completed.")
