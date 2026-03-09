from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.sql import func

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    def set_password(self, password):
        """Menghash password plain teks dan menyimpannya."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Memverifikasi password dengan hash yang tersimpan."""
        return check_password_hash(self.password_hash, password)

class BukuKas(db.Model):
    __tablename__ = 'buku_kas'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    nama_buku = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    user = db.relationship('User', backref=db.backref('buku_kas', lazy=True, cascade='all, delete-orphan'))
    # Relasi one-to-one: BukuKas punya satu ProfilPerusahaan
    profil = db.relationship('ProfilPerusahaan', backref='buku_kas', uselist=False, lazy=True, cascade='all, delete-orphan')

class Transaksi(db.Model):
    __tablename__ = 'transaksi'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    buku_kas_id = db.Column(db.Integer, db.ForeignKey('buku_kas.id', ondelete='CASCADE'), nullable=False)
    tanggal = db.Column(db.Date, nullable=False)
    kategori = db.Column(db.String(50), nullable=False)  # 'Makanan & Minuman', 'Retail', 'Jasa', 'Lainnya'
    jenis_pengeluaran = db.Column(db.String(50), default='operasional')
    pemasukan = db.Column(db.Float, default=0.0)
    pengeluaran = db.Column(db.Float, default=0.0)
    jumlah_pelanggan = db.Column(db.Integer, default=0)
    catatan = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    
    user = db.relationship('User', backref=db.backref('transaksi', lazy=True, cascade='all, delete-orphan'))
    buku_kas = db.relationship('BukuKas', backref=db.backref('transaksi_buku', lazy=True, cascade='all, delete-orphan'))

class ProfilPerusahaan(db.Model):
    __tablename__ = 'profil_perusahaan'
    
    id = db.Column(db.Integer, primary_key=True)
    buku_kas_id = db.Column(db.Integer, db.ForeignKey('buku_kas.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # I. IDENTITAS PERUSAHAAN
    nama_perusahaan = db.Column(db.String(150), nullable=False)
    contact_person = db.Column(db.String(100))
    jabatan = db.Column(db.String(50))
    bentuk_usaha = db.Column(db.String(50)) # PT/CV/Firma/dll
    jenis_usaha = db.Column(db.String(150))
    tahun_berdiri = db.Column(db.String(10))
    
    # Alamat
    alamat_jalan = db.Column(db.String(255))
    alamat_rtrw = db.Column(db.String(50))
    alamat_desa = db.Column(db.String(100))
    alamat_kecamatan = db.Column(db.String(100))
    alamat_kabkota = db.Column(db.String(100))
    alamat_provinsi = db.Column(db.String(100))
    kode_pos = db.Column(db.String(20))
    
    # Kontak
    no_telp = db.Column(db.String(50))
    email_web = db.Column(db.String(100))
    
    # Legalitas
    ijin_usaha = db.Column(db.String(255))
    haki = db.Column(db.String(255))
    merk_dagang = db.Column(db.String(100))
    
    # SDM
    tk_tetap = db.Column(db.Integer, default=0)
    tk_tidak_tetap = db.Column(db.Integer, default=0)
    
    # II & III. KAPASITAS, TEKNOLOGI, PEMASARAN, KOMITMEN (JSON String)
    # Ini menampung sisa isian formulir yang tebal agar tidak terjadi kolom null raksasa
    detil_industri = db.Column(db.Text, default="{}")
    
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())
