from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DateField, FloatField, SelectField, IntegerField, RadioField, TextAreaField
from wtforms.validators import DataRequired, Length, EqualTo, Regexp
from flask_wtf.file import FileField, FileRequired, FileAllowed
from datetime import date

class LoginForm(FlaskForm):
    """Form Login Pengguna UMKM."""
    username = StringField('Nama Pengguna', validators=[
        DataRequired(message="Nama pengguna tidak boleh kosong.")
    ])
    password = PasswordField('Kata Sandi', validators=[
        DataRequired(message="Kata sandi tidak boleh kosong.")
    ])
    submit = SubmitField('Masuk ke Akun Saya')

class RegisterForm(FlaskForm):
    """Form Pendaftaran Pengguna UMKM Baru yang aman."""
    username = StringField('Nama Pengguna Terdaftar', validators=[
        DataRequired(message="Nama pengguna tidak boleh kosong."),
        Length(min=4, max=50, message="Nama pengguna harus 4-50 karakter."),
        Regexp(r'^\w+$', message="Gunakan hanya huruf, angka, atau garis bawah.")
    ])
    password = PasswordField('Kata Sandi Baru', validators=[
        DataRequired(message="Kata sandi tidak boleh kosong."),
        Length(min=6, message="Kata sandi minimal 6 karakter demi keamanan.")
    ])
    confirm_password = PasswordField('Ulangi Kata Sandi', validators=[
        DataRequired(message="Ulangi kembali kata sandi di atas."),
        EqualTo('password', message="Kata sandi yang Anda masukkan tidak cocok.")
    ])
    submit = SubmitField('Daftar Akun Baru')

class TransaksiForm(FlaskForm):
    """Form Pencatatan Transaksi Manual."""
    tanggal = DateField('Tanggal', format='%Y-%m-%d', default=date.today, validators=[DataRequired("Tanggal tidak boleh kosong.")])
    kategori = SelectField('Kategori Penjualan', choices=[
        ('Makanan & Minuman', 'Makanan & Minuman'),
        ('Retail', 'Retail (Barang Jadi)'),
        ('Jasa', 'Layanan Jasa'),
        ('Lainnya', 'Lainnya')
    ], validators=[DataRequired("Kategori wajib dipilih.")])
    # Menggunakan FloatField yang akan dimanipulasi di JS untuk mask rupiah
    pemasukan = FloatField('Total Pemasukan (Rp)', default=0, validators=[DataRequired("Harus mengisi pemasukan. Isi 0 jika nihil.")])
    pengeluaran = FloatField('Total Pengeluaran (Rp)', default=0, validators=[DataRequired("Harus mengisi pengeluaran. Isi 0 jika nihil.")])
    jenis_pengeluaran = RadioField('Jenis Pengeluaran', choices=[('operasional', 'Operasional'), ('modal', 'Modal')], default='operasional')
    jumlah_pelanggan = IntegerField('Jumlah Pelanggan', default=0)
    catatan = TextAreaField('Catatan Hari Ini (Opsional)', validators=[Length(max=200, message="Maksimal 200 karakter.")])
    submit = SubmitField('Simpan Transaksi')

class UploadCSVForm(FlaskForm):
    """Form Pengunggahan Laporan CSV."""
    file_csv = FileField('Pilih File Laporan (.csv)', validators=[
        FileRequired(message="Anda belum memilih file CSV."),
        FileAllowed(['csv'], message="Mohon pastikan format file yang diunggah adalah .csv")
    ])
    submit = SubmitField('Unggah File Ini')

class BukuKasForm(FlaskForm):
    """Form untuk Membuat / Mengelola Pemisahan File Laporan Proyek."""
    nama_buku = StringField('Nama Buku Kas Baru', validators=[
        DataRequired(message="Nama buku kas tidak boleh kosong."),
        Length(max=100, message="Nama buku kas maksimal 100 karakter.")
    ])
    submit = SubmitField('Buat Buku Kas')
