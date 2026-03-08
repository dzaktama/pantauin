import sqlite3

def run_migration():
    conn = sqlite3.connect(r'C:\laragon\www\PANTAUIN\pantauin.db')
    c = conn.cursor()

    print("Membuat tabel buku_kas...")
    c.execute('''
    CREATE TABLE IF NOT EXISTS buku_kas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        nama_buku VARCHAR(100) NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    print("Menambahkan kolom buku_kas_id pada tabel transaksi...")
    try:
        c.execute('ALTER TABLE transaksi ADD COLUMN buku_kas_id INTEGER REFERENCES buku_kas(id) ON DELETE CASCADE')
    except sqlite3.OperationalError:
        print("Kolom buku_kas_id sepertinya sudah ada, dilanjutkan...")

    print("Memberikan 'Buku Kas Utama' default untuk setiap Pengguna lama...")
    c.execute('SELECT id FROM users')
    users = c.fetchall()
    
    for row in users:
        uid = row[0]
        # Cek apakah user sudah punya buku kas (untuk idempotensi)
        c.execute('SELECT id FROM buku_kas WHERE user_id = ?', (uid,))
        bk = c.fetchone()
        
        if not bk:
            c.execute('INSERT INTO buku_kas (user_id, nama_buku) VALUES (?, ?)', (uid, "Buku Kas Utama"))
            bk_id = c.lastrowid
        else:
            bk_id = bk[0]
            
        # Pindahkan catatan yatim piatu ke dalam Buku Kas default ini
        c.execute('UPDATE transaksi SET buku_kas_id = ? WHERE user_id = ? AND buku_kas_id IS NULL', (bk_id, uid))

    conn.commit()
    conn.close()
    print("Migrasi Multi-Project (Buku_Kas) berhasil dijalankan secara End-to-End!")

if __name__ == '__main__':
    run_migration()
