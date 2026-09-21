import re
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="지역별 연령별 인구 분포", layout="wide")

st.title("👥 지역별 연령별 인구 분포")
st.caption("2026년 행정안전부 주민등록 인구 기준")

POP_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/population_yearly.csv.gz"


# 1. 인구 데이터 불러오기
@st.cache_data(show_spinner="인구 데이터를 불러오는 중입니다...")
def load_population():
    return pd.read_csv(POP_URL, dtype={"코드": str})


df = load_population()


# 2. 2026년 데이터만 사용
df = df[df["연도"] == 2026].copy()


# 3. 지역명 열 찾기
# 데이터의 행정구역 열을 자동으로 찾습니다.
region_col = None

for col in ["행정구역", "행정구역명", "지역", "지역명"]:
    if col in df.columns:
        region_col = col
        break

if region_col is None:
    st.error("행정구역 이름 열을 찾을 수 없습니다.")
    st.stop()


# 4. 행정구역을 시도 / 시군구 / 읍면동으로 나누기
def split_region(value):
    parts = str(value).split()

    if len(parts) >= 3:
        return pd.Series({
            "시도": parts[0],
            "시군구": parts[1],
            "읍면동": " ".join(parts[2:])
        })

    elif len(parts) == 2:
        return pd.Series({
            "시도": parts[0],
            "시군구": parts[1],
            "읍면동": ""
        })

    else:
        return pd.Series({
            "시도": parts[0] if parts else "",
            "시군구": "",
            "읍면동": ""
        })


region_parts = df[region_col].apply(split_region)
df = pd.concat([df, region_parts], axis=1)


# 5. 시도 선택
st.subheader("📍 지역 선택")

sido_list = sorted(df["시도"].dropna().unique())

selected_sido = st.selectbox(
    "① 시도",
    sido_list
)


# 6. 시군구 선택
sigungu_df = df[df["시도"] == selected_sido]

sigungu_list = sorted(
    sigungu_df["시군구"].dropna().unique()
)

selected_sigungu = st.selectbox(
    "② 시군구",
    sigungu_list
)


# 7. 읍면동 선택
dong_df = sigungu_df[
    sigungu_df["시군구"] == selected_sigungu
]

dong_list = sorted(
    dong_df["읍면동"].dropna().unique()
)

selected_dong = st.selectbox(
    "③ 읍면동",
    dong_list
)


# 8. 선택한 지역 데이터
selected = dong_df[
    dong_df["읍면동"] == selected_dong
].copy()


# 9. 연령대별 열 만들기
def age_number(col):
    match = re.match(r"계_(\d+)세", col)
    return int(match.group(1)) if match else None


age_cols = [
    col for col in df.columns
    if col.startswith("계_") and age_number(col) is not None
]


# 10. 9개 연령대로 묶기
age_groups = {
    "0~9세": range(0, 10),
    "10~19세": range(10, 20),
    "20~29세": range(20, 30),
    "30~39세": range(30, 40),
    "40~49세": range(40, 50),
    "50~59세": range(50, 60),
    "60~69세": range(60, 70),
    "70~79세": range(70, 80),
    "80세 이상": range(80, 101),
}


result = []

for group_name, ages in age_groups.items():

    columns = []

    for col in age_cols:
        age = age_number(col)

        if age in ages:
            columns.append(col)

    population = selected[columns].sum().sum()

    result.append({
        "연령대": group_name,
        "인구수": int(population)
    })


age_df = pd.DataFrame(result)


# 11. 선택 지역 표시
st.divider()

st.subheader(
    f"📊 {selected_sido} {selected_sigungu} {selected_dong}"
)

# 전체 인구
total_population = age_df["인구수"].sum()

st.metric(
    "전체 인구",
    f"{total_population:,}명"
)


# 12. 연령별 막대그래프
fig = px.bar(
    age_df,
    x="연령대",
    y="인구수",
    text="인구수",
    labels={
        "연령대": "연령대",
        "인구수": "인구수(명)"
    },
    title="2026년 연령대별 인구 분포"
)

fig.update_traces(
    texttemplate="%{text:,}",
    textposition="outside"
)

fig.update_layout(
    margin=dict(l=20, r=20, t=60, b=20),
    height=500,
    xaxis_title="연령대",
    yaxis_title="인구수(명)"
)

st.plotly_chart(
    fig,
    width="stretch"
)


# 13. 연령대별 표
st.subheader("📋 연령대별 인구")

display_df = age_df.copy()

display_df["인구수"] = display_df["인구수"].map(
    lambda x: f"{x:,}명"
)

st.dataframe(
    display_df,
    width="stretch",
    hide_index=True
)


# 14. 가장 많은 연령대
largest = age_df.loc[
    age_df["인구수"].idxmax()
]

st.info(
    f"가장 많은 연령대는 **{largest['연령대']}**로 "
    f"**{int(largest['인구수']):,}명**입니다."
)
