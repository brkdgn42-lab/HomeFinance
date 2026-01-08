import streamlit as st
from supabase import create_client
import datetime
import pandas as pd

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
    sabit = supabase.table("sabit_gider").select("*").order("id").execute()
    # Gelir/Gider (Bu ay)
    hareketler = supabase.table("gelir_gider")\
        .select("*")\
        .gte("tarih", str(ay_basi))\
        .order("tarih", desc=True).execute()
        
    return pd.DataFrame(sabit.data), pd.DataFrame(hareketler.data)

# --- SESSION STATE BAŞLATMA ---
if 'df_sabit' not in st.session_state:
    sabit, hareket = verileri_yukle()
    st.session_state.df_sabit = sabit
    st.session_state.df_hareket = hareket

# --- ÜST KISIM VE HESAPLAMA ---
# Gelir ve Gider toplamları
toplam_gelir = st.session_state.df_hareket[st.session_state.df_hareket['tur'] == 'Gelir']['tutar'].sum() if not st.session_state.df_hareket.empty else 0
toplam_gider = st.session_state.df_hareket[st.session_state.df_hareket['tur'] == 'Gider']['tutar'].sum() if not st.session_state.df_hareket.empty else 0

col_baslik, col_bakiye = st.columns([3, 1])

with col_baslik:
    st.title("🏠 Ev Yönetim Paneli")
    st.caption(f"{datetime.date.today().strftime('%B %Y')} Dönemi")

# --- ORTA KISIM: SABİT GİDERLER ---
st.subheader("📌 Sabit Giderler")

# Veri editörü (Anlık değişiklikleri yakalar)
edited_df = st.data_editor(
    st.session_state.df_sabit[["id", "aciklama", "tutar", "odendi"]],
    column_config={
        "odendi": st.column_config.CheckboxColumn("Ödendi", default=False),
        "id": None 
    },
    use_container_width=True,
    hide_index=True,
    key="sabit_editor"
)

# --- BAKİYE HESABI (EDİTÖRE GÖRE) ---
# Burada kritik nokta: Bakiye, veritabanına değil o anki tablo durumuna (edited_df) bakıyor
odenen_sabit_guncel = edited_df[edited_df['odendi'] == True]['tutar'].sum()
güncel_bakiye = toplam_gelir - toplam_gider - odenen_sabit_guncel

# Sağ üstteki bakiye güncellemesi
with col_bakiye:
    st.container(border=True).metric("HESAP DURUMU", f"{güncel_bakiye:,.2f} TL")

# --- KAYDETME VE DİĞER İŞLEMLER ---
col_save, col_empty = st.columns([1, 4])
with col_save:
    if st.button("Değişiklikleri Veritabanına Sabitle", use_container_width=True):
        for index, row in edited_df.iterrows():
            supabase.table("sabit_gider").update({"odendi": row["odendi"]}).eq("id", row["id"]).execute()
        st.success("Kaydedildi!")
        # Verileri tazelemek için session'ı temizle
        del st.session_state.df_sabit
        st.rerun()

st.divider()

# --- AKSİYON BUTONU (MODAL) ---
with st.sidebar:
    st.header("İşlemler")
    with st.popover("➕ Yeni Gelir/Gider Ekle", use_container_
