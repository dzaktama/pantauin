import os
import csv
import io
from datetime import datetime, date, timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

from config import Config
from models import db, User, Transaksi, BukuKas, ProfilPerusahaan
from forms import LoginForm, RegisterForm, TransaksiForm, BukuKasForm, UploadCSVForm, ProfilPerusahaanForm
from flask_caching import Cache
import json
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

from calculator import hitung_health_score
import gemini_helper
from pdf_generator import generate_pdf_report

# Ekstensi
cache = Cache()
limiter = Limiter(key_func=get_remote_address)
csrf = CSRFProtect()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    cache.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)

    with app.app_context():
        db.create_all()

    # --- ERROR HANDLERS ---
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('error.html', pesan="Halaman rute tidak ditemukan."), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('error.html', pesan="Gagal memproses permintaan, server sedang sibuk."), 500

    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash("Silakan masuk menggunakan akun Anda terlebih dahulu.", "warning")
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    @app.context_processor
    def inject_buku_kas():
        if 'user_id' in session:
            daftar_buku = BukuKas.query.filter_by(user_id=session['user_id']).order_by(BukuKas.created_at.asc()).all()
            # Set default session ID jika kosong namun user memiliki buku
            if 'buku_kas_id' not in session and daftar_buku:
                session['buku_kas_id'] = daftar_buku[0].id
            
            buku_aktif = next((b for b in daftar_buku if b.id == session.get('buku_kas_id')), None)
            return dict(daftar_buku=daftar_buku, buku_kas_aktif=buku_aktif)
        return dict(daftar_buku=[], buku_kas_aktif=None)

    # --- AUTH ROUTES ---
    @app.route('/', methods=['GET'])
    def index():
        if 'user_id' in session: return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        try:
            form = LoginForm()
            if form.validate_on_submit():
                user = User.query.filter_by(username=form.username.data).first()
                if user and user.check_password(form.password.data):
                    session['user_id'] = user.id
                    session['username'] = user.username
                    flash(f"Halo kembali, {user.username}!", "success")
                    return redirect(url_for('dashboard'))
                flash("Kredensial tidak cocok, silakan coba lagi.", "error")
            return render_template('login.html', form=form)
        except Exception:
            return render_template('error.html', pesan="Terjadi kesalahan saat masuk."), 500

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        try:
            form = RegisterForm()
            if form.validate_on_submit():
                if User.query.filter_by(username=form.username.data).first():
                    flash("Nama pengguna ini sudah dipakai.", "error")
                    return render_template('register.html', form=form)
                
                u = User(username=form.username.data)
                u.set_password(form.password.data)
                db.session.add(u)
                db.session.flush() # flush agar mendapatkan u.id

                # Buat Buku Kas Pertama Secara Otomatis
                bk = BukuKas(user_id=u.id, nama_buku="Buku Kas Utama")
                db.session.add(bk)
                
                db.session.commit()
                flash("Sukses mendaftar! Yuk mulai sesi barumu.", "success")
                return redirect(url_for('login'))
            return render_template('register.html', form=form)
        except Exception:
            db.session.rollback()
            return render_template('error.html', pesan="Permintaan ditolak."), 500

    @app.route('/logout', methods=['POST'])
    @login_required
    def logout():
        session.clear()
        return redirect(url_for('login'))

    # --- PROJECT (BUKU KAS) ROUTES ---
    @app.route('/buku-kas', methods=['GET', 'POST'])
    @login_required
    def buku_kas_manager():
        form = BukuKasForm()
        if form.validate_on_submit():
            bk = BukuKas(user_id=session['user_id'], nama_buku=form.nama_buku.data)
            db.session.add(bk)
            db.session.commit()
            flash(f"Buku Kas '{bk.nama_buku}' berhasil dibuat!", "success")
            return redirect(url_for('buku_kas_manager'))
            
        return render_template('buku_kas.html', form=form)

    @app.route('/buku-kas/switch/<int:buku_id>', methods=['POST'])
    @login_required
    def switch_buku_kas(buku_id):
        bk = BukuKas.query.filter_by(id=buku_id, user_id=session['user_id']).first_or_404()
        session['buku_kas_id'] = bk.id
        
        # Tangkap parameter destinasi dari tombol yang diklik
        destination = request.form.get('destination', 'dashboard')
        flash(f"Berpindah ke proyek: {bk.nama_buku}", "info")
        
        if destination == 'input':
            return redirect(url_for('input_transaksi'))
        elif destination == 'riwayat':
            return redirect(url_for('riwayat_transaksi'))
        else:
            return redirect(url_for('dashboard'))

    @app.route('/buku-kas/reset/<int:buku_id>', methods=['POST'])
    @login_required
    def reset_buku_kas(buku_id):
        # Pastikan user pemilik asli buku kas
        bk = BukuKas.query.filter_by(id=buku_id, user_id=session['user_id']).first_or_404()
        
        try:
            # Hapus semua transaksi massal
            jumlah_dihapus = Transaksi.query.filter_by(buku_kas_id=bk.id).delete()
            db.session.commit()
            
            # Bersihkan cache kalkulator jika buku sedang aktif
            if session.get('buku_kas_id') == bk.id:
                cache.clear()
                
            flash(f"Data Transaksi pada Buku '{bk.nama_buku}' ({jumlah_dihapus} baris) berhasil dikosongkan. Profil Perusahaan tetap aman.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Gagal mengosongkan data transaksi: {str(e)}", "danger")
            
        return redirect(url_for('buku_kas_manager'))

    # --- CORE ROUTES ---
    @app.route('/dashboard')
    @login_required
    def dashboard():
        try:
            buku_kas_id = session.get('buku_kas_id')
            if not buku_kas_id: 
                return redirect(url_for('buku_kas_manager'))
            
            # Wajib isi profil perusahaan jika belum
            profil = ProfilPerusahaan.query.filter_by(buku_kas_id=buku_kas_id).first()
            if not profil:
                flash("Isi profil perusahaan usahamu terlebih dahulu sebelum menjelajah dasbor.", "warning")
                return redirect(url_for('edit_profil_perusahaan'))
            
            # Filter Parameter Periode Dashboard
            periode = request.args.get('periode', 30, type=int)
            if periode not in [30, 60, 90]:
                periode = 30
                
            cache_key = f"dashboard_bk_{buku_kas_id}_{periode}_{datetime.now().strftime('%Y%m%d')}_v3"
            data = cache.get(cache_key)
            saran_gemini = cache.get(f"saran_bk_{buku_kas_id}")

            if data is None or saran_gemini is None:
                transaksi_list = Transaksi.query.filter_by(buku_kas_id=buku_kas_id).order_by(Transaksi.tanggal.asc()).all()
                data = hitung_health_score(transaksi_list, periode_grafik=periode)
                
                # Panggil Gemini jika data valid
                if data['is_cukup']:
                    saran_gemini = gemini_helper.get_dashboard_suggestion(
                        data['skor'], data['total_pemasukan_minggu_ini'], 
                        data['total_pengeluaran_minggu_ini'], data['tren_status'],
                        data.get('catatan_mingguan', [])
                    )
                else:
                    saran_gemini = "Saran belum tersedia. Lengkapi pencatatan laporan buku ini setidaknya 14 hari."

                cache.set(cache_key, data)
                cache.set(f"saran_bk_{buku_kas_id}", saran_gemini)

            return render_template('dashboard.html', data=data, saran_gemini=saran_gemini)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return render_template('error.html', pesan=f"Gagal merender dasbor analisis! Detail: {str(e)}"), 500

    @app.route('/profil-perusahaan', methods=['GET', 'POST'])
    @login_required
    def edit_profil_perusahaan():
        buku_kas_id = session.get('buku_kas_id')
        if not buku_kas_id: return redirect(url_for('buku_kas_manager'))
            
        buku_aktif = BukuKas.query.get_or_404(buku_kas_id)
        profil = ProfilPerusahaan.query.filter_by(buku_kas_id=buku_kas_id).first()
        
        form = ProfilPerusahaanForm(obj=profil)
        
        if request.method == 'GET' and profil and profil.detil_industri:
            try:
                dt_extr = json.loads(profil.detil_industri)
                form.jenis_produk.data = dt_extr.get('jenis_produk', '')
                form.kapasitas_produksi.data = dt_extr.get('kapasitas_produksi', '')
                form.omzet_usaha.data = dt_extr.get('omzet_usaha', '')
                form.teknologi_produksi.data = dt_extr.get('teknologi_produksi', '')
                form.teknologi_pengemasan.data = dt_extr.get('teknologi_pengemasan', '')
                form.bahan_baku_asal.data = dt_extr.get('bahan_baku_asal', '')
                form.bahan_baku_ketersediaan.data = dt_extr.get('bahan_baku_ketersediaan', '')
                form.desain_produk.data = dt_extr.get('desain_produk', '')
                form.kemasan_bahan.data = dt_extr.get('kemasan_bahan', '')
                form.kemasan_desain.data = dt_extr.get('kemasan_desain', '')
                form.segmen_pasar.data = dt_extr.get('segmen_pasar', '')
                form.daerah_pemasaran.data = dt_extr.get('daerah_pemasaran', '')
                form.wilayah_pemasaran.data = dt_extr.get('wilayah_pemasaran', '')
                form.sistem_penjualan.data = dt_extr.get('sistem_penjualan', '')
                form.komitmen.data = dt_extr.get('komitmen', '')
            except:
                pass

        if form.validate_on_submit():
            dt_extr = {
                'jenis_produk': form.jenis_produk.data,
                'kapasitas_produksi': form.kapasitas_produksi.data,
                'omzet_usaha': form.omzet_usaha.data,
                'teknologi_produksi': form.teknologi_produksi.data,
                'teknologi_pengemasan': form.teknologi_pengemasan.data,
                'bahan_baku_asal': form.bahan_baku_asal.data,
                'bahan_baku_ketersediaan': form.bahan_baku_ketersediaan.data,
                'desain_produk': form.desain_produk.data,
                'kemasan_bahan': form.kemasan_bahan.data,
                'kemasan_desain': form.kemasan_desain.data,
                'segmen_pasar': form.segmen_pasar.data,
                'daerah_pemasaran': form.daerah_pemasaran.data,
                'wilayah_pemasaran': form.wilayah_pemasaran.data,
                'sistem_penjualan': form.sistem_penjualan.data,
                'komitmen': form.komitmen.data
            }
            
            if not profil:
                profil = ProfilPerusahaan(buku_kas_id=buku_kas_id)
                db.session.add(profil)
            
            form.populate_obj(profil)
            profil.detil_industri = json.dumps(dt_extr)
            profil.buku_kas_id = buku_kas_id
            
            db.session.commit()
            flash("Profil Perusahaan berhasil disimpan!", "success")
            return redirect(url_for('dashboard'))
            
        return render_template('profil_perusahaan.html', form=form, nama_buku=buku_aktif.nama_buku)

    @app.route('/input', methods=['GET', 'POST'])
    @login_required
    def input_transaksi():
        try:
            buku_kas_id = session.get('buku_kas_id')
            if not buku_kas_id: return redirect(url_for('buku_kas_manager'))
            
            form = TransaksiForm()
            if form.validate_on_submit():
                t = Transaksi(
                    user_id=session['user_id'],
                    buku_kas_id=buku_kas_id,
                    tanggal=form.tanggal.data,
                    kategori=form.kategori.data,
                    jenis_pengeluaran=form.jenis_pengeluaran.data,
                    pemasukan=form.pemasukan.data,
                    pengeluaran=form.pengeluaran.data,
                    jumlah_pelanggan=form.jumlah_pelanggan.data,
                    catatan=form.catatan.data if form.catatan.data else None
                )
                db.session.add(t)
                db.session.commit()
                # Invalidate cache
                cache.delete(f"dashboard_bk_{buku_kas_id}_30_{datetime.now().strftime('%Y%m%d')}_v3")
                cache.delete(f"dashboard_bk_{buku_kas_id}_60_{datetime.now().strftime('%Y%m%d')}_v3")
                cache.delete(f"dashboard_bk_{buku_kas_id}_90_{datetime.now().strftime('%Y%m%d')}_v3")
                cache.delete(f"saran_bk_{buku_kas_id}")
                flash("Sip, Transaksi berhasil dicatat!", "success")
                return redirect(url_for('input_transaksi'))
            
            # Ambil Riwayat 15 Transaksi Terakhir untuk Tabel Transparansi
            riwayat = Transaksi.query.filter_by(buku_kas_id=buku_kas_id).order_by(Transaksi.tanggal.desc()).limit(15).all()
            return render_template('input.html', form=form, riwayat=riwayat)
        except Exception:
            db.session.rollback()
            return render_template('error.html', pesan="Gagal menyimpan/memuat transaksi manual."), 500

    @app.route('/riwayat', methods=['GET'])
    @login_required
    def riwayat():
        try:
            buku_kas_id = session.get('buku_kas_id')
            if not buku_kas_id: return redirect(url_for('buku_kas_manager'))
            
            q = request.args.get('q', '').strip()
            page = request.args.get('page', 1, type=int)
            query = Transaksi.query.filter_by(buku_kas_id=buku_kas_id)
            
            if q:
                query = query.filter(db.or_(
                    Transaksi.catatan.ilike(f"%{q}%"),
                    Transaksi.kategori.ilike(f"%{q}%")
                ))
            
            # Paginasi SQLite ringan (20 baris per halaman)
            pagination = query.order_by(Transaksi.tanggal.desc()).paginate(page=page, per_page=20, error_out=False)
            
            return render_template('riwayat.html', pagination=pagination, q=q)
        except Exception as e:
            return render_template('error.html', pesan=f"Gagal memuat halaman master data. Detail: {str(e)}"), 500

    @app.route('/upload', methods=['GET', 'POST'])
    @login_required
    def upload_csv():
        try:
            buku_kas_id = session.get('buku_kas_id')
            if not buku_kas_id: return redirect(url_for('buku_kas_manager'))
            
            form = UploadCSVForm()
            if form.validate_on_submit():
                # Dapatkan array multi-files dari input OS
                files = request.files.getlist(form.file_csv.name)
                sukses = 0
                
                for file in files:
                    if not file.filename.endswith('.csv'): continue
                    stream = io.StringIO(file.stream.read().decode('utf-8'))
                    reader = csv.DictReader(stream)
                    
                    # Validasi Kolom
                    k_wajib = {'tanggal', 'kategori', 'pemasukan', 'pengeluaran', 'jumlah_pelanggan'}
                    if not k_wajib.issubset(set(reader.fieldnames or [])):
                        flash(f"Kolom CSV '{file.filename}' tidak lengkap. Diabaikan.", "error")
                        continue

                    # Penggabungan Multiple CSV: Tidak Menghapus Transaksi Lama
                    for row in reader:
                        # Lewati baris kosong
                        if not row['tanggal']: continue
                        try:
                            t = Transaksi(
                                user_id=session['user_id'],
                                buku_kas_id=buku_kas_id,
                                tanggal=datetime.strptime(row['tanggal'], '%Y-%m-%d').date(),
                                kategori=row.get('kategori', 'Lainnya'),
                                jenis_pengeluaran=row.get('jenis_pengeluaran', 'operasional').lower() if row.get('jenis_pengeluaran') else 'operasional',
                                pemasukan=float(row.get('pemasukan') or 0),
                                pengeluaran=float(row.get('pengeluaran') or 0),
                                jumlah_pelanggan=int(row.get('jumlah_pelanggan') or 0),
                                catatan=row.get('catatan') or None
                            )
                            if t.jenis_pengeluaran not in ['operasional', 'modal']:
                                t.jenis_pengeluaran = 'operasional'
                            db.session.add(t)
                            sukses += 1
                        except ValueError:
                            pass # Skip baris malformed
                        
                db.session.commit()
                cache.delete(f"dashboard_bk_{buku_kas_id}_30_{datetime.now().strftime('%Y%m%d')}_v3")
                cache.delete(f"dashboard_bk_{buku_kas_id}_60_{datetime.now().strftime('%Y%m%d')}_v3")
                cache.delete(f"dashboard_bk_{buku_kas_id}_90_{datetime.now().strftime('%Y%m%d')}_v3")
                cache.delete(f"saran_bk_{buku_kas_id}")
                flash(f"Berhasil menggabungkan {sukses} baris transaksi ke Buku Kas ini.", "success")
                return redirect(url_for('dashboard'))

            return render_template('upload.html', form=form)
        except Exception:
            db.session.rollback()
            return render_template('error.html', pesan="File CSV rusak atau berekstensi asing."), 500

    @app.route('/download-template', methods=['GET'])
    @login_required
    def download_template():
        content = "tanggal,kategori,pemasukan,pengeluaran,jenis_pengeluaran,jumlah_pelanggan,catatan\n" \
                  "2026-03-01,Makanan & Minuman,500000,200000,operasional,15,Hari hujan rintik\n" \
                  "2026-03-02,Retail,1500000,4500000,modal,5,Beli stok grosir baru\n"
        return send_file(io.BytesIO(content.encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='Template_PANTAUIN.csv')

    @app.route('/simulator', methods=['GET'])
    @login_required
    def simulator():
        return render_template('simulator.html')

    # --- API ENDPOINTS (RATE LIMITED & CSRF PROTECTED) ---
    @app.route('/api/simulator', methods=['POST'])
    @login_required
    @limiter.limit("30 per minute")
    def api_simulator():
        """Menghitung proyeksi mingguan berdasarkan persen penurunan pemasukan."""
        try:
            buku_kas_id = session.get('buku_kas_id')
            if not buku_kas_id: return jsonify({"error": "Pilih buku kas terlebih dahulu."}), 400
            
            req = request.get_json()
            persen = float(req.get('penurunan_persen', 0)) / 100
            
            baseline = cache.get(f"dashboard_bk_{buku_kas_id}_30_{datetime.now().strftime('%Y%m%d')}_v3")
            if not baseline:
                t_list = Transaksi.query.filter_by(buku_kas_id=buku_kas_id).order_by(Transaksi.tanggal.asc()).all()
                baseline = hitung_health_score(t_list, periode_grafik=30)

            # Kalkulasi manual cepat
            in_baru = baseline['total_pemasukan_minggu_ini'] * (1 - persen)
            # Asumsi default: pengeluaran sulit turun (fixed cost dominan)
            out_baru = baseline['total_pengeluaran_minggu_ini'] 
            saldo_baru = in_baru - out_baru
            
            saran = "Aman, masih ada margin untung di batas ini." if saldo_baru >= 0 else ("Awas, Anda akan rugi! Siapkan dana darurat Rp " + str(abs(int(saldo_baru))))
            if persen == 0: saran = "Kondisi awal sesuai transaksi mingguanmu."

            return jsonify({
                "pemasukan_baru": in_baru,
                "pengeluaran_baru": out_baru,
                "saldo_baru": saldo_baru,
                "saran": saran
            })
        except Exception:
            return jsonify({"error": "Gagal simulasi"}), 500

    @app.route('/api/chatbot', methods=['POST'])
    @login_required
    @limiter.limit("15 per minute") 
    def api_chatbot():
        try:
            pesan_user = request.get_json().get('message', '')
            
            buku_kas_id = session.get('buku_kas_id')
            if not buku_kas_id: return jsonify({"reply": "Anda belum memilih Proyek/Buku Kas."})
            
            cache_key = f"dashboard_bk_{buku_kas_id}_30_{datetime.now().strftime('%Y%m%d')}_v3"
            konteks = cache.get(cache_key)
            if not konteks:
                t_list = Transaksi.query.filter_by(buku_kas_id=buku_kas_id).order_by(Transaksi.tanggal.asc()).all()
                konteks = hitung_health_score(t_list, periode_grafik=30)
                cache.set(cache_key, konteks)
            
            reply = gemini_helper.get_chatbot_response(pesan_user, konteks)
            return jsonify({"reply": reply})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"reply": f"AI Kelebihan beban detail: {str(e)}"}), 500

    @app.route('/unduh-laporan', methods=['GET', 'POST'])
    @login_required
    def download_report():
        try:
            buku_kas_id = session.get('buku_kas_id')
            if not buku_kas_id: return redirect(url_for('buku_kas_manager'))
            
            # Wajib isi profil perusahaan jika belum (untuk dicetak)
            profil = ProfilPerusahaan.query.filter_by(buku_kas_id=buku_kas_id).first()
            if not profil:
                flash("Isi profil perusahaan usahamu terlebih dahulu sebelum mencetak Laporan Utama.", "warning")
                return redirect(url_for('edit_profil_perusahaan'))
                
            cache_key = f"dashboard_bk_{buku_kas_id}_30_{datetime.now().strftime('%Y%m%d')}_v3"
            data = cache.get(cache_key)
            if not data:
                t_list = Transaksi.query.filter_by(buku_kas_id=buku_kas_id).order_by(Transaksi.tanggal.asc()).all()
                data = hitung_health_score(t_list, periode_grafik=30)
                cache.set(cache_key, data)

            if not data.get('is_cukup'):
                flash("Anda belum memiliki cukup data transaksi untuk dicetak pada Buku Kas ini (minimal 14 hari).", "warning")
                return redirect(url_for('dashboard'))
                
            buku_aktif = BukuKas.query.get(buku_kas_id)
            nama_proyek = profil.nama_perusahaan if profil and profil.nama_perusahaan else (buku_aktif.nama_buku if buku_aktif else session['username'])
            
            # Ambil narasi AI dari cache yang pernah dirender dashboard
            saran_gemini = cache.get(f"saran_bk_{buku_kas_id}") or "Hasil analitik AI belum tesedia, silakan generate ulang dashboard."
            
            if request.method == 'POST':
                # Tangkap Opsi Kustomisasi
                teks_ai_diedit = request.form.get('narasi_ai', saran_gemini)
                lampir_profil = request.form.get('lampir_profil', 'off') == 'on'
                lampir_proyeksi = request.form.get('lampir_proyeksi', 'off') == 'on'
                
                base_dir = os.path.abspath(os.path.dirname(__file__))
                output_file = os.path.join(base_dir, f'Laporan_PANTAUIN_{int(datetime.now().timestamp())}.pdf')
                
                # Fetch Profil Detil untuk dilempar ke Generator bila lampir disetujui
                profil_dict = None
                if lampir_profil and profil:
                    try:
                        dt_ekstra = json.loads(profil.detil_industri) if profil.detil_industri else {}
                    except: dt_ekstra = {}
                    profil_dict = {
                        'entitas': profil.nama_perusahaan,
                        'contact_person': profil.contact_person,
                        'jabatan': profil.jabatan,
                        'bentuk_usaha': profil.bentuk_usaha,
                        'tahun_berdiri': profil.tahun_berdiri,
                        'alamat': f"{profil.alamat_jalan}, {profil.alamat_rtrw}, {profil.alamat_desa}, {profil.alamat_kecamatan}, {profil.alamat_kabkota}, {profil.alamat_provinsi} {profil.kode_pos}",
                        'kontak': f"{profil.no_telp} / {profil.email_web}",
                        'legalitas': f"Ijin: {profil.ijin_usaha} | HAKI: {profil.haki}",
                        'tk': f"Tetap: {profil.tk_tetap}, Tidak Tetap: {profil.tk_tidak_tetap}",
                        'kapasitas': dt_ekstra.get('kapasitas_produksi', '-'),
                        'omzet': dt_ekstra.get('omzet_usaha', '-'),
                        'bahan_baku': f"Asal: {dt_ekstra.get('bahan_baku_asal', '-')} ({dt_ekstra.get('bahan_baku_ketersediaan', '')})",
                        'pasar': dt_ekstra.get('segmen_pasar', '-'),
                        'wilayah': dt_ekstra.get('wilayah_pemasaran', '-')
                    }
                
                # Panggil fungsi report lab
                generate_pdf_report(
                    user_name=nama_proyek, 
                    score=data['skor'], 
                    avg_in=data['rata_pemasukan'], 
                    avg_out=data['rata_pengeluaran'], 
                    warnings=data['peringatan'], 
                    catatan_mingguan=data.get('catatan_mingguan', []), 
                    output_path=output_file,
                    breakdown=data.get('rincian_skor', {}),
                    stat_4_minggu=data.get('statistik_4_minggu', []),
                    proyeksi=data.get('grafik_proyeksi', []),
                    proyeksi_pengeluaran=data.get('proyeksi_pengeluaran', []),
                    tgl_cetak_dt=datetime.now(),
                    tgl_mulai_dt=date.today() - timedelta(days=30),
                    tgl_akhir_dt=date.today(),
                    # Parameter Argumen Kustom
                    kustom_teks_ai=teks_ai_diedit,
                    lampir_proyeksi=lampir_proyeksi,
                    profil_dict=profil_dict # Jika None, generator akan skip bab Profil Perusahaan
                )
                action_type = request.form.get('action', 'download')
                
                if action_type == 'preview':
                    return send_file(output_file, as_attachment=False, mimetype='application/pdf')
                else:
                    return send_file(output_file, as_attachment=True, download_name=f"PANTAUIN_Kustom_{date.today()}_{nama_proyek.replace(' ', '_')}.pdf")
            
            # Jika GET -> Render Preview Halaman Customize
            return render_template('laporan_kustom.html', nama_buku=nama_proyek, teks_ai=saran_gemini)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return render_template('error.html', pesan=f"Gagal memproses File Laporan: {str(e)}"), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5050)
