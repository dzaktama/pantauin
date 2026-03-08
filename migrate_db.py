import sqlite3
import os

db_path = os.path.join(r"C:\laragon\www\PANTAUIN", "pantauin.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

try:
    cur.execute("ALTER TABLE transaksi ADD COLUMN jenis_pengeluaran VARCHAR(50) DEFAULT 'operasional'")
    print("Added jenis_pengeluaran")
except Exception as e:
    print(e)
    
try:
    cur.execute("ALTER TABLE transaksi ADD COLUMN catatan TEXT")
    print("Added catatan")
except Exception as e:
    print(e)

conn.commit()
conn.close()
print("Done")
