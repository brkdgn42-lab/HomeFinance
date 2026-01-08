import streamlit as st
from supabase import create_client
import datetime
import pandas as pd
from fpdf import FPDF

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Ev Yönetim Paneli", layout="wide")

# --- BAĞLANTI ---
# Bu bilgileri Streamlit Cloud panelinde "Secrets" kısmına ekleyeceğiz
url = st.secrets["https://ctbpcjqayruedqyqyxdp.supabase.co"]
key = st.secrets["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0YnBjanFheXJ1ZWRxeXF5eGRwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc4NDE1OTcsImV4cCI6MjA4MzQxNzU5N30.F7yPvg0afGK8yIKgQTfrn0JknVGLO6FAZz3J6k5hg-Q"]
supabase = create_client(url, key)

# --- VERİ ÇEKME FONKSİYONLARI ---
def verileri_getir():
    # Güncel ayın başı ve sonu
    bugun = datetime.date.today()
    ay_basi = bugun.replace(day=1)
    
    # Sabit Giderler
    sabit = supabase.table("sabit_gider").select("*").execute()
    
    # Gelir/Gider (Sadece bu ay)
    hareketler = supabase.table("gelir_gider")\
        .select("*")\
        .gte("tarih", str(ay_basi))\
        .order("tarih", desc=True).execute()
        
    return pd.DataFrame(sabit.data), pd.DataFrame(hareketler.data)

# --- VERİLERİ YÜKLE ---
df_sabit, df_hareket = verileri_getir()

# --- HESAPLAMA MANTIĞI ---
toplam_gelir = df_hareket[df_hareket['tur'] == 'Gelir']['tutar'].sum() if not df_hareket.empty else 0
toplam_gider = df_hareket[df_hareket['tur'] == 'Gider']['tutar'].sum() if not df_hareket.empty else 0
# Sadece "odendi" işaretli olan sabit giderleri hesaptan düşer
odenen_sabit = df_sabit[df_sabit['odendi'] == True]['tutar'].sum() if not df_sabit.empty else 0

güncel_baki_ye = toplam_gelir - toplam_gider - odenen_sabit

# --- ARAYÜZ: ÜST KISIM ---
col_baslik, col_bakiye = st.columns([3, 1])

with col_baslik:
    st.title("🏠 Ev Yönetim Paneli")
    st.caption(f"{datetime.date.today().strftime('%B %Y')} Dönemi")

with col_bakiye:
    st.container(border=True).metric("HESAP DURUMU", f"{güncel_baki_ye:,.2f} TL")

# --- AKSİYON BUTONU (MODAL) ---
with st.sidebar:
    st.header("İşlemler")
    with st.popover("➕ Yeni Gelir/Gider Ekle", use_container_width=True):
        with st.form("yeni_kayit", clear_on_submit=True):
            tarih = st.date_input("Tarih", datetime.date.today())
            tur = st.selectbox("Tür", ["Gelir", "Gider"])
            aciklama = st.text_input("Açıklama")
            tutar = st.number_input("Tutar", min_value=0.0)
            if st.form_submit_button("Kaydet"):
                data = {"tarih": str(tarih), "aciklama": aciklama, "tutar": tutar, "tur": tur}
                supabase.table("gelir_gider").insert(data).execute()
                st.success("İşlem kaydedildi!")
                st.rerun()

# --- ORTA KISIM: SABİT GİDERLER ---
st.subheader("📌 Sabit Giderler")
if not df_sabit.empty:
    # Kullanıcının checkbox'ları işaretleyebileceği interaktif tablo
    edited_df = st.data_editor(
        df_sabit[["id", "aciklama", "tutar", "odendi"]],
        column_config={
            "odendi": st.column_config.CheckboxColumn("Ödendi", default=False),
            "id": None # ID'yi gizle
        },
        use_container_width=True,
        key="sabit_editor"
    )
    
    # Değişiklik varsa veritabanını güncelle
    if st.button("Ödeme Durumlarını Kaydet"):
        for index, row in edited_df.iterrows():
            supabase.table("sabit_gider").update({"odendi": row["odendi"]}).eq("id", row["id"]).execute()
        st.rerun()

st.divider()

# --- ALT KISIM: HAREKETLER ---
st.subheader("📊 Ay İçindeki Hareketler")
if not df_hareket.empty:
    st.dataframe(df_hareket[["tarih", "aciklama", "tur", "tutar"]], use_container_width=True)
else:
    st.info("Bu ay henüz bir hareket girilmemiş.")

# --- PDF BÖLÜMÜ ---
st.sidebar.divider()
st.sidebar.subheader("🖨️ Raporlama")
if st.sidebar.button("Bu Ayın Raporunu İndir"):
    st.sidebar.write("PDF Hazırlanıyor...")
    # Burada FPDF ile rapor oluşturma kodları çalışacak
