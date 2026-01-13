import streamlit as st
from supabase import create_client
import datetime
import pandas as pd
from fpdf import FPDF

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Ev Yönetim Paneli", layout="wide")

# --- BAĞLANTI ---
# Not: Localde çalıştırırken bunları secrets.toml veya çevre değişkenlerinden almalısın
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- VERİ ÇEKME FONKSİYONLARI ---
def verileri_yukle():
    bugun = datetime.date.today()
    ay_basi = bugun.replace(day=1)
    
    sabit_res = supabase.table("sabit_gider").select("*").order("id").execute()
    hareket_res = supabase.table("gelir_gider")\
        .select("*")\
        .gte("tarih", str(ay_basi))\
        .order("tarih", desc=True).execute()
        
    return pd.DataFrame(sabit_res.data), pd.DataFrame(hareket_res.data)

# --- PDF OLUŞTURMA FONKSİYONU ---
def pdf_olustur(df_sabit, df_hareket, bakiye):
    pdf = FPDF()
    pdf.add_page()
    # Not: Türkçe karakter sorunu yaşarsan fpdf2 kullanarak font eklemeliyiz
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "EV YONETIM RAPORU", ln=True, align="C")
    # ... (Geri kalan PDF kodların aynı kalabilir)
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

# --- VERİLERİ ÇEK ---
if 'df_sabit' not in st.session_state or 'df_hareket' not in st.session_state:
    sabit, hareket = verileri_yukle()
    st.session_state.df_sabit = sabit
    st.session_state.df_hareket = hareket

df_h = st.session_state.get('df_hareket', pd.DataFrame())
df_s = st.session_state.get('df_sabit', pd.DataFrame())

# --- HESAPLAMA ---
toplam_gelir = df_h[df_h['tur'] == 'Gelir']['tutar'].sum() if not df_h.empty else 0
toplam_gider = df_h[df_h['tur'] == 'Gider']['tutar'].sum() if not df_h.empty else 0
odenen_sabit = df_s[df_s['odendi'] == True]['tutar'].sum() if not df_s.empty else 0
güncel_bakiye = toplam_gelir - toplam_gider - odenen_sabit

# --- ARAYÜZ (ANA EKRAN) ---
st.title("🏠 Ev Yönetim Paneli")

# Hesap Durumu Kartı (Mobilde tam genişlik)
bakiye_metni = f"{güncel_bakiye:,.2f} €"
st.markdown(
    f"""
    <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; border: 1px solid #d1d5db; text-align: center; margin-bottom: 20px;">
        <p style="margin: 0; font-size: 16px; color: #6b7280; font-weight: bold;">GÜNCEL HESAP DURUMU</p>
        <p style="margin: 0; font-size: 28px; font-weight: 800; color: #1f2937;">{bakiye_metni}</p>
    </div>
    """, unsafe_allow_html=True
)

# --- İŞLEMLER (SIDEBAR YERİNE BURADA) ---
col1, col2 = st.columns(2)

with col1:
    # Mobilde Popover yerine Expander daha sağlıklı çalışır
    with st.expander("➕ Yeni Gelir/Gider Ekle", expanded=False):
        with st.form("yeni_kayit", clear_on_submit=True):
            tarih = st.date_input("Tarih", datetime.date.today())
            tur = st.selectbox("Tür", ["Gelir", "Gider"])
            aciklama = st.text_input("Açıklama")
            tutar = st.number_input("Tutar", min_value=0.0)
            if st.form_submit_button("Kaydet", use_container_width=True):
                data = {"tarih": str(tarih), "aciklama": aciklama, "tutar": tutar, "tur": tur}
                supabase.table("gelir_gider").insert(data).execute()
                if 'df_hareket' in st.session_state:
                    del st.session_state.df_hareket
                st.rerun()

with col2:
    with st.expander("🖨️ Raporlama Seçenekleri"):
        if st.button("📄 PDF Raporu Hazırla", use_container_width=True):
            pdf_data = pdf_olustur(df_s, df_h, güncel_bakiye)
            st.download_button(
                label="📥 İndir",
                data=pdf_data,
                file_name=f"Ev_Raporu_{datetime.date.today().strftime('%m_%Y')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

st.divider()

# --- TABLOLAR ---
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

st.subheader("📊 Ay İçindeki Hareketler")
if not df_h.empty:
    st.dataframe(df_h[["tarih", "aciklama", "tur", "tutar"]], use_container_width=True, hide_index=True)
else:
    st.info("Bu ay henüz bir hareket girilmemiş.")
