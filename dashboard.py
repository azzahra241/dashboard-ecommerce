import os

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title='Dashboard E-Commerce', layout='wide')

BASE_DIR = os.path.dirname(__file__)
DELAY_ORDER = ['Tepat waktu/Lebih cepat', 'Terlambat 1-3 hari',
               'Terlambat 4-7 hari', 'Terlambat >7 hari']

# Palet warna: satu warna dasar untuk perbandingan, satu warna lebih gelap untuk sorotan
BASE_COLOR = '#B8C7D9'
HIGHLIGHT_COLOR = '#1F5FA8'


@st.cache_data
def load_data():
    delivery_df = pd.read_csv(os.path.join(BASE_DIR, 'main_data.csv'),
                              parse_dates=['order_purchase_date'])
    category_df = pd.read_csv(os.path.join(BASE_DIR, 'category_sales.csv'),
                              parse_dates=['order_purchase_date'])
    delivery_df['delay_category'] = pd.Categorical(
        delivery_df['delay_category'], categories=DELAY_ORDER, ordered=True
    )
    return delivery_df, category_df


delivery_df, category_df = load_data()

# ---------- Sidebar: filter ----------
min_date = min(delivery_df['order_purchase_date'].min(),
               category_df['order_purchase_date'].min()).date()
max_date = max(delivery_df['order_purchase_date'].max(),
               category_df['order_purchase_date'].max()).date()

st.sidebar.header('Filter')
date_range = st.sidebar.date_input(
    'Periode pemesanan',
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)
if len(date_range) != 2:
    st.info('Pilih tanggal awal dan tanggal akhir pada filter periode pemesanan.')
    st.stop()
start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])

all_categories = sorted(category_df['product_category_name_english'].unique())
selected_categories = st.sidebar.multiselect(
    'Kategori produk',
    options=all_categories,
    help='Kosongkan untuk menampilkan semua kategori.',
)

# ---------- Terapkan filter ----------
category_f = category_df[category_df['order_purchase_date'].between(start_date, end_date)]
if selected_categories:
    category_f = category_f[category_f['product_category_name_english'].isin(selected_categories)]

delivery_f = delivery_df[delivery_df['order_purchase_date'].between(start_date, end_date)]
if selected_categories:
    delivery_f = delivery_f[delivery_f['order_id'].isin(category_f['order_id'])]

if category_f.empty or delivery_f.empty:
    st.warning('Tidak ada data untuk kombinasi filter yang dipilih. Ubah periode atau kategori.')
    st.stop()

# ---------- Data turunan ----------
revenue_df = (
    category_f.groupby('product_category_name_english', as_index=False)['price'].sum()
    .rename(columns={'product_category_name_english': 'kategori', 'price': 'total_revenue'})
    .sort_values('total_revenue', ascending=False)
    .reset_index(drop=True)
)
total_revenue = revenue_df['total_revenue'].sum()
revenue_df['kontribusi_pct'] = revenue_df['total_revenue'] / total_revenue * 100
top5_share = revenue_df.head(5)['kontribusi_pct'].sum()
on_time_pct = (delivery_f['delay_category'] == DELAY_ORDER[0]).mean() * 100

# ---------- Header & metrik utama ----------
st.title('Dashboard Analisis E-Commerce')
st.caption('Gunakan filter di sebelah kiri untuk mengatur periode pemesanan dan kategori produk.')

col1, col2, col3, col4 = st.columns(4)
col1.metric('Total Pendapatan', f'{total_revenue / 1e6:,.2f} juta')
col2.metric('Kontribusi 5 Kategori Teratas', f'{top5_share:.2f}%')
col3.metric('Rata-rata Skor Review', f"{delivery_f['review_score'].mean():.2f}")
col4.metric('Ulasan dari Pesanan Tepat Waktu', f'{on_time_pct:.1f}%')

# ---------- Visualisasi 1: pendapatan per kategori ----------
st.subheader('Kategori Produk dengan Pendapatan Tertinggi')

max_n = min(15, len(revenue_df))
if max_n > 5:
    top_n = st.slider('Jumlah kategori yang ditampilkan', min_value=5,
                      max_value=max_n, value=min(10, max_n))
else:
    top_n = max_n

top_df = revenue_df.head(top_n).copy()
top_df['kelompok'] = ['5 kategori teratas' if i < 5 else 'Lainnya' for i in range(len(top_df))]
top_df['pendapatan_juta'] = top_df['total_revenue'] / 1e6

fig1 = px.bar(
    top_df,
    x='pendapatan_juta',
    y='kategori',
    orientation='h',
    color='kelompok',
    color_discrete_map={'5 kategori teratas': HIGHLIGHT_COLOR, 'Lainnya': BASE_COLOR},
    text=top_df['pendapatan_juta'].map('{:.2f} jt'.format),
    hover_data={'pendapatan_juta': ':.2f', 'kontribusi_pct': ':.2f', 'kelompok': False},
    labels={'pendapatan_juta': 'Total Pendapatan (juta)',
            'kontribusi_pct': 'Kontribusi (%)', 'kategori': 'Kategori Produk'},
)
fig1.update_yaxes(categoryorder='total ascending', title=None)
fig1.update_xaxes(title='Total Pendapatan (juta)', automargin=True)
fig1.update_traces(textposition='outside', cliponaxis=False)
fig1.update_layout(legend_title_text='', plot_bgcolor='white', paper_bgcolor='white',
                   font=dict(color='#31333F'),
                   margin=dict(l=140, r=60, t=40, b=60), height=470)
st.plotly_chart(fig1, theme=None)

# ---------- Visualisasi 2: keterlambatan vs skor review ----------
st.subheader('Keterlambatan Pengiriman dan Rata-rata Skor Review')
if selected_categories:
    st.caption('Dengan filter kategori aktif, analisis ini memakai pesanan yang memuat kategori terpilih.')

delay_summary = (
    delivery_f.groupby('delay_category', observed=False)['review_score']
    .agg(rata_rata='mean', jumlah='count')
    .reset_index()
    .dropna(subset=['rata_rata'])
)
delay_summary['delay_category'] = delay_summary['delay_category'].astype(str)
lowest_idx = delay_summary['rata_rata'].idxmin()
delay_summary['sorotan'] = ['Skor terendah' if i == lowest_idx else 'Lainnya'
                            for i in delay_summary.index]

fig2 = px.bar(
    delay_summary,
    x='delay_category',
    y='rata_rata',
    color='sorotan',
    color_discrete_map={'Skor terendah': HIGHLIGHT_COLOR, 'Lainnya': BASE_COLOR},
    category_orders={'delay_category': DELAY_ORDER},
    text=delay_summary['rata_rata'].map('{:.2f}'.format),
    hover_data={'rata_rata': ':.2f', 'jumlah': ':,', 'sorotan': False},
    labels={'delay_category': 'Kategori Keterlambatan',
            'rata_rata': 'Rata-rata Review Score', 'jumlah': 'Jumlah ulasan'},
)
fig2.update_yaxes(range=[0, 5], title='Rata-rata Review Score')
fig2.update_xaxes(title='Kategori Keterlambatan', automargin=True)
fig2.update_traces(textposition='outside')
fig2.update_layout(legend_title_text='', plot_bgcolor='white', paper_bgcolor='white',
                   font=dict(color='#31333F'),
                   margin=dict(l=50, r=60, t=30, b=60), height=440)
st.plotly_chart(fig2, theme=None)

with st.expander('Lihat data ringkasan'):
    st.dataframe(
        delay_summary[['delay_category', 'rata_rata', 'jumlah']].rename(columns={
            'delay_category': 'Kategori Keterlambatan',
            'rata_rata': 'Rata-rata Skor Review',
            'jumlah': 'Jumlah Ulasan',
        }),
        hide_index=True,
    )