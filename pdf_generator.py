import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from gemini_helper import get_pdf_narration

def generate_pdf_report(user_name, score, avg_in, avg_out, warnings, catatan_mingguan, output_path):
    """
    Membuat laporan cetak evaluasi kesehatan bisnis untuk pengguna. (ISO 25010 Reliability)
    Mencakup Narasi Gemini.
    """
    doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=30)
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=22, spaceAfter=20)
    h2_style = ParagraphStyle('CustomH2', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=16, spaceAfter=10)
    normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=11, spaceAfter=8, leading=16)

    elements = []
    
    # 1. Judul
    elements.append(Paragraph(f"Laporan Evaluasi Bisnis: {user_name}", title_style))
    elements.append(Paragraph("Dihasilkan secara otomatis oleh platform cerdas PANTAUIN.", normal_style))
    elements.append(Spacer(1, 20))
    
    # 2. Skor Kesehatan
    label_skor = "Sehat" if score >= 80 else ("Kritis" if score < 60 else "Waspada")
    elements.append(Paragraph(f"Business Health Score: <b>{score} / 100</b> ({label_skor})", h2_style))
    elements.append(Spacer(1, 15))

    # 3. Tabel Ringkasan
    data_tabel = [
        ['Parameter Evaluasi', 'Nilai Rata-Rata Harian (Rp)'],
        ['Total Pemasukan Harian', f"Rp {avg_in:,}"],
        ['Total Pengeluaran Harian', f"Rp {avg_out:,}"]
    ]
    t = Table(data_tabel, colWidths=[250, 200], style=[
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#1B2A6B')),
        ('TEXTCOLOR', (0,0), (1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ])
    elements.append(t)
    elements.append(Spacer(1, 25))

    # 4. Narasi Gemini / Evaluasi Pakar AI
    elements.append(Paragraph("Evaluasi & Saran (Analisa AI):", h2_style))
    narasi = get_pdf_narration(score, avg_in, avg_out, warnings, catatan_mingguan)
    elements.append(Paragraph(narasi, normal_style))
    
    # Tambahkan Peringatan jika ada
    if warnings:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("<b>PERHATIAN KHUSUS:</b>", normal_style))
        for w in warnings:
            elements.append(Paragraph(f"• {w}", normal_style))

    # Build PDF
    doc.build(elements)
