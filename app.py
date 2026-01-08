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
    
    sabit = supabase.table("sabit_gider").select("*").order("id").execute()
    hareketler = supabase.table("gelir_gider")\
        .select("*")\
        .gte("tarih", str(ay_basi))\
        .order("tarih", desc=True).execute()
        
    return pd.DataFrame(sabit.data), pd.DataFrame(hareketler.data)

# --- ANLIK GÜNCELLEME FONKSİYONU ---
def sabit_guncelle():
    # Tablodaki değişiklikleri yakala
    degisiklikler = st.session_state["sabit_editor"]["edited_rows"]
    for satir_index, degerler in degisiklikler.items():
        if "odendi" in degerler:
            # Gerçek ID'yi bul ve Supabase'e gönder
            row_id = int(st.session_state.df_sabit.iloc[satir_index]["id"])
            yeni_durum = degerler["odendi"]
            supabase.table("sabit_gider").update({"odendi": yeni_durum}).eq("id", row_id).execute()
            # Hafızadaki veriyi güncelle (Bakiyenin anında değişmesi için)
            st.session_state.df_sabit.at[satir_index, "odendi"] = yeni_durum

# --- SESSION STATE ---
if 'df_sabit' not in st.session_state:
    sabit, hareket = verileri_yukle()
    st.session_state.df_sabit = sabit
    st.session_state.df_hareket = hareket

# --- HESAPLAMA ---
toplam_gelir = st.session_state.df_hareket[st.session_state.df_hareket['tur'] == 'Gelir']['tutar'].sum() if not st.session_state.df_hareket.empty else 0
toplam_gider = st.session_state.df_hareket[st.session_state.df_hareket['tur'] == 'Gider']['tutar'].sum() if not st.session_state.df_hareket.empty else 0
odenen_sabit = st.session_state.df_sabit[st.session_state.df_sabit['odendi'] == True]['tutar'].sum() if not st.session_state.df_sabit.empty else 0
güncel_bakiye = toplam_gelir - toplam_gider - odenen_sabit

# --- ARAYÜZ ---
col_baslik, col_bakiye = st.columns([3, 1])

with col_baslik:
    st.title("🏠 Ev Yönetim Paneli")
    st.caption(f"{datetime.date.today().strftime('%B %Y')} Dönemi")

with col_bakiye:
    st.container(border=True).metric("HESAP DURUMU", f"{güncel_bakiye:,.2f} TL")

# --- SABİT GİDERLER TABLOSU ---
st.subheader("📌 Sabit Giderler")
st.data_editor(
    st.session_state.df_sabit[["id", "aciklama", "tutar", "odendi"]],
    column_config={
        "odendi": st.column_config.CheckboxColumn("Ödendi", default=False),
        "id": None 
    },
    use_container_width=True,
    hide_index=True,
    key="sabit_editor",
    on_change=sabit_guncelle # Tıklandığı an fonksiyonu çalıştırır
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
                # Verileri tazelemek için session'ı temizle
                del st.session_state.df_hareket
                st.rerun()

    st.divider()
    st.subheader("🖨️ Raporlama")
    secilen_ay = st.date_input("Rapor Alınacak Ay", value=datetime.date.today())
    if st.button("📄 Bu Ayın PDF Raporunu Al", use_container_width=True):
        st.info("Rapor hazırlanıyor...")

# --- HAREKETLER ---
st.subheader("📊 Ay İçindeki Hareketler")
if not st.session_state.df_hareket.empty:
    st.dataframe(st.session_state.df_hareket[["tarih", "aciklama", "tur", "tutar"]], use_container_width=True)
else:
    st.info("Bu ay henüz bir hareket girilmemiş.")
