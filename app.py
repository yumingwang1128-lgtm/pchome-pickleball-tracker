from pathlib import Path
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from pickleball_tracker.dashboard import (  # noqa: E402
    count_new_products,
    filter_snapshots,
    load_snapshots,
    price_change_rankings,
    summarize_snapshots,
)


DATABASE_PATH = Path("data/tracker.db")

st.set_page_config(page_title="匹克球拍價格追蹤", layout="wide")
st.title("PChome 匹克球拍價格追蹤")
st.caption("資料為公開商品頁快照；價格不代表成交價，品牌、評分與評價數可能未提供。")

if not DATABASE_PATH.exists():
    st.info("尚無資料。請在確認資料取得權限後，以 --live 執行一次收集。")
    st.stop()

snapshots = load_snapshots(DATABASE_PATH)
if snapshots.empty:
    st.info("資料庫尚無商品快照。")
    st.stop()

minimum_date = snapshots["observed_at"].min().date()
maximum_date = snapshots["observed_at"].max().date()
minimum_price = int(snapshots["current_price"].min())
maximum_price = int(snapshots["current_price"].max())
brand_options = sorted(snapshots["brand"].dropna().unique())

with st.sidebar:
    st.header("篩選條件")
    selected_dates = st.date_input(
        "擷取日期區間",
        value=(minimum_date, maximum_date),
        min_value=minimum_date,
        max_value=maximum_date,
    )
    selected_brands = st.multiselect("品牌", brand_options, default=brand_options)
    selected_prices = st.slider(
        "目前售價（NT$）",
        min_value=minimum_price,
        max_value=maximum_price,
        value=(minimum_price, maximum_price),
    )

if not isinstance(selected_dates, tuple) or len(selected_dates) != 2:
    st.info("請選擇完整的起訖日期。")
    st.stop()

filtered = filter_snapshots(
    snapshots,
    start_date=selected_dates[0].isoformat(),
    end_date=selected_dates[1].isoformat(),
    brands=selected_brands,
    minimum_price=selected_prices[0],
    maximum_price=selected_prices[1],
)
if filtered.empty:
    st.warning("沒有符合目前篩選條件的商品快照。")
    st.stop()

summary = summarize_snapshots(filtered)
active_histories = snapshots[snapshots["product_id"].isin(filtered["product_id"])]
new_product_count = count_new_products(active_histories, selected_dates[0].isoformat())

st.caption(
    f"資料期間：{minimum_date.isoformat()} 至 {maximum_date.isoformat()}｜"
    f"篩選後 {summary['snapshot_count']} 筆快照｜最新資料日：{summary['latest_date']}"
)
col1, col2, col3, col4 = st.columns(4)
col1.metric("追蹤商品", summary["product_count"])
col2.metric("品牌數", summary["brand_count"])
col3.metric("最新中位數價格", f"NT${summary['latest_median_price']:,.0f}")
col4.metric("期間內新出現商品", new_product_count)

st.subheader("每日價格中位數")
daily_prices = (
    filtered.assign(observed_date=filtered["observed_at"].dt.date)
    .groupby("observed_date")["current_price"]
    .median()
)
st.line_chart(daily_prices)

left, right = st.columns(2)
with left:
    st.subheader("價格帶分布")
    price_bands = pd.cut(filtered["current_price"], bins=6).value_counts().sort_index()
    st.bar_chart(price_bands)
with right:
    st.subheader("最新商品的品牌分布")
    latest_products = (
        filtered.sort_values("observed_at").groupby("product_id", as_index=False).tail(1)
    )
    brand_counts = latest_products["brand"].fillna("未提供").value_counts()
    st.bar_chart(brand_counts)

st.subheader("降價幅度排行")
price_drops = price_change_rankings(filtered).head(10)
if price_drops.empty:
    st.info("目前篩選條件下，尚無可比較的降價商品。")
else:
    st.dataframe(
        price_drops[["name", "brand", "first_price", "latest_price", "price_change", "price_change_percent"]],
        column_config={
            "name": "商品名稱",
            "brand": "品牌",
            "first_price": st.column_config.NumberColumn("期初價格", format="NT$%d"),
            "latest_price": st.column_config.NumberColumn("最新價格", format="NT$%d"),
            "price_change": st.column_config.NumberColumn("變動金額", format="NT$%d"),
            "price_change_percent": st.column_config.NumberColumn("變動幅度", format="%.1f%%"),
        },
        hide_index=True,
        use_container_width=True,
    )

st.subheader("各商品最新快照")
latest_table = latest_products.sort_values("current_price", ascending=False)[
    ["name", "brand", "current_price", "original_price", "rating", "review_count", "observed_at", "url"]
]
st.dataframe(
    latest_table,
    column_config={
        "name": "商品名稱",
        "brand": "品牌",
        "current_price": st.column_config.NumberColumn("目前售價", format="NT$%d"),
        "original_price": st.column_config.NumberColumn("原價", format="NT$%d"),
        "rating": "評分",
        "review_count": "評價數",
        "observed_at": st.column_config.DatetimeColumn("擷取時間", format="YYYY-MM-DD HH:mm"),
        "url": st.column_config.LinkColumn("商品頁", display_text="查看"),
    },
    hide_index=True,
    use_container_width=True,
)

st.info(
    "目前資料僅累積約兩週，價格趨勢與降價排行僅供探索；「新出現商品」代表首次被本系統追蹤，"
    "不等於 PChome 真正新品。"
)
