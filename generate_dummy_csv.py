import csv
import random
from datetime import date, timedelta
import math

def generate_csv(filename, days_count=90):
    start_date = date.today() - timedelta(days=days_count - 1)
    
    # Target parameter for score ~73
    # 1. Stabilitas Cashflow (Margin Operasional > 20% -> Skor 100) -> Bobot 25% = 25
    # 2. Tren Penjualan pertumbuhannya positif tapi tidak terlalu ekstrim -> Skor ~60 -> Bobot 25% = 15
    # 3. Rasio Pengeluaran Operasional ~65% -> Skor 35 -> Bobot 20% = 7
    # 4. Gross Margin Harian dijaga di angka ~25% -> Skor 83 -> Bobot 20% = 16.6
    # 5. Konsistensi Pemasukan (CV 0.1) -> Skor 90 -> Bobot 10% = 9
    # Total ~ 72.6 (dibulatkan jadi 73)

    records = []
    
    # Base configuration
    base_revenue = 1500000  # Pemasukan harian dasar Rp 1.500.000
    
    for day in range(days_count):
        current_date = start_date + timedelta(days=day)
        
        # 1. Pemasukan (Konsisten dengan sedikit variasi + tren naik pelan)
        # Tambahkan tren linear yang sangat lambat (misal naik Rp 2.000 per hari)
        trend_factor = day * 2000
        # Variasi acak ± 10% untuk konsistensi (CV kecil)
        daily_revenue = base_revenue + trend_factor + random.uniform(-150000, 150000)
        
        # 2. Pengeluaran Operasional (Target Rasio ~65% sampai 70% dari pemasukan)
        # Ini akan mempengaruhi Stabilitas Cashflow (Margin Operasional) dan Rasio Pengeluaran
        op_ratio = random.uniform(0.65, 0.70)
        daily_op_expense = daily_revenue * op_ratio
        
        # 3. Pengeluaran Modal (Jarang terjadi, mungkin sebulan 1-2 kali)
        daily_modal_expense = 0
        if random.random() < 0.05:  # 5% peluang ada pengeluaran modal
            daily_modal_expense = random.uniform(500000, 1500000)

        # Pecah transaksi harian menjadi beberapa baris (minimal mencapai total 1000 baris dalam 90 hari)
        # Target: ~11 baris per hari (90 * 11 = 990 baris)
        num_transactions = random.randint(10, 14)
        
        # Alokasikan pemasukan ke beberapa transaksi
        revenue_chunks = []
        remaining_rev = daily_revenue
        for i in range(num_transactions // 2):
            if i == (num_transactions // 2) - 1:
                chunk = remaining_rev
            else:
                chunk = remaining_rev * random.uniform(0.1, 0.4)
            revenue_chunks.append(int(chunk))
            remaining_rev -= chunk
            
        # Alokasikan pengeluaran operasional
        op_chunks = []
        remaining_op = daily_op_expense
        for i in range(num_transactions // 2):
            if i == (num_transactions // 2) - 1:
                chunk = remaining_op
            else:
                chunk = remaining_op * random.uniform(0.1, 0.5)
            op_chunks.append(int(chunk))
            remaining_op -= chunk

        # Buat records untuk hari ini
        for idx in range(num_transactions // 2):
            # Transaksi Pemasukan
            records.append({
                'tanggal': current_date.strftime('%Y-%m-%d'),
                'keterangan': f"Penjualan Produk {random.choice(['A', 'B', 'C', 'Paket Khusus'])}",
                'pemasukan': revenue_chunks[idx],
                'pengeluaran': 0,
                'jenis_pengeluaran': ''
            })
            
            # Transaksi Pengeluaran Operasional
            records.append({
                'tanggal': current_date.strftime('%Y-%m-%d'),
                'keterangan': f"Beli Bahan Baku {random.choice(['Tepung', 'Daging', 'Sayuran', 'Kemasan'])}",
                'pemasukan': 0,
                'pengeluaran': op_chunks[idx],
                'jenis_pengeluaran': 'operasional'
            })
            
        # Jika ada pengeluaran modal hari ini, tambahkan sebagai 1 baris terpisah
        if daily_modal_expense > 0:
            records.append({
                'tanggal': current_date.strftime('%Y-%m-%d'),
                'keterangan': f"Beli Aset {random.choice(['Etalase', 'Mesin Pres', 'Renovasi Kios'])}",
                'pemasukan': 0,
                'pengeluaran': int(daily_modal_expense),
                'jenis_pengeluaran': 'modal'
            })

    # Tulis ke file CSV
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['tanggal', 'keterangan', 'pemasukan', 'pengeluaran', 'jenis_pengeluaran'])
        writer.writeheader()
        writer.writerows(records)

    print(f"Berhasil membuat {len(records)} baris data di '{filename}'.")

if __name__ == '__main__':
    generate_csv('data_dummy_73.csv', days_count=90)
