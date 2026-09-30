import streamlit as st
import pandas as pd
import plotly.express as px
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import random

# ----------------- 頁面基本設定 -----------------
st.set_page_config(
    page_title="暢銷書籍社群聲量與趨勢儀表板",
    page_icon="📚",
    layout="wide"
)

st.title("📚 暢銷書籍社群聲量監測儀表板")
st.caption("支援 YouTube 影音數據即時追蹤、曝光量統計與時間趨勢分析")

# ----------------- 側邊欄設定 -----------------
with st.sidebar:
    st.header("⚙️ 數據來源設定")
    api_key = st.text_input("YouTube Data API Key (選填)", type="password", help="若無輸入，系統將以展示模擬資料呈現。")
    
    st.markdown("---")
    st.header("📖 書籍選取")
    
    # 支援上傳先前建立的 CSV 檔
    uploaded_file = st.file_uploader("上傳排行榜 CSV 檔案", type=["csv"])
    
    book_options = []
    if uploaded_file is not None:
        try:
            df_uploaded = pd.read_csv(uploaded_file)
            if "中文書名" in df_uploaded.columns:
                book_options = df_uploaded["中文書名"].dropna().tolist()
        except Exception as e:
            st.error(f"檔案讀取失敗: {e}")
            
    if not book_options:
        # 預設展示書單
        book_options = [
            "隨他們去",
            "別把你的錢留到死",
            "花錢的藝術",
            "原子習慣",
            "解憂雜貨店"
        ]
        
    selected_book = st.selectbox("選擇要分析的書籍名稱：", book_options)
    manual_input = st.text_input("或自訂搜尋關鍵字：")
    
    target_keyword = manual_input.strip() if manual_input.strip() else selected_book
    max_results = st.slider("抓取影片數量上限", min_value=10, max_value=50, value=25, step=5)

# ----------------- 數據抓取函式 -----------------
@st.cache_data(ttl=3600)
def fetch_youtube_data(keyword, key, limit=25):
    """透過 YouTube Data API v3 搜尋書籍影片並獲取互動統計"""
    try:
        youtube = build("youtube", "v3", developerKey=key)
        
        # 1. 搜尋相關影片
        search_response = youtube.search().list(
            q=keyword,
            part="id,snippet",
            maxResults=limit,
            type="video",
            order="relevance"
        ).execute()

        video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]
        if not video_ids:
            return pd.DataFrame()

        # 2. 批量取得影片統計數據 (Views, Likes, Comments)
        video_response = youtube.videos().list(
            part="snippet,statistics",
            id=",".join(video_ids)
        ).execute()

        records = []
        for item in video_response.get("items", []):
            stats = item.get("statistics", {})
            snippet = item.get("snippet", {})
            records.append({
                "影片標題": snippet.get("title"),
                "頻道名稱": snippet.get("channelTitle"),
                "發布日期": snippet.get("publishedAt")[:10],
                "曝光量 (觀看數)": int(stats.get("viewCount", 0)),
                "按讚數": int(stats.get("likeCount", 0)),
                "留言數": int(stats.get("commentCount", 0)),
                "影片連結": f"https://www.youtube.com/watch?v={item['id']}",
                "縮圖": snippet.get("thumbnails", {}).get("medium", {}).get("url")
            })

        df = pd.DataFrame(records)
        df["發布日期"] = pd.to_datetime(df["發布日期"])
        return df.sort_values(by="曝光量 (觀看數)", ascending=False)
    except Exception as e:
        st.error(f"API 請求失敗: {e}")
        return pd.DataFrame()

def generate_mock_data(keyword, limit=25):
    """模擬數據產生器（供尚未填寫 API Key 時展示）"""
    base_date = datetime.now()
    records = []
    for i in range(limit):
        pub_date = base_date - timedelta(days=random.randint(1, 180))
        views = random.randint(1500, 150000)
        likes = int(views * random.uniform(0.015, 0.05))
        comments = int(likes * random.uniform(0.05, 0.15))
        records.append({
            "影片標題": f"【說書/書評】{keyword} 核心思維導讀與實戰重點 Ep.{i+1}",
            "頻道名稱": f"閱讀推薦特輯_{i+1}台",
            "發布日期": pub_date.strftime("%Y-%m-%d"),
            "曝光量 (觀看數)": views,
            "按讚數": likes,
            "留言數": comments,
            "影片連結": "https://www.youtube.com",
            "縮圖": "https://via.placeholder.com/320x180.png?text=Book+Review"
        })
    df = pd.DataFrame(records)
    df["發布日期"] = pd.to_datetime(df["發布日期"])
    return df.sort_values(by="曝光量 (觀看數)", ascending=False)

# ----------------- 主畫面資料處理與展示 -----------------
st.subheader(f"📊 當前分析主題：【{target_keyword}】")

if api_key:
    with st.spinner("正在連線 YouTube API 擷取最新社群數據..."):
        df_results = fetch_youtube_data(target_keyword, api_key, limit=max_results)
else:
    st.info("💡 目前處於「展示模擬模式」。若需讀取即時線上即時真實數據，請於左側輸入 YouTube Data API Key。")
    df_results = generate_mock_data(target_keyword, limit=max_results)

if df_results.empty:
    st.warning("查無相關社群影音資料，請確認搜尋關鍵字或 API 配額。")
else:
    # 1. 核心指標統計卡片
    total_views = df_results["曝光量 (觀看數)"].sum()
    total_likes = df_results["按讚數"].sum()
    total_comments = df_results["留言數"].sum()
    total_interactions = total_likes + total_comments
    engagement_rate = (total_interactions / total_views * 100) if total_views > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👁️ 曝光總量 (累計觀看)", f"{total_views:,}")
    with col2:
        st.metric("💬 社群互動總量", f"{total_interactions:,}", help="按讚數 + 留言數總和")
    with col3:
        st.metric("❤️ 總按讚數", f"{total_likes:,}")
    with col4:
        st.metric("📈 互動率 (Engagement)", f"{engagement_rate:.2f}%")

    st.markdown("---")

    # 2. 時間趨勢 (按月/週累計曝光與影片數量趨勢)
    st.subheader("📅 時間趨勢分析")
    
    # 依月份聚合
    df_results["發布年月"] = df_results["發布日期"].dt.to_period("M").dt.to_timestamp()
    trend_df = df_results.groupby("發布年月").agg({
        "曝光量 (觀看數)": "sum",
        "影片標題": "count"
    }).rename(columns={"影片標題": "影片發布數"}).reset_index()

    fig = px.bar(
        trend_df,
        x="發布年月",
        y="曝光量 (觀看數)",
        title=f"各月份影片觀看累積曝光趨勢",
        text_auto=".2s",
        color="曝光量 (觀看數)",
        color_continuous_scale="Viridis"
    )
    fig.update_layout(xaxis_title="時間", yaxis_title="總觀看次數", height=380)
    st.plotly_chart(fig, use_container_width=True)

    # 3. 熱門影片列表與社群互動明細
    st.subheader("🔥 熱門影片排行 (按曝光量排序)")
    
    tab1, tab2 = st.tabs(["條列式排版", "完整資料表"])
    
    with tab1:
        for idx, row in df_results.head(5).iterrows():
            c_thumb, c_detail = st.columns([1, 3])
            with c_thumb:
                st.image(row["縮圖"], use_container_width=True)
            with c_detail:
                st.markdown(f"**[{row['影片標題']}]({row['影片連結']})**")
                st.caption(f"頻道：{row['頻道名稱']} ｜ 發布日期：{row['發布日期'].strftime('%Y-%m-%d')}")
                st.markdown(f"👁️ 觀看數：`{row['曝光量 (觀看數)']:,}` ｜ 👍 讚數：`{row['按讚數']:,}` ｜ 💬 留言數：`{row['留言數']:,}`")
            st.divider()

    with tab2:
        st.dataframe(
            df_results[["影片標題", "頻道名稱", "發布日期", "曝光量 (觀看數)", "按讚數", "留言數", "影片連結"]],
            use_container_width=True
        )