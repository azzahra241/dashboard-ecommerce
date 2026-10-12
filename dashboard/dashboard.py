import os
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

st.set_page_config(page_title='Dashboard E-Commerce', layout='wide')

BASE_DIR = os.path.dirname(__file__)
DELAY_ORDER = ['Tepat waktu/Lebih cepat', 'Terlambat 1-3 hari',
               'Terlambat 4-7 hari', 'Terlambat >7 hari']

@st.cache_data
def load_data():
    delivery_df = pd.read_csv(os.path.join(BASE_DIR, 'main_data.csv'))
    category_df = pd.read_csv(os.path.join(BASE_DIR, 'category_sales.csv'))
    delivery_df['delay_category'] = pd.Categorical(
        delivery_df['delay_category'], categories=DELAY_ORDER, ordered=True
    )
    return delivery_df, category_df


delivery_df, category_df = load_data()

revenue_df = (
    category_df.groupby('product_category_name_english')['price']
    .sum().sort_values(ascending=False).reset_index()
    .rename(columns={'price': 'total_revenue'})
)
revenue_df['contribution_pct'] = revenue_df['total_revenue'] / revenue_df['total_revenue'].sum() * 100

delay_summary = (
    delivery_df.groupby('delay_category', observed=False)['review_score']
    .agg(['mean', 'count']).reset_index()
)

st.title('Dashboard Analisis E-Commerce')
st.caption('Periode data: September 2016 - Oktober 2018')

col1, col2, col3 = st.columns(3)
col1.metric('Total Pendapatan', f"{revenue_df['total_revenue'].sum() / 1e6:,.2f} juta")
col2.metric('Rata-rata Skor Review', f"{delivery_df['review_score'].mean():.2f}")
on_time = (delivery_df['delay_category'] == DELAY_ORDER[0]).mean() * 100
col3.metric('Ulasan dari Pesanan Tepat Waktu', f'{on_time:.1f}%')

st.header('Pertanyaan 1: Kategori Produk dengan Pendapatan Tertinggi')
top_n = st.slider('Jumlah kategori yang ditampilkan', min_value=5, max_value=15, value=10)

top_df = revenue_df.head(top_n).sort_values('total_revenue', ascending=True)
top5_names = revenue_df.head(5)['product_category_name_english'].tolist()
colors = ['#2E8B57' if n in top5_names else '#BDBDBD' for n in top_df['product_category_name_english']]

fig1, ax1 = plt.subplots(figsize=(10, 6))
bars = ax1.barh(top_df['product_category_name_english'], top_df['total_revenue'] / 1e6, color=colors)
ax1.bar_label(bars, labels=[f'{v/1e6:.2f} jt' for v in top_df['total_revenue']], padding=3)
ax1.set_xlim(0, top_df['total_revenue'].max() / 1e6 * 1.15)
ax1.set_xlabel('Total Pendapatan (juta)')
ax1.set_ylabel('Kategori Produk')
ax1.spines[['top', 'right']].set_visible(False)
st.pyplot(fig1)

st.info(f"Lima kategori teratas menyumbang {revenue_df.head(5)['contribution_pct'].sum():.2f}% dari total pendapatan.")

st.header('Pertanyaan 2: Keterlambatan Pengiriman dan Skor Review')

fig2, ax2 = plt.subplots(figsize=(9, 5))
bars2 = ax2.bar(delay_summary['delay_category'].astype(str), delay_summary['mean'],
                color=['#2E8B57', '#F4A261', '#E76F51', '#C0392B'])
ax2.bar_label(bars2, fmt='%.2f')
ax2.set_ylim(0, 5)
ax2.set_xlabel('Kategori Keterlambatan')
ax2.set_ylabel('Rata-rata Review Score')
ax2.spines[['top', 'right']].set_visible(False)
st.pyplot(fig2)

st.dataframe(delay_summary.rename(columns={'mean': 'rata-rata skor', 'count': 'jumlah ulasan'}))

st.subheader('Kesimpulan')
st.markdown("""
- **Pertanyaan 1:** Kategori health_beauty menjadi penyumbang pendapatan tertinggi, disusul watches_gifts dan bed_bath_table. Lima kategori teratas menyumbang 40,35% dari total pendapatan, 
dengan penurunan yang cukup tajam setelah kategori kelima.
- **Pertanyaan 2:** Skor review mulai turun signifikan sejak keterlambatan 1-3 hari (4,29 menjadi 3,29), dan penurunan terbesar terjadi pada keterlambatan 4-7 hari (3,29 menjadi 2,10). 
Pada keterlambatan lebih dari 7 hari skor rata-rata hanya 1,70. Analisis ini menunjukkan hubungan, bukan sebab-akibat, karena skor review juga dipengaruhi faktor lain seperti kualitas produk.
""")

st.subheader('Rekomendasi Action Item')
st.markdown("""
- Karena keterlambatan 1-3 hari saja berkaitan dengan penurunan skor review sekitar 1 poin (4,29 menjadi 3,29), perusahaan sebaiknya 
menyiapkan pemantauan pesanan yang berisiko melewati tanggal estimasi, lalu memberi notifikasi proaktif kepada pelanggan sebelum tenggat terlewati agar kekecewaan bisa ditekan sejak dini.
- Karena penurunan skor paling tajam terjadi pada keterlambatan 4-7 hari (3,29 menjadi 2,10) dan skor terendah ada pada keterlambatan lebih dari 7 hari (1,70), 
perusahaan sebaiknya memprioritaskan penanganan pesanan yang sudah terlambat lebih dari 3 hari, misalnya lewat eskalasi ke pihak logistik atau kompensasi, supaya tidak jatuh ke kelompok dengan kepuasan terendah.
- Karena lima kategori teratas (health_beauty, watches_gifts, bed_bath_table, sports_leisure, computers_accessories) menyumbang 40,35% dari total pendapatan, perusahaan 
sebaiknya memprioritaskan kelancaran stok dan pengiriman pada kategori-kategori tersebut terlebih dahulu, karena gangguan di sana berdampak paling besar terhadap pendapatan.
""")