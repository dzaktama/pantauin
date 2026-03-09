import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import Flowable


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def format_tanggal_indonesia(dt):
    hari  = ["Senin","Selasa","Rabu","Kamis","Jumat","Sabtu","Minggu"]
    bulan = ["","Januari","Februari","Maret","April","Mei","Juni",
             "Juli","Agustus","September","Oktober","November","Desember"]
    return f"{hari[dt.weekday()]}, {dt.day} {bulan[dt.month]} {dt.year}"

def _bulan(n):
    return ["","Januari","Februari","Maret","April","Mei","Juni",
            "Juli","Agustus","September","Oktober","November","Desember"][n]

def _fmt_rp(nilai):
    return f"Rp {int(nilai):,}".replace(",",".")

def _tgl(dt):
    return f"{dt.day} {_bulan(dt.month)} {dt.year}"

# ──────────────────────────────────────────────
# RISK ENGINE  (pure-rules, no AI language)
# ──────────────────────────────────────────────

def _hitung_risiko(score, breakdown, val_in_30, val_op_30, val_saldo_30,
                   avg_in, avg_out, gross_margin_pct, warnings, proy_arr):
    """
    Menghasilkan dict profil risiko untuk keperluan pengajuan kredit.
    Skala risiko: 1 (Sangat Rendah) – 5 (Sangat Tinggi)
    """
    risiko = {}

    # 1. Risiko Likuiditas
    dana_darurat_ideal = avg_out * 14          # 2 minggu operasional
    coverage           = val_saldo_30 / dana_darurat_ideal if dana_darurat_ideal > 0 else 0
    if   coverage >= 2.0: r_liq = 1
    elif coverage >= 1.0: r_liq = 2
    elif coverage >= 0.5: r_liq = 3
    elif coverage >= 0.0: r_liq = 4
    else:                 r_liq = 5
    risiko["likuiditas"] = {
        "skor": r_liq,
        "coverage": coverage,
        "dana_tersedia": val_saldo_30,
        "dana_ideal": dana_darurat_ideal,
        "keterangan": _liq_ket(r_liq, coverage, val_saldo_30, dana_darurat_ideal)
    }

    # 2. Risiko Profitabilitas
    rasio_op = (val_op_30 / val_in_30 * 100) if val_in_30 > 0 else 100
    if   gross_margin_pct >= 50 and rasio_op <= 50: r_profit = 1
    elif gross_margin_pct >= 35 and rasio_op <= 65: r_profit = 2
    elif gross_margin_pct >= 20 and rasio_op <= 80: r_profit = 3
    elif gross_margin_pct >= 10:                    r_profit = 4
    else:                                           r_profit = 5
    risiko["profitabilitas"] = {
        "skor": r_profit,
        "gross_margin": gross_margin_pct,
        "rasio_operasional": rasio_op,
        "keterangan": _profit_ket(r_profit, gross_margin_pct, rasio_op)
    }

    # 3. Risiko Arus Kas (cashflow volatility)
    tren  = breakdown.get("tren", 0)
    stab  = breakdown.get("stabilitas", 0)
    kons  = breakdown.get("konsistensi", 0)
    avg_cf = (tren + stab + kons) / 3
    if   avg_cf >= 80: r_cf = 1
    elif avg_cf >= 65: r_cf = 2
    elif avg_cf >= 50: r_cf = 3
    elif avg_cf >= 35: r_cf = 4
    else:              r_cf = 5
    risiko["arus_kas"] = {
        "skor": r_cf,
        "stabilitas": stab,
        "tren": tren,
        "konsistensi": kons,
        "keterangan": _cf_ket(r_cf, avg_cf)
    }

    # 4. Risiko Proyeksi (forward-looking)
    neg_weeks = sum(1 for (_,_,_,s) in proy_arr if s < 0)
    if   neg_weeks == 0: r_proj = 1
    elif neg_weeks == 1: r_proj = 2
    elif neg_weeks == 2: r_proj = 3
    elif neg_weeks == 3: r_proj = 4
    else:                r_proj = 5
    risiko["proyeksi"] = {
        "skor": r_proj,
        "minggu_negatif": neg_weeks,
        "keterangan": _proj_ket(r_proj, neg_weeks)
    }

    # 5. Risiko Kepatuhan Data
    n_warn = len(warnings)
    if   n_warn == 0: r_data = 1
    elif n_warn == 1: r_data = 2
    elif n_warn <= 3: r_data = 3
    elif n_warn <= 5: r_data = 4
    else:             r_data = 5
    risiko["kepatuhan"] = {
        "skor": r_data,
        "jumlah_peringatan": n_warn,
        "keterangan": _data_ket(r_data, n_warn)
    }

    # ── Composite Risk Rating ──
    bobot = {"likuiditas":0.30,"profitabilitas":0.25,"arus_kas":0.25,
             "proyeksi":0.15,"kepatuhan":0.05}
    composite = sum(risiko[k]["skor"] * bobot[k] for k in bobot)
    if   composite <= 1.5: label, warna = "SANGAT RENDAH", "AAA"
    elif composite <= 2.2: label, warna = "RENDAH",        "AA"
    elif composite <= 3.0: label, warna = "MODERAT",       "BBB"
    elif composite <= 3.8: label, warna = "TINGGI",        "BB"
    else:                  label, warna = "SANGAT TINGGI", "CCC"

    risiko["composite"] = {
        "skor": round(composite, 2),
        "label": label,
        "rating": warna
    }
    return risiko


def _liq_ket(r, cov, ada, ideal):
    if r == 1: return f"Dana operasional sangat mencukupi ({cov:.1f}x dari kebutuhan cadangan ideal)."
    if r == 2: return f"Dana cadangan memadai, menutup {cov:.1f}x kebutuhan operasional 2 minggu."
    if r == 3: return f"Dana cadangan terbatas, hanya {cov:.1f}x kebutuhan minimum. Perlu penguatan."
    if r == 4: return f"Dana cadangan di bawah standar minimum. Rentan terhadap gangguan operasional."
    return        f"Dana cadangan tidak mencukupi. Risiko gagal bayar kewajiban jangka pendek tinggi."

def _profit_ket(r, gm, ro):
    if r == 1: return f"Profitabilitas sangat baik. Gross margin {gm:.1f}%, rasio beban operasional {ro:.1f}%."
    if r == 2: return f"Profitabilitas baik. Gross margin {gm:.1f}%, pengendalian biaya cukup efisien."
    if r == 3: return f"Profitabilitas moderat. Gross margin {gm:.1f}% perlu ditingkatkan agar lebih efisien."
    if r == 4: return f"Profitabilitas rendah. Gross margin {gm:.1f}% mengindikasikan tekanan margin."
    return        f"Profitabilitas sangat rendah. Risiko kerugian operasional berkelanjutan."

def _cf_ket(r, avg):
    if r == 1: return "Arus kas sangat stabil dan konsisten. Mencerminkan kualitas manajemen keuangan yang baik."
    if r == 2: return "Arus kas stabil dengan variasi minor yang dapat diterima."
    if r == 3: return "Arus kas cukup stabil namun terdapat volatilitas yang perlu dipantau."
    if r == 4: return "Arus kas tidak stabil. Fluktuasi tinggi berisiko mengganggu kemampuan membayar kewajiban."
    return        "Arus kas sangat tidak stabil. Risiko default jangka pendek perlu diantisipasi."

def _proj_ket(r, neg):
    if r == 1: return "Proyeksi 4 minggu ke depan seluruhnya positif. Kemampuan bayar terjaga."
    if r == 2: return f"Proyeksi menunjukkan {neg} minggu dengan arus kas negatif. Perlu pemantauan."
    if r == 3: return f"Proyeksi menunjukkan {neg} minggu negatif. Diperlukan penyesuaian pengeluaran."
    if r == 4: return f"Proyeksi menunjukkan {neg} minggu negatif. Risiko likuiditas jangka dekat signifikan."
    return        "Seluruh proyeksi menunjukkan arus kas negatif. Diperlukan intervensi segera."

def _data_ket(r, n):
    if r == 1: return "Tidak ditemukan anomali data. Laporan keuangan konsisten dan lengkap."
    if r == 2: return f"Ditemukan {n} peringatan minor yang perlu ditindaklanjuti."
    if r == 3: return f"Ditemukan {n} peringatan. Terdapat ketidakkonsistenan data yang perlu dijelaskan."
    if r == 4: return f"Ditemukan {n} peringatan. Kualitas data berpengaruh terhadap akurasi penilaian."
    return        f"Ditemukan {n} peringatan serius. Validasi ulang data keuangan sangat disarankan."


# ──────────────────────────────────────────────
# CUSTOM FLOWABLE: Horizontal Risk Bar
# ──────────────────────────────────────────────

class RiskBar(Flowable):
    """Menggambar progress bar risiko 1–5."""
    def __init__(self, skor, width=120, height=10):
        super().__init__()
        self.skor   = skor
        self.width  = width
        self.height = height

    def wrap(self, *args):
        return (self.width, self.height + 4)

    def draw(self):
        c = self.canv
        pct = (self.skor - 1) / 4          # 1→0%, 5→100%

        if   pct <= 0.25: fill = colors.HexColor("#27AE60")
        elif pct <= 0.50: fill = colors.HexColor("#F39C12")
        elif pct <= 0.75: fill = colors.HexColor("#E67E22")
        else:             fill = colors.HexColor("#C0392B")

        # Background track
        c.setFillColor(colors.HexColor("#E8E8E8"))
        c.roundRect(0, 2, self.width, self.height, 3, fill=1, stroke=0)

        # Fill
        fill_w = max(int(self.width * pct), 12)
        c.setFillColor(fill)
        c.roundRect(0, 2, fill_w, self.height, 3, fill=1, stroke=0)


# ──────────────────────────────────────────────
# MAIN GENERATOR
# ──────────────────────────────────────────────

def generate_pdf_report(
    user_name, score, avg_in, avg_out, warnings, catatan_mingguan,
    output_path, breakdown, stat_4_minggu, proyeksi, proyeksi_pengeluaran,
    tgl_cetak_dt, tgl_mulai_dt, tgl_akhir_dt,
    kustom_teks_ai=None, lampir_proyeksi=True, profil_dict=None
):
    """
    Laporan Kesehatan Bisnis – Format Profesional (Bankable)
    Struktur:
      H1 – Cover Formal
      H2 – Profil Entitas (opsional)
      H3 – Ringkasan Eksekutif & Skor
      H4 – Rincian Indikator
      H5 – Analisis Risiko & Credit Rating
      H6 – Proyeksi & Rekomendasi
      H7 – Analisis Naratif
    """

    # ── Palet Warna (monokrom profesional) ──
    C_NAVY   = colors.HexColor("#1A2B52")
    C_DARK   = colors.HexColor("#2C3E50")
    C_ACCENT = colors.HexColor("#2E86AB")
    C_GREEN  = colors.HexColor("#1E8449")
    C_AMBER  = colors.HexColor("#B7770D")
    C_RED    = colors.HexColor("#922B21")
    C_LGRAY  = colors.HexColor("#F5F6FA")
    C_MGRAY  = colors.HexColor("#BDC3C7")
    C_TXT    = colors.HexColor("#2C3E50")
    C_WHITE  = colors.white

    # ── Dokumen ──
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        rightMargin=2.2*cm, leftMargin=2.2*cm,
        topMargin=2.5*cm,   bottomMargin=2.5*cm,
        title=f"Laporan Kesehatan Bisnis – {user_name}",
        author="PANTAUIN Platform Analitik"
    )
    W = 17.6 * cm   # usable width

    # ── Styles ──
    s = getSampleStyleSheet()

    def S(name, **kw):
        base = kw.pop("parent", s["Normal"])
        return ParagraphStyle(name, parent=base, **kw)

    st_cover_brand  = S("CovBrand",  fontName="Helvetica-Bold",   fontSize=11, textColor=C_ACCENT,  alignment=TA_CENTER, spaceAfter=0)
    st_cover_title  = S("CovTitle",  fontName="Helvetica-Bold",   fontSize=28, textColor=C_NAVY,    alignment=TA_CENTER, spaceAfter=6,  leading=32)
    st_cover_sub    = S("CovSub",    fontName="Helvetica",        fontSize=13, textColor=C_DARK,    alignment=TA_CENTER, spaceAfter=4)
    st_cover_meta   = S("CovMeta",   fontName="Helvetica",        fontSize=10, textColor=C_MGRAY,   alignment=TA_CENTER, spaceAfter=3)
    st_cover_conf   = S("CovConf",   fontName="Helvetica-Bold",   fontSize=9,  textColor=C_WHITE,   alignment=TA_CENTER)

    st_h1           = S("H1",        fontName="Helvetica-Bold",   fontSize=15, textColor=C_NAVY,    spaceAfter=10, spaceBefore=18, leading=18)
    st_h2           = S("H2",        fontName="Helvetica-Bold",   fontSize=12, textColor=C_ACCENT,  spaceAfter=6,  spaceBefore=14, leading=15)
    st_body         = S("Body",      fontName="Helvetica",        fontSize=10, textColor=C_TXT,     leading=15, spaceAfter=8,  alignment=TA_JUSTIFY)
    st_body_c       = S("BodyC",     fontName="Helvetica",        fontSize=10, textColor=C_TXT,     leading=15, alignment=TA_CENTER)
    st_caption      = S("Cap",       fontName="Helvetica-Oblique",fontSize=8,  textColor=C_MGRAY,   spaceAfter=4)
    st_footnote     = S("Foot",      fontName="Helvetica",        fontSize=8,  textColor=C_MGRAY,   leading=11)
    st_label        = S("Lbl",       fontName="Helvetica-Bold",   fontSize=9,  textColor=C_NAVY)
    st_num_big      = S("NumBig",    fontName="Helvetica-Bold",   fontSize=36, textColor=C_WHITE,   alignment=TA_CENTER, leading=40)
    st_num_lbl      = S("NumLbl",    fontName="Helvetica-Bold",   fontSize=12, textColor=C_WHITE,   alignment=TA_CENTER, spaceAfter=2)
    st_num_sub      = S("NumSub",    fontName="Helvetica",        fontSize=9,  textColor=C_WHITE,   alignment=TA_CENTER)
    st_tbl_head     = S("TblHd",     fontName="Helvetica-Bold",   fontSize=9,  textColor=C_WHITE,   alignment=TA_CENTER)
    st_tbl_cell     = S("TblCl",     fontName="Helvetica",        fontSize=9,  textColor=C_TXT)
    st_tbl_cell_r   = S("TblClR",    fontName="Helvetica",        fontSize=9,  textColor=C_TXT,     alignment=TA_RIGHT)
    st_tbl_cell_c   = S("TblClC",    fontName="Helvetica",        fontSize=9,  textColor=C_TXT,     alignment=TA_CENTER)
    st_red          = S("Red",       fontName="Helvetica",        fontSize=9,  textColor=C_RED)
    st_green        = S("Grn",       fontName="Helvetica",        fontSize=9,  textColor=C_GREEN)
    st_amber        = S("Amb",       fontName="Helvetica",        fontSize=9,  textColor=C_AMBER)

    TPAD = [("TOPPADDING",(0,0),(-1,-1),6), ("BOTTOMPADDING",(0,0),(-1,-1),6),
            ("LEFTPADDING",(0,0),(-1,-1),8), ("RIGHTPADDING",(0,0),(-1,-1),8)]

    def tbl_style_base(header_rows=1):
        return TableStyle([
            ("BACKGROUND",(0,0),(-1,header_rows-1), C_NAVY),
            ("TEXTCOLOR",  (0,0),(-1,header_rows-1), C_WHITE),
            ("FONTNAME",   (0,0),(-1,header_rows-1), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0),(-1,header_rows-1), 9),
            ("LINEBELOW",  (0,0),(-1,header_rows-1), 1, C_NAVY),
            ("ROWBACKGROUNDS",(0,header_rows),(-1,-1),[C_WHITE, C_LGRAY]),
            ("GRID",       (0,0),(-1,-1), 0.3, C_MGRAY),
            ("VALIGN",     (0,0),(-1,-1), "MIDDLE"),
        ] + TPAD)

    # ── Pre-compute values ──
    val_in_30  = sum(s_["pemasukan"]       for s_ in stat_4_minggu) if stat_4_minggu else 0
    val_op_30  = sum(s_["pengeluaran_op"]  for s_ in stat_4_minggu) if stat_4_minggu else 0
    val_saldo_30 = sum(s_["saldo"]         for s_ in stat_4_minggu) if stat_4_minggu else 0
    gross_margin_pct = breakdown.get("nilai_gross_margin_pct", 0) * 100
    tren_penjualan   = breakdown.get("tren", 0)
    rasio_pengeluaran= breakdown.get("nilai_rasio_out", 0) * 100
    konsistensi      = breakdown.get("konsistensi", 0)

    tgl_cetak  = format_tanggal_indonesia(tgl_cetak_dt)
    tgl_mulai  = _tgl(tgl_mulai_dt)
    tgl_akhir  = _tgl(tgl_akhir_dt)

    # Score label
    if score > 70:
        bg_score, lbl_score, risk_overall = C_GREEN, "BISNIS SEHAT",      "RENDAH"
    elif score >= 40:
        bg_score, lbl_score, risk_overall = C_AMBER, "PERLU PERHATIAN",   "MODERAT"
    else:
        bg_score, lbl_score, risk_overall = C_RED,   "KONDISI KRITIS",    "TINGGI"

    # Proyeksi
    proy_arr = []
    if proyeksi and len(proyeksi)>=28 and proyeksi_pengeluaran and len(proyeksi_pengeluaran)>=28:
        for i,label in enumerate(["Minggu +1","Minggu +2","Minggu +3","Minggu +4"]):
            sl = slice(i*7, i*7+7)
            pi, po = sum(proyeksi[sl]), sum(proyeksi_pengeluaran[sl])
            proy_arr.append((label, pi, po, pi-po))

    # Risk engine
    risiko = _hitung_risiko(
        score, breakdown, val_in_30, val_op_30, val_saldo_30,
        avg_in, avg_out, gross_margin_pct, warnings, proy_arr
    )

    elements = []

    # ══════════════════════════════════════════
    # HALAMAN 1 – COVER FORMAL
    # ══════════════════════════════════════════
    def cover_page():
        # Top band (drawn via canvas in footer callback, here we add spacing)
        elements.append(Spacer(1, 1.5*cm))

        elements.append(Paragraph("PANTAUIN", st_cover_brand))
        elements.append(Spacer(1, 0.3*cm))
        elements.append(HRFlowable(width=W, thickness=2, color=C_NAVY))
        elements.append(Spacer(1, 1*cm))

        elements.append(Paragraph("LAPORAN KESEHATAN BISNIS", st_cover_title))
        elements.append(Paragraph("Analisis Komprehensif &amp; Penilaian Kelayakan Kredit", st_cover_sub))
        elements.append(Spacer(1, 0.8*cm))

        # Entity box
        entity_data = [
            [Paragraph(f"<b>{user_name}</b>",
                       S("EN", fontName="Helvetica-Bold", fontSize=16, textColor=C_NAVY, alignment=TA_CENTER))]
        ]
        t_entity = Table(entity_data, colWidths=[W], style=TableStyle([
            ("BOX",        (0,0),(0,0), 1.5, C_NAVY),
            ("LINEBELOW",  (0,0),(0,0), 4,   C_ACCENT),
            ("BACKGROUND", (0,0),(0,0),      C_LGRAY),
            ("TOPPADDING", (0,0),(0,0), 14),
            ("BOTTOMPADDING",(0,0),(0,0),14),
        ]))
        elements.append(t_entity)
        elements.append(Spacer(1, 0.6*cm))

        # Meta info
        meta = [
            ["Periode Analisis",  f"{tgl_mulai}  –  {tgl_akhir}"],
            ["Tanggal Laporan",   tgl_cetak],
            ["Nomor Laporan",     f"PTN-{tgl_cetak_dt.year}{tgl_cetak_dt.month:02d}{tgl_cetak_dt.day:02d}-001"],
            ["Disusun Oleh",      "PANTAUIN Analytics Engine v2.0"],
        ]
        t_meta = Table(meta, colWidths=[5*cm, W-5*cm], style=TableStyle([
            ("FONTNAME",  (0,0),(0,-1), "Helvetica-Bold"),
            ("FONTNAME",  (1,0),(1,-1), "Helvetica"),
            ("FONTSIZE",  (0,0),(-1,-1), 10),
            ("TEXTCOLOR", (0,0),(-1,-1), C_DARK),
            ("LINEBELOW", (0,0),(-1,-1), 0.3, C_MGRAY),
            ("TOPPADDING",(0,0),(-1,-1), 7),
            ("BOTTOMPADDING",(0,0),(-1,-1),7),
        ]))
        elements.append(t_meta)
        elements.append(Spacer(1, 1*cm))

        # Summary KPI strip
        c_saldo = C_GREEN if val_saldo_30 >= 0 else C_RED
        kpi_data = [
            [
                Paragraph(f"<b>{score}</b><br/><font size='9'>Business Health Score</font>",
                          S("K1", fontName="Helvetica-Bold", fontSize=22, textColor=C_WHITE, alignment=TA_CENTER, leading=28)),
                Paragraph(f"<b>{lbl_score}</b><br/><font size='9'>Status Bisnis</font>",
                          S("K2", fontName="Helvetica-Bold", fontSize=14, textColor=C_WHITE, alignment=TA_CENTER, leading=22)),
                Paragraph(f"<b>{risiko['composite']['rating']}</b><br/><font size='9'>Credit Rating</font>",
                          S("K3", fontName="Helvetica-Bold", fontSize=22, textColor=C_WHITE, alignment=TA_CENTER, leading=28)),
                Paragraph(f"<b>{risk_overall}</b><br/><font size='9'>Tingkat Risiko</font>",
                          S("K4", fontName="Helvetica-Bold", fontSize=14, textColor=C_WHITE, alignment=TA_CENTER, leading=22)),
            ]
        ]
        kpi_col = W / 4
        t_kpi = Table(kpi_data, colWidths=[kpi_col]*4, style=TableStyle([
            ("BACKGROUND",     (0,0),(0,0), bg_score),
            ("BACKGROUND",     (1,0),(1,0), bg_score),
            ("BACKGROUND",     (2,0),(2,0), C_ACCENT),
            ("BACKGROUND",     (3,0),(3,0), C_ACCENT),
            ("TOPPADDING",     (0,0),(-1,-1), 16),
            ("BOTTOMPADDING",  (0,0),(-1,-1), 16),
            ("LINEAFTER",      (0,0),(2,0), 1, colors.white),
            ("VALIGN",         (0,0),(-1,-1), "MIDDLE"),
        ]))
        elements.append(t_kpi)
        elements.append(Spacer(1, 1.2*cm))

        # Confidentiality notice
        conf = Table(
            [[Paragraph("DOKUMEN INI BERSIFAT RAHASIA DAN HANYA DIPERUNTUKKAN BAGI PIHAK-PIHAK YANG BERKEPENTINGAN", st_cover_conf)]],
            colWidths=[W], style=TableStyle([
                ("BACKGROUND",    (0,0),(0,0), C_DARK),
                ("TOPPADDING",    (0,0),(0,0), 8),
                ("BOTTOMPADDING", (0,0),(0,0), 8),
            ])
        )
        elements.append(conf)

        # Disclaimer
        elements.append(Spacer(1, 0.6*cm))
        elements.append(Paragraph(
            "Laporan ini disusun berdasarkan data transaksi yang diinput melalui platform PANTAUIN. "
            "Penilaian bersifat indikatif menggunakan model skoring internal dan tidak menggantikan "
            "due diligence keuangan oleh lembaga keuangan berwenang.",
            st_footnote
        ))

        elements.append(PageBreak())

    cover_page()

    # ══════════════════════════════════════════
    # HALAMAN 2 – PROFIL ENTITAS (opsional)
    # ══════════════════════════════════════════
    if profil_dict:
        elements.append(Paragraph("1. PROFIL ENTITAS USAHA", st_h1))
        elements.append(HRFlowable(width=W, thickness=1, color=C_ACCENT, spaceAfter=8))

        rows = [
            [Paragraph("IDENTITAS UMUM", st_tbl_head), ""],
            ["Nama Entitas",       profil_dict.get("entitas", "–")],
            ["Penanggung Jawab",   f"{profil_dict.get('contact_person','–')} ({profil_dict.get('jabatan','–')})"],
            ["Bentuk Hukum",       profil_dict.get("bentuk_usaha","–")],
            ["Tahun Berdiri",      profil_dict.get("tahun_berdiri","–")],
            ["Alamat",             profil_dict.get("alamat","–")],
            ["Kontak",             profil_dict.get("kontak","–")],
            ["Legalitas / NIB",    profil_dict.get("legalitas","–")],
            [Paragraph("OPERASIONAL", st_tbl_head), ""],
            ["Jumlah Tenaga Kerja",profil_dict.get("tk","–")],
            ["Kapasitas Produksi", profil_dict.get("kapasitas","–")],
            ["Rata-rata Omzet",    profil_dict.get("omzet","–")],
            ["Sumber Bahan Baku",  profil_dict.get("bahan_baku","–")],
            ["Segmen Konsumen",    profil_dict.get("pasar","–")],
            ["Jangkauan Pasar",    profil_dict.get("wilayah","–")],
        ]

        col0 = 5.5*cm; col1 = W - col0
        ts = TableStyle([
            ("BACKGROUND",  (0,0),(-1,0),  C_NAVY),
            ("BACKGROUND",  (0,8),(-1,8),  C_NAVY),
            ("SPAN",        (0,0),(-1,0)),
            ("SPAN",        (0,8),(-1,8)),
            ("FONTNAME",    (0,1),(0,7),   "Helvetica-Bold"),
            ("FONTNAME",    (0,9),(0,-1),  "Helvetica-Bold"),
            ("FONTSIZE",    (0,0),(-1,-1), 9),
            ("ROWBACKGROUNDS",(0,1),(-1,7), [C_WHITE, C_LGRAY]),
            ("ROWBACKGROUNDS",(0,9),(-1,-1),[C_WHITE, C_LGRAY]),
            ("GRID",        (0,0),(-1,-1), 0.3, C_MGRAY),
            ("VALIGN",      (0,0),(-1,-1), "TOP"),
        ] + TPAD)

        elements.append(Table(rows, colWidths=[col0, col1], style=ts))
        elements.append(PageBreak())

    sec = 1 if not profil_dict else 2

    # ══════════════════════════════════════════
    # HALAMAN 3 – RINGKASAN EKSEKUTIF
    # ══════════════════════════════════════════
    elements.append(Paragraph(f"{sec}. RINGKASAN EKSEKUTIF", st_h1)); sec+=1
    elements.append(HRFlowable(width=W, thickness=1, color=C_ACCENT, spaceAfter=8))

    # Skor Box
    score_tbl = Table([
        [Paragraph(f"{score}", st_num_big)],
        [Paragraph(lbl_score, st_num_lbl)],
        [Paragraph("Business Health Score (0–100)", st_num_sub)],
    ], colWidths=[7*cm], style=TableStyle([
        ("BACKGROUND",    (0,0),(0,-1), bg_score),
        ("TOPPADDING",    (0,0),(0,0),  18),
        ("BOTTOMPADDING", (0,-1),(0,-1),18),
        ("ALIGN",         (0,0),(0,-1), "CENTER"),
    ]))

    # KPI Kanan
    kpi_right = [
        ["Total Pemasukan 30 Hari",           _fmt_rp(val_in_30)],
        ["Total Pengeluaran Operasional",      _fmt_rp(val_op_30)],
        ["Saldo Bersih 30 Hari",               _fmt_rp(val_saldo_30)],
        ["Rata-rata Pemasukan Harian",         _fmt_rp(avg_in)],
        ["Rata-rata Pengeluaran Harian",       _fmt_rp(avg_out)],
        ["Gross Margin Rata-rata",             f"{gross_margin_pct:.1f}%"],
        ["Credit Rating Komposit",             risiko["composite"]["rating"]],
    ]

    def _kpi_row(label, val, i):
        c_bg = C_WHITE if i % 2 == 0 else C_LGRAY
        c_val = C_GREEN if "Rp" in str(val) and val_saldo_30 >= 0 and "Saldo" in label else C_TXT
        return [
            Paragraph(label, S(f"kl{i}", fontName="Helvetica",      fontSize=9, textColor=C_DARK)),
            Paragraph(f"<b>{val}</b>", S(f"kv{i}", fontName="Helvetica-Bold", fontSize=9,
                                          textColor=(C_RED if "Saldo" in label and val_saldo_30<0 else
                                                     C_GREEN if "Saldo" in label else
                                                     C_ACCENT if "Rating" in label else C_TXT),
                                          alignment=TA_RIGHT)),
        ]

    kpi_rows = [_kpi_row(l, v, i) for i,(l,v) in enumerate(kpi_right)]
    t_kpi_right = Table(kpi_rows, colWidths=[6*cm, 4*cm], style=TableStyle([
        ("GRID",  (0,0),(-1,-1), 0.3, C_MGRAY),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[C_WHITE, C_LGRAY]),
    ] + TPAD))

    t_overview = Table([[score_tbl, t_kpi_right]],
                       colWidths=[7.2*cm, W-7.2*cm],
                       style=TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),
                                         ("LEFTPADDING",(1,0),(1,0),12)]))
    elements.append(t_overview)
    elements.append(Spacer(1, 14))

    # Peringatan
    if warnings:
        warn_rows = [[Paragraph("PERINGATAN AKTIF", st_tbl_head)]]
        for w in warnings:
            warn_rows.append([Paragraph(f"• {w}", S("wi", fontName="Helvetica", fontSize=9, textColor=C_RED))])
        t_w = Table(warn_rows, colWidths=[W], style=TableStyle([
            ("BACKGROUND", (0,0),(0,0), C_RED),
            ("BACKGROUND", (0,1),(0,-1), colors.HexColor("#FDFEFE")),
            ("LINEAFTER",  (0,0),(0,-1), 2, C_RED),
            ("LINEBEFORE", (0,0),(0,-1), 2, C_RED),
            ("LINEBELOW",  (0,-1),(0,-1), 2, C_RED),
            ("LINEBELOW",  (0,1),(0,-2), 0.3, C_MGRAY),
        ] + TPAD))
        elements.append(t_w)
        elements.append(Spacer(1, 10))

    elements.append(PageBreak())

    # ══════════════════════════════════════════
    # HALAMAN 4 – RINCIAN INDIKATOR & STATISTIK
    # ══════════════════════════════════════════
    elements.append(Paragraph(f"{sec}. RINCIAN INDIKATOR KESEHATAN", st_h1)); sec+=1
    elements.append(HRFlowable(width=W, thickness=1, color=C_ACCENT, spaceAfter=8))

    def _status_p(v):
        if v > 70:  return Paragraph("Baik",         S("sg", fontName="Helvetica-Bold", fontSize=9, textColor=C_GREEN))
        if v >= 40: return Paragraph("Perlu Perhatian",S("sa", fontName="Helvetica-Bold", fontSize=9, textColor=C_AMBER))
        return           Paragraph("Kritis",         S("sr", fontName="Helvetica-Bold", fontSize=9, textColor=C_RED))

    ind_data = [
        [Paragraph(h, st_tbl_head) for h in ["Indikator","Bobot","Skor Komponen","Kontribusi","Status"]],
        ["Stabilitas Cashflow",    "25%",
         f"{breakdown.get('stabilitas',0)}/100",
         f"{breakdown.get('stabilitas',0)*0.25:.1f}/25",
         _status_p(breakdown.get("stabilitas",0))],
        ["Tren Penjualan",         "25%",
         f"{breakdown.get('tren',0)}/100",
         f"{breakdown.get('tren',0)*0.25:.1f}/25",
         _status_p(breakdown.get("tren",0))],
        ["Rasio Pengeluaran Ops.", "20%",
         f"{breakdown.get('pengeluaran',0)}/100",
         f"{breakdown.get('pengeluaran',0)*0.20:.1f}/20",
         _status_p(breakdown.get("pengeluaran",0))],
        ["Gross Margin",           "20%",
         f"{breakdown.get('gross_margin',0)}/100",
         f"{breakdown.get('gross_margin',0)*0.20:.1f}/20",
         _status_p(breakdown.get("gross_margin",0))],
        ["Konsistensi Pemasukan",  "10%",
         f"{breakdown.get('konsistensi',0)}/100",
         f"{breakdown.get('konsistensi',0)*0.10:.1f}/10",
         _status_p(breakdown.get("konsistensi",0))],
        [Paragraph("<b>TOTAL</b>", S("tot", fontName="Helvetica-Bold", fontSize=9)), "100%", "—",
         Paragraph(f"<b>{score}/100</b>", S("ts", fontName="Helvetica-Bold", fontSize=9,
                                             textColor=bg_score)), ""],
    ]

    ts_ind = tbl_style_base()
    ts_ind.add("FONTNAME",    (0,-1),(-1,-1), "Helvetica-Bold")
    ts_ind.add("BACKGROUND",  (0,-1),(-1,-1), C_LGRAY)
    ts_ind.add("ALIGN",       (1,0), (-1,-1), "CENTER")
    ts_ind.add("ALIGN",       (0,0), (0,-1),  "LEFT")

    elements.append(Table(ind_data, colWidths=[5.5*cm,2*cm,3.2*cm,3.2*cm,3.7*cm],
                          style=ts_ind))
    elements.append(Spacer(1, 16))

    # Statistik 4 Minggu
    elements.append(Paragraph("Statistik 4 Minggu Terakhir", st_h2))
    stat_data = [[Paragraph(h, st_tbl_head) for h in
                  ["Periode","Pemasukan","Pengeluaran Ops.","Saldo Bersih","Tren"]]]
    if stat_4_minggu:
        for st_ in reversed(stat_4_minggu):
            c_s = C_GREEN if st_["saldo"] >= 0 else C_RED
            c_t = (C_GREEN if "Naik" in st_["tren"] else
                   C_RED   if "Turun" in st_["tren"] else colors.grey)
            stat_data.append([
                Paragraph(st_["minggu"],           st_tbl_cell_c),
                Paragraph(_fmt_rp(st_["pemasukan"]),st_tbl_cell_r),
                Paragraph(_fmt_rp(st_["pengeluaran_op"]),st_tbl_cell_r),
                Paragraph(f"<b>{_fmt_rp(st_['saldo'])}</b>",
                          S("ss", fontName="Helvetica-Bold", fontSize=9, textColor=c_s, alignment=TA_RIGHT)),
                Paragraph(st_["tren"],
                          S("st", fontName="Helvetica-Bold", fontSize=9, textColor=c_t, alignment=TA_CENTER)),
            ])

    ts_stat = tbl_style_base()
    ts_stat.add("ALIGN",(1,0),(-1,-1),"RIGHT")
    ts_stat.add("ALIGN",(0,0),(0,-1),"CENTER")
    ts_stat.add("ALIGN",(4,0),(4,-1),"CENTER")
    elements.append(Table(stat_data, colWidths=[3.5*cm,3.8*cm,3.8*cm,3.8*cm,2.7*cm],
                          style=ts_stat))

    elements.append(PageBreak())

    # ══════════════════════════════════════════
    # HALAMAN 5 – ANALISIS RISIKO (CREDIT SECTION)
    # ══════════════════════════════════════════
    elements.append(Paragraph(f"{sec}. ANALISIS RISIKO BISNIS", st_h1)); sec+=1
    elements.append(HRFlowable(width=W, thickness=1, color=C_ACCENT, spaceAfter=4))
    elements.append(Paragraph(
        "Bagian ini menyajikan profil risiko komprehensif yang dapat digunakan sebagai "
        "referensi dalam proses penilaian kelayakan kredit atau investasi.",
        st_body))

    RATING_COLOR = {
        "AAA": C_GREEN, "AA": C_GREEN, "A": C_GREEN,
        "BBB": C_ACCENT, "BB": C_AMBER,
        "B": C_AMBER, "CCC": C_RED, "CC": C_RED, "C": C_RED
    }

    # Credit Rating Box
    rat = risiko["composite"]["rating"]
    rat_color = RATING_COLOR.get(rat, C_DARK)
    rat_label = risiko["composite"]["label"]
    rat_skor  = risiko["composite"]["skor"]

    rat_tbl = Table([
        [Paragraph(rat, S("RatN", fontName="Helvetica-Bold", fontSize=32, textColor=C_WHITE, alignment=TA_CENTER)),
         [
             Paragraph(f"<b>Rating Risiko: {rat_label}</b>",
                       S("RL", fontName="Helvetica-Bold", fontSize=12, textColor=rat_color, spaceAfter=3)),
             Paragraph(f"Skor Komposit: {rat_skor:.2f} / 5.00",
                       S("RS", fontName="Helvetica", fontSize=10, textColor=C_TXT, spaceAfter=3)),
             Paragraph("Skala: AAA (Terbaik) — CCC (Paling Berisiko)",
                       S("RI", fontName="Helvetica-Oblique", fontSize=9, textColor=C_MGRAY)),
         ]
        ]
    ], colWidths=[3.5*cm, W-3.5*cm], style=TableStyle([
        ("BACKGROUND",    (0,0),(0,0), rat_color),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("LEFTPADDING",   (1,0),(1,0), 16),
        ("TOPPADDING",    (0,0),(0,0), 16),
        ("BOTTOMPADDING", (0,0),(0,0), 16),
        ("BOX",           (0,0),(-1,-1), 1, C_MGRAY),
    ]))
    elements.append(rat_tbl)
    elements.append(Spacer(1, 14))

    # Risk Dimension Table
    elements.append(Paragraph("Rincian Dimensi Risiko", st_h2))

    RISK_LABELS = {1:"Sangat Rendah",2:"Rendah",3:"Moderat",4:"Tinggi",5:"Sangat Tinggi"}
    RISK_COLORS = {1:C_GREEN,2:C_GREEN,3:C_AMBER,4:C_RED,5:C_RED}
    BOBOT_LABELS = {
        "likuiditas":    ("Risiko Likuiditas",     "30%"),
        "profitabilitas":("Risiko Profitabilitas", "25%"),
        "arus_kas":      ("Risiko Arus Kas",       "25%"),
        "proyeksi":      ("Risiko Proyeksi",       "15%"),
        "kepatuhan":     ("Kepatuhan Data",        "5%"),
    }

    risk_data = [[Paragraph(h, st_tbl_head) for h in
                  ["Dimensi Risiko","Bobot","Tingkat","Skor","Keterangan"]]]

    for key, (nama, bobot) in BOBOT_LABELS.items():
        r = risiko[key]
        s_num = r["skor"]
        lbl = RISK_LABELS[s_num]
        c   = RISK_COLORS[s_num]
        risk_data.append([
            Paragraph(nama, S(f"rn{key}", fontName="Helvetica", fontSize=9)),
            Paragraph(bobot, st_tbl_cell_c),
            Paragraph(f"<b>{lbl}</b>", S(f"rl{key}", fontName="Helvetica-Bold", fontSize=9, textColor=c, alignment=TA_CENTER)),
            Paragraph(f"{s_num}/5",    st_tbl_cell_c),
            Paragraph(r["keterangan"], S(f"rk{key}", fontName="Helvetica", fontSize=8.5, textColor=C_TXT)),
        ])

    ts_risk = tbl_style_base()
    ts_risk.add("ALIGN",(1,0),(3,-1),"CENTER")
    ts_risk.add("ALIGN",(0,0),(0,-1),"LEFT")
    elements.append(Table(risk_data,
                          colWidths=[4*cm,1.8*cm,3*cm,1.5*cm,W-10.3*cm],
                          style=ts_risk))
    elements.append(Spacer(1, 14))

    # Visual risk matrix
    elements.append(Paragraph("Visualisasi Skor Dimensi Risiko", st_h2))
    vis_data = [[Paragraph(h, st_tbl_head) for h in ["Dimensi","Indikator","Tingkat Risiko (1=Rendah, 5=Tinggi)"]]]
    for key, (nama, _) in BOBOT_LABELS.items():
        s_num = risiko[key]["skor"]
        vis_data.append([
            Paragraph(nama, S(f"vn{key}", fontName="Helvetica", fontSize=9)),
            Paragraph(f"{s_num}/5", st_tbl_cell_c),
            RiskBar(s_num, width=int(W*0.48)),
        ])
    ts_vis = tbl_style_base()
    ts_vis.add("ALIGN",(1,0),(1,-1),"CENTER")
    elements.append(Table(vis_data, colWidths=[4.5*cm,2*cm,W-6.5*cm], style=ts_vis))

    elements.append(PageBreak())

    # ══════════════════════════════════════════
    # HALAMAN 6 – PROYEKSI & REKOMENDASI
    # ══════════════════════════════════════════
    if lampir_proyeksi:
        elements.append(Paragraph(f"{sec}. PROYEKSI ARUS KAS 4 MINGGU", st_h1)); sec+=1
        elements.append(HRFlowable(width=W, thickness=1, color=C_ACCENT, spaceAfter=8))

        proy_data = [[Paragraph(h, st_tbl_head) for h in
                      ["Periode","Proyeksi Pemasukan","Proyeksi Pengeluaran","Proyeksi Saldo","Status"]]]
        for (lbl, pi, po, ps) in proy_arr:
            c_s = C_GREEN if ps >= 0 else C_RED
            status = Paragraph("Positif" if ps >= 0 else "Negatif",
                               S("ps", fontName="Helvetica-Bold", fontSize=9, textColor=c_s, alignment=TA_CENTER))
            proy_data.append([
                Paragraph(lbl, st_tbl_cell_c),
                Paragraph(_fmt_rp(pi), st_tbl_cell_r),
                Paragraph(_fmt_rp(po), st_tbl_cell_r),
                Paragraph(f"<b>{_fmt_rp(ps)}</b>",
                          S("psd", fontName="Helvetica-Bold", fontSize=9, textColor=c_s, alignment=TA_RIGHT)),
                status,
            ])

        ts_proy = tbl_style_base()
        ts_proy.add("ALIGN",(1,0),(-2,-1),"RIGHT")
        ts_proy.add("ALIGN",(0,0),(0,-1),"CENTER")
        ts_proy.add("ALIGN",(-1,0),(-1,-1),"CENTER")
        elements.append(Table(proy_data, colWidths=[2.8*cm,3.8*cm,3.8*cm,4*cm,3.2*cm], style=ts_proy))
        elements.append(Paragraph(
            "Proyeksi dihitung menggunakan metode regresi linear berbasis data historis 30 hari terakhir. "
            "Proyeksi ini bersifat indikatif dan dapat berubah sesuai kondisi aktual.",
            st_caption))
        elements.append(Spacer(1, 16))

    # Rekomendasi
    elements.append(Paragraph(f"{sec}. REKOMENDASI TINDAKAN", st_h1)); sec+=1
    elements.append(HRFlowable(width=W, thickness=1, color=C_ACCENT, spaceAfter=8))

    rekomendasi = []
    avg_weekly_expense = avg_out * 7
    dana_darurat_ideal = avg_weekly_expense * 2

    rekomendasi.append((
        "Pengelolaan Margin",
        f"Pertahankan gross margin di atas {gross_margin_pct:.1f}% dengan optimasi harga jual "
        f"dan pengendalian harga pokok produksi secara berkala."
    ))
    rekomendasi.append((
        "Pencatatan Keuangan",
        "Lakukan pencatatan transaksi secara disiplin setiap hari untuk meningkatkan akurasi "
        "analisis dan memperkuat kredibilitas laporan keuangan."
    ))
    if tren_penjualan < 50:
        rekomendasi.append((
            "Peningkatan Penjualan",
            "Tren penjualan menunjukkan penurunan. Disarankan untuk mengimplementasikan program "
            "promosi terstruktur atau strategi retensi pelanggan guna mendorong pertumbuhan pendapatan."
        ))
    if rasio_pengeluaran > 60:
        rekomendasi.append((
            "Efisiensi Operasional",
            f"Rasio pengeluaran operasional sebesar {rasio_pengeluaran:.1f}% melampaui batas efisiensi "
            f"yang disarankan (60%). Lakukan audit biaya dan identifikasi pos yang dapat dipangkas 10–15%."
        ))
    if gross_margin_pct < 30:
        rekomendasi.append((
            "Perbaikan Margin",
            f"Gross margin {gross_margin_pct:.1f}% berada di bawah standar sektor UMKM (>30%). "
            "Pertimbangkan penyesuaian harga jual atau negosiasi ulang harga bahan baku dengan pemasok."
        ))
    if val_saldo_30 < dana_darurat_ideal:
        rekomendasi.append((
            "Pembentukan Dana Cadangan",
            f"Saldo bersih saat ini ({_fmt_rp(val_saldo_30)}) belum memenuhi dana cadangan operasional "
            f"minimum 2 minggu ({_fmt_rp(dana_darurat_ideal)}). Alokasikan sebagian pemasukan untuk "
            "pembentukan dana darurat secara bertahap."
        ))
    neg_in = sum(1 for (_,_,_,s) in proy_arr if s < 0)
    if neg_in > 0:
        rekomendasi.append((
            "Antisipasi Cashflow Negatif",
            f"Proyeksi menunjukkan potensi arus kas negatif dalam {neg_in} periode ke depan. "
            "Tunda pengeluaran modal yang tidak kritis dan optimalkan penagihan piutang."
        ))
    if konsistensi < 60:
        rekomendasi.append((
            "Konsistensi Pendapatan",
            "Fluktuasi pendapatan harian yang tinggi mengindikasikan ketidakstabilan permintaan. "
            "Identifikasi pola penjualan dan kembangkan strategi untuk periode permintaan rendah."
        ))

    rekomendasi = rekomendasi[:7]

    rec_rows = [[Paragraph(h, st_tbl_head) for h in ["No.","Aspek","Rekomendasi Tindakan"]]]
    for i, (aspek, isi) in enumerate(rekomendasi, 1):
        rec_rows.append([
            Paragraph(str(i), st_tbl_cell_c),
            Paragraph(f"<b>{aspek}</b>", S(f"as{i}", fontName="Helvetica-Bold", fontSize=9, textColor=C_NAVY)),
            Paragraph(isi, S(f"ri{i}", fontName="Helvetica", fontSize=9, textColor=C_TXT, leading=13)),
        ])
    ts_rec = tbl_style_base()
    ts_rec.add("ALIGN",(0,0),(0,-1),"CENTER")
    ts_rec.add("VALIGN",(0,0),(-1,-1),"TOP")
    elements.append(Table(rec_rows, colWidths=[1.2*cm,3.5*cm,W-4.7*cm], style=ts_rec))

    elements.append(PageBreak())

    # ══════════════════════════════════════════
    # HALAMAN 7 – ANALISIS NARATIF
    # ══════════════════════════════════════════
    elements.append(Paragraph(f"{sec}. ANALISIS NARATIF", st_h1)); sec+=1
    elements.append(HRFlowable(width=W, thickness=1, color=C_ACCENT, spaceAfter=8))

    # Try to get AI narration if available
    try:
        from gemini_helper import get_pdf_narration
        if kustom_teks_ai:
            ai_text = kustom_teks_ai
        else:
            proy_arr_safe = proy_arr if proy_arr else []
            ai_text = get_pdf_narration(
                nama_bisnis=user_name, skor=score, label_skor=lbl_score,
                total_pemasukan=val_in_30, total_pengeluaran_ops=val_op_30,
                saldo_bersih=val_saldo_30, avg_harian_masuk=avg_in,
                gross_margin=gross_margin_pct, tren_penjualan=tren_penjualan,
                stabilitas=breakdown.get("stabilitas",0),
                rasio_pengeluaran=rasio_pengeluaran, konsistensi=konsistensi,
                peringatan_list=warnings,
                proyeksi_pemasukan=sum(proyeksi) if proyeksi else 0,
                proyeksi_saldo=sum(p[3] for p in proy_arr_safe) if proy_arr_safe else 0
            )
    except Exception:
        ai_text = (
            f"Berdasarkan analisis komprehensif terhadap data keuangan {user_name} selama periode "
            f"{tgl_mulai} hingga {tgl_akhir}, entitas usaha ini memperoleh Business Health Score "
            f"sebesar {score}/100 dengan status '{lbl_score}'.\n\n"
            f"Dari sisi profitabilitas, gross margin tercatat sebesar {gross_margin_pct:.1f}% dengan "
            f"rata-rata pemasukan harian sebesar {_fmt_rp(avg_in)}. Rasio pengeluaran operasional "
            f"terhadap pendapatan berada di angka {rasio_pengeluaran:.1f}%.\n\n"
            f"Penilaian risiko komposit menghasilkan rating {risiko['composite']['rating']} "
            f"({risiko['composite']['label']}), yang mencerminkan profil risiko keseluruhan bisnis "
            f"ini berdasarkan lima dimensi: likuiditas, profitabilitas, stabilitas arus kas, "
            f"proyeksi ke depan, dan kepatuhan data.\n\n"
            "Laporan ini dapat digunakan sebagai dokumen pendukung dalam pengajuan kredit atau "
            "pembiayaan usaha kepada lembaga keuangan."
        )

    for par in ai_text.split("\n"):
        if par.strip():
            elements.append(Paragraph(par.strip(), st_body))

    elements.append(Spacer(1, 2*cm))

    # Metodologi
    elements.append(HRFlowable(width=W, thickness=0.5, color=C_MGRAY, spaceAfter=8))
    elements.append(Paragraph("<b>Catatan Metodologi</b>", S("mh", fontName="Helvetica-Bold", fontSize=9, textColor=C_DARK)))
    metodologi = [
        "Business Health Score dihitung menggunakan Weighted Scoring Model dengan lima indikator komprehensif.",
        "Analisis risiko menggunakan Rules-Based Scoring Framework dengan pembobotan berdasarkan signifikansi terhadap kemampuan membayar.",
        "Proyeksi arus kas menggunakan metode regresi linear berbasis data historis 30 hari.",
        "Credit Rating Komposit merupakan agregasi tertimbang dari lima dimensi risiko internal.",
        "Laporan ini bersifat indikatif dan tidak menggantikan proses due diligence keuangan oleh lembaga keuangan berwenang.",
    ]
    for m in metodologi:
        elements.append(Paragraph(f"• {m}", st_footnote))

    # ── Footer Callback ──
    def make_footer(canvas_obj, doc_obj):
        canvas_obj.saveState()

        # Top accent line
        canvas_obj.setStrokeColor(C_NAVY)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(2.2*cm, A4[1]-1.8*cm, (A4[0]-2.2*cm), A4[1]-1.8*cm)

        # Header brand (small)
        canvas_obj.setFont("Helvetica-Bold", 8)
        canvas_obj.setFillColor(C_ACCENT)
        canvas_obj.drawString(2.2*cm, A4[1]-1.5*cm, "PANTAUIN")
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.setFillColor(C_MGRAY)
        canvas_obj.drawString(2.2*cm+2.8*cm, A4[1]-1.5*cm,
                              "Laporan Kesehatan Bisnis")
        canvas_obj.drawRightString(A4[0]-2.2*cm, A4[1]-1.5*cm,
                                   f"{user_name}  |  {tgl_cetak}")

        # Footer line
        canvas_obj.setStrokeColor(C_MGRAY)
        canvas_obj.setLineWidth(0.4)
        canvas_obj.line(2.2*cm, 2*cm, A4[0]-2.2*cm, 2*cm)

        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.setFillColor(C_MGRAY)
        canvas_obj.drawString(2.2*cm, 1.6*cm, "PANTAUIN — Platform Analitik Bisnis UMKM")
        canvas_obj.drawRightString(A4[0]-2.2*cm, 1.6*cm,
                                   f"Halaman {canvas_obj.getPageNumber()}")
        canvas_obj.restoreState()

    doc.build(elements, onFirstPage=make_footer, onLaterPages=make_footer)