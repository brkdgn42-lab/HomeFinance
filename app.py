import streamlit as st
from supabase import create_client
import datetime
import pandas as pd
from fpdf import FPDF

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Ev Yönetim Paneli", layout="wide")

# --- BAĞLANTI ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- VERİ ÇEKME FONKSİYONLARI ---
def verileri_yukle():
    bugun = datetime.date.today()
    ay_basi = bugun.replace(day=1)
    
    # Sabit Giderler
    sabit_res = supabase.table("sabit_gider").select("*").order("id").execute()
    # Gelir/Gider (Bu ay)
    hareket_res = supabase.table("gelir_gider")\
        .select("*")\
        .gte("tarih", str(ay_basi))\
        .order("tarih", desc=True).execute()
        
    return pd.DataFrame(sabit_res.data), pd.DataFrame(hareket_res.data)

# --- PDF OLUŞTURMA FONKSİYONU ---
def pdf_olustur(df_sabit, df_hareket, bakiye):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "EV YONETIM RAPORU", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(190, 10, f"Rapor Tarihi: {datetime.date.today().strftime('%d.%m.%Y')}", ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(100, 10, f"TOPLAM HESAP DURUMU: {bakiye:,.2f} TL", 0, 1, "L")
    pdf.ln(5)

    # Sabit Giderler Tablosu
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(120, 8, "Aciklama", 1, 0, "C", True)
    pdf.cell(35, 8, "Tutar", 1, 0, "C", True)
    pdf.cell(35, 8, "Durum", 1, 1, "C", True)
    
    pdf.set_font("Arial", "", 10)
    for _, row in df_sabit.iterrows():
        durum = "Odendi" if row['odendi'] else "Odenmedi"
        pdf.cell(120, 8, str(row['aciklama']), 1)
        pdf.cell(35, 8, f"{row['tutar']:.2f} TL", 1, 0, "R")
        pdf.cell(35, 8, durum, 1, 1, "C")
    
    return pdf.output(dest='S').encode('latin-1')

# --- ANLIK GÜNCELLEME FONKSİYONU ---
def sabit_guncelle():
    if "sabit_editor" in st.session_state:
        degisiklikler = st.session_state["sabit_editor"]["edited_rows"]
        for satir_index, degerler in degisiklikler.items():
            if "odendi" in degerler:
                row_id = int(st.session_state.df_sabit.iloc[satir_index]["id"])
                yeni_durum = degerler["odendi"]
                supabase.table("sabit_gider").update({"odendi": yeni_durum}).eq("id", row_id).execute()
                st.session_state.df_sabit.at[satir_index, "odendi"] = yeni_durum

# --- SESSION STATE KONTROLÜ (GÜVENLİ) ---
if 'df_sabit' not in st.session_state or 'df_hareket' not in st.session_state:
    sabit, hareket = verileri_yukle()
    st.session_state.df_sabit = sabit
    st.session_state.df_hareket = hareket

# --- HESAPLAMA (GÜVENLİ OKUMA) ---
# Veri o an silinmişse boş dataframe oluşturup çökmesini engelliyoruz
df_h = st.session_state.get('df_hareket', pd.DataFrame())
df_s = st.session_state.get('df_sabit', pd.DataFrame())

toplam_gelir = df_h[df_h['tur'] == 'Gelir']['tutar'].sum() if not df_h.empty else 0
toplam_gider = df_h[df_h['tur'] == 'Gider']['tutar'].sum() if not df_h.empty else 0
odenen_sabit = df_s[df_s['odendi'] == True]['tutar'].sum() if not df_s.empty else 0
güncel_bakiye = toplam_gelir - toplam_gider - odenen_sabit

# --- ARAYÜZ ---
col_baslik, col_bakiye = st.columns([3, 1])

with col_baslik:
    st.title("🏠 Ev Yönetim Paneli")
    st.caption(f"{datetime.date.today().strftime('%B %Y')} Dönemi")

with col_bakiye:
    # Değişken isminde Türkçe karakter sorunu riskine karşı direkt hesaplanmış rakamı alıyoruz
    bakiye_metni = f"{güncel_bakiye:,.2f} €"
    
    st.markdown(
        f"""
        <div style="
            background-color: #f0f2f6;
            padding: 10px;
            border-radius: 10px;
            border: 1px solid #d1d5db;
            text-align: center;">
            <p style="margin: 0; font-size: 14px; color: #6b7280; font-weight: bold;">HESAP DURUMU</p>
            <p style="margin: 0; font-size: 20px; font-weight: 800; color: #1f2937;">{bakiye_metni}</p>
        </div>
        """,
        unsafe_allow_html=True
    )
# --- SABİT GİDERLER TABLOSU ---
st.subheader("📌 Sabit Giderler")
if not df_s.empty:
    st.data_editor(
        df_s[["id", "aciklama", "tutar", "odendi"]],
        column_config={
            "odendi": st.column_config.CheckboxColumn("Ödendi", default=False),
            "id": None 
        },
        use_container_width=True,
        hide_index=True,
        key="sabit_editor",
        on_change=sabit_guncelle
    )

st.divider()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ İşlemler")
    with st.popover("➕ Yeni Gelir/Gider Ekle", use_container_width=True):
        with st.form("yeni_kayit", clear_on_submit=True):
            tarih = st.date_input("Tarih", datetime.date.today())
            tur = st.selectbox("Tür", ["Gelir", "Gider"])
            aciklama = st.text_input("Açıklama")
            tutar = st.number_input("Tutar", min_value=0.0)
            if st.form_submit_button("Kaydet"):
                data = {"tarih": str(tarih), "aciklama": aciklama, "tutar": tutar, "tur": tur}
                supabase.table("gelir_gider").insert(data).execute()
                # Sadece ilgili veriyi siliyoruz, bir sonraki döngüde if bloğu bunu yenileyecek
                if 'df_hareket' in st.session_state:
                    del st.session_state.df_hareket
                st.rerun()

    st.divider()
    st.subheader("🖨️ Raporlama")
    if st.button("📄 Bu Ayın PDF Raporunu Hazırla", use_container_width=True):
        pdf_data = pdf_olustur(df_s, df_h, güncel_bakiye)
        st.download_button(
            label="📥 PDF Raporunu İndir",
            data=pdf_data,
            file_name=f"Ev_Raporu_{datetime.date.today().strftime('%m_%Y')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

# --- HAREKETLER ---
st.subheader("📊 Ay İçindeki Hareketler")
if not df_h.empty:
    st.dataframe(df_h[["tarih", "aciklama", "tur", "tutar"]], use_container_width=True)
else:
    st.info("Bu ay henüz bir hareket girilmemiş.")
