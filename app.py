from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st


DATABASE_PATH = Path("data/tracker.db")

st.set_page_config(page_title="匹克球拍價格追蹤", layout="wide")
st.title("PChome 匹克球拍價格追蹤")
st.caption("資料為公開商品頁快照；價格不代表成交價，品牌、評分與評價數可能未提供。")

if not DATABASE_PATH.exists():
    st.info("尚無資料。請在確認資料取得權限後，以 --live 執行一次收集。")
    st.stop()

with sqlite3.connect(DATABASE_PATH) as connection:
    snapshots = pd.read_sql_query(
        """
        SELECT p.name, p.brand, s.observed_at, s.current_price, s.original_price,
               s.rating, s.review_count, s.availability
        FROM price_snapshots AS s JOIN products AS p USING(product_id)
        ORDER BY s.observed_at
        """,
        connection,
        parse_dates=["observed_at"],
    )

if snapshots.empty:
    st.info("資料庫尚無商品快照。")
    st.stop()

brand_options = sorted(snapshots["brand"].dropna().unique())
selected_brands = st.multiselect("品牌", brand_options, default=brand_options)
if selected_brands:
    snapshots = snapshots[snapshots["brand"].isin(selected_brands)]

first_seen = snapshots.sort_values("observed_at").groupby("name", as_index=False).first()
col1, col2, col3 = st.columns(3)
col1.metric("追蹤商品", snapshots["name"].nunique())
col2.metric("最新中位數價格", f"NT${snapshots['current_price'].median():,.0f}")
col3.metric("已觀察新品", len(first_seen))
st.subheader("價格趨勢")
st.line_chart(snapshots.set_index("observed_at").groupby(level=0)["current_price"].median())
st.subheader("價格帶分布")
st.bar_chart(snapshots["current_price"].value_counts(bins=8).sort_index())
st.subheader("最近快照")
st.dataframe(snapshots.sort_values("observed_at", ascending=False), use_container_width=True)
