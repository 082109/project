import re
import requests
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="🐈 전국 고령화 지도",
    page_icon="🐈",
    layout="wide"
)

# =========================
# 🐈 고양이 테마
# =========================
st.markdown("""
<style>
    .stApp {
        background-color: #F7FAFF;
    }

    h1 {
        color: #315B8C !important;
        font-weight: 800 !important;
    }

    h2, h3 {
        color: #416D9F !important;
    }

    .stCaption {
        color: #6D849E !important;
    }

    [data-testid="stDataFrame"] {
        border: 2px solid #C9DCF2;
        border-radius: 12px;
        overflow: hidden;
    }

    .cat-box {
        background-color: #EAF4FF;
        padding: 14px 20px;
        border-radius: 15px;
        border: 2px solid #C9DCF2;
        margin-bottom: 15px;
        color: #365A7D;
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)


# =========================
# 제목
# =========================
st.title("🐈 전국 고령화 지도")

st.caption(
    "🐾 시군구별 65세 이상 인구 비율을 한눈에 확인해보세요!"
)

st.markdown("""
<div class="cat-box">
🐾 <b>지역별 고령화율을 색으로 확인해보세요!</b><br>
파란색이 진할수록 65세 이상 인구 비율이 높은 지역입니다.
</div>
""", unsafe_allow_html=True)


POP_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/population_yearly.csv.gz"
GEO_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/boundaries/sigungu_kr.geojson"


@st.cache_data(show_spinner="🐱 인구 데이터를 불러오는 중입니다...")
def load_population():
    return pd.read_csv(POP_URL, dtype={"코드": str})


@st.cache_data(show_spinner="🐱 지도 경계를 불러오는 중입니다...")
def load_geojson():
    return requests.get(GEO_URL, timeout=30).json()


df = load_population()
geojson = load_geojson()


# =========================
# 최신 연도
# =========================
latest_year = int(df["연도"].max())
df = df[df["연도"] == latest_year].copy()


# =========================
# 전체 인구 / 65세 이상 인구
# =========================
total_cols = [c for c in df.columns if c.startswith("계_")]


def age_of(col):
    m = re.match(r"계_(\d+)세", col)
    return int(m.group(1)) if m else None


elderly_cols = [
    c for c in total_cols
    if age_of(c) is not None and age_of(c) >= 65
]


df["전체인구"] = df[total_cols].sum(axis=1)
df["고령인구"] = df[elderly_cols].sum(axis=1)


# =========================
# 시군구별 계산
# =========================
df["시군구코드"] = df["코드"].str[:5]

grouped = (
    df.groupby("시군구코드")[["전체인구", "고령인구"]]
    .sum()
    .reset_index()
)

# 고령화율 = 65세 이상 인구 / 전체 인구 × 100
grouped["고령화율"] = (
    grouped["고령인구"]
    / grouped["전체인구"]
    * 100
).round(2)


# =========================
# 시군구 이름 연결
# =========================
names = pd.DataFrame([
    {
        "시군구코드": str(f["properties"]["코드"]),
        "시군구": f["properties"]["시군구"],
        "시도": f["properties"]["시도"],
    }
    for f in geojson["features"]
])

merged = grouped.merge(
    names,
    on="시군구코드",
    how="left"
)


# =========================
# 💙 파란색 5단계
# =========================
BINS = [0, 19, 23, 28, 38, 100]

LABELS = [
    "19% 미만",
    "19~23%",
    "23~28%",
    "28~38%",
    "38% 이상"
]

COLORS = {
    "19% 미만": "#E3F2FD",
    "19~23%": "#90CAF9",
    "23~28%": "#42A5F5",
    "28~38%": "#1976D2",
    "38% 이상": "#0D47A1",
}

merged["단계"] = pd.cut(
    merged["고령화율"],
    bins=BINS,
    labels=LABELS,
    right=False
)


# =========================
# 🗺️ 지도
# =========================
fig = px.choropleth(
    merged,
    geojson=geojson,
    locations="시군구코드",
    featureidkey="properties.코드",
    color="단계",
    category_orders={"단계": LABELS},
    color_discrete_map=COLORS,
    hover_name="시군구",
    hover_data={
        "고령화율": True,
        "시도": True,
        "시군구코드": False,
        "단계": False
    },
    labels={
        "고령화율": "65세 이상 비율(%)"
    }
)

fig.update_geos(
    fitbounds="locations",
    visible=False
)

fig.update_layout(
    margin=dict(l=0, r=0, t=10, b=0),
    height=700,
    paper_bgcolor="#F7FAFF",
    plot_bgcolor="#F7FAFF",
    legend_title_text=f"🐾 65세 이상 비율 ({latest_year}년)"
)

st.plotly_chart(fig, width="stretch")


# =========================
# 📊 순위
# =========================
c1, c2 = st.columns(2)

cols = ["시도", "시군구", "고령화율"]

with c1:
    st.subheader("🔵 고령화율 높은 곳 10")
    st.dataframe(
        merged.nlargest(10, "고령화율")[cols]
        .reset_index(drop=True),
        width="stretch"
    )

with c2:
    st.subheader("🐾 고령화율 낮은 곳 10")
    st.dataframe(
        merged.nsmallest(10, "고령화율")[cols]
        .reset_index(drop=True),
        width="stretch"
    )


st.markdown("""
<div style="text-align:center; color:#66809B; padding:20px;">
🐈 냥냥! 우리나라 지역별 고령화 현황을 살펴보세요 💙🐾
</div>
""", unsafe_allow_html=True)
