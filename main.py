```python
import re
import requests
import pandas as pd
import streamlit as st
import plotly.express as px


# ==================================================
# 기본 설정
# ==================================================
st.set_page_config(
    page_title="지역별 연령별 인구 분포",
    page_icon="👥",
    layout="wide"
)

st.title("👥 2026년 지역별 연령별 인구 분포")
st.caption("행정안전부 주민등록 인구 데이터를 이용한 지역별 연령 분포")


# ==================================================
# 데이터 주소
# ==================================================
POP_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/population_yearly.csv.gz"


# ==================================================
# 데이터 불러오기
# ==================================================
@st.cache_data(show_spinner="인구 데이터를 불러오는 중입니다...")
def load_population():
    return pd.read_csv(
        POP_URL,
        dtype={"코드": str}
    )


try:
    df = load_population()
except Exception as e:
    st.error("인구 데이터를 불러오지 못했습니다.")
    st.stop()


# ==================================================
# 2026년 데이터만 사용
# ==================================================
df["연도"] = pd.to_numeric(
    df["연도"],
    errors="coerce"
)

df = df[df["연도"] == 2026].copy()

if df.empty:
    st.error("2026년 인구 데이터를 찾을 수 없습니다.")
    st.stop()


# ==================================================
# 코드 정리
# ==================================================
df["코드"] = (
    df["코드"]
    .astype(str)
    .str.replace(".0", "", regex=False)
    .str.zfill(10)
)


# ==================================================
# 연령별 '계_' 열 찾기
# 남자/여자 데이터를 더하지 않고 '계_'만 사용
# ==================================================
total_cols = [
    c for c in df.columns
    if str(c).startswith("계_")
]


def get_age(col):
    """
    계_0세
    계_1세
    ...
    계_100세 이상
    에서 나이 숫자를 추출
    """
    match = re.match(r"계_(\d+)세", str(col))

    if match:
        return int(match.group(1))

    return None


age_columns = []

for col in total_cols:

    age = get_age(col)

    if age is not None:
        age_columns.append((age, col))


age_columns = sorted(
    age_columns,
    key=lambda x: x[0]
)


if not age_columns:
    st.error("연령별 인구 열을 찾을 수 없습니다.")
    st.stop()


# ==================================================
# 지역 정보 만들기
#
# population_yearly 데이터는 행정구역 이름을
# 코드와 함께 가지고 있으므로 코드 앞자리를 이용
# ==================================================

# 데이터에 행정구역 관련 열이 있는지 확인
possible_region_cols = [
    "행정구역",
    "지역",
    "지역명",
    "읍면동"
]

region_col = None

for col in possible_region_cols:
    if col in df.columns:
        region_col = col
        break


if region_col is None:

    # 행정구역 열이 없는 경우
    # 데이터의 첫 번째 문자열 열을 찾아 사용
    text_columns = []

    for col in df.columns:

        if col in ["연도", "코드"]:
            continue

        if df[col].dtype == "object":
            text_columns.append(col)

    if text_columns:
        region_col = text_columns[0]


if region_col is None:
    st.error("지역 정보를 찾을 수 없습니다.")
    st.stop()


df["지역"] = df[region_col].astype(str)


# ==================================================
# 코드로 시도 / 시군구 / 읍면동 구분
# ==================================================

df["시도코드"] = df["코드"].str[:2]
df["시군구코드"] = df["코드"].str[:5]


# ==================================================
# 행정구역 이름에서 지역 단계 만들기
# ==================================================

def split_region(text):

    text = str(text).strip()

    # 여러 공백을 하나로
    text = re.sub(r"\s+", " ", text)

    return text.split()


df["지역_parts"] = df["지역"].apply(split_region)


# ==================================================
# 시도
# ==================================================
def get_sido(parts):

    if len(parts) >= 1:
        return parts[0]

    return ""


df["시도"] = df["지역_parts"].apply(get_sido)


sido_list = sorted(
    [
        x for x in df["시도"].unique()
        if x != ""
    ]
)


selected_sido = st.selectbox(
    "📍 1. 시도를 선택하세요",
    sido_list
)


# ==================================================
# 시군구
# ==================================================
sido_df = df[
    df["시도"] == selected_sido
].copy()


def get_sigungu(parts):

    if len(parts) >= 2:
        return parts[1]

    return ""


sido_df["시군구"] = sido_df["지역_parts"].apply(
    get_sigungu
)


sigungu_list = sorted(
    [
        x for x in sido_df["시군구"].unique()
        if x != ""
    ]
)


selected_sigungu = st.selectbox(
    "📍 2. 시군구를 선택하세요",
    sigungu_list
)


# ==================================================
# 읍면동
# ==================================================
sigungu_df = sido_df[
    sido_df["시군구"] == selected_sigungu
].copy()


def get_emd(parts):

    if len(parts) >= 3:
        return " ".join(parts[2:])

    return ""


sigungu_df["읍면동"] = sigungu_df["지역_parts"].apply(
    get_emd
)


emd_list = sorted(
    [
        x for x in sigungu_df["읍면동"].unique()
        if x != ""
    ]
)


if emd_list:

    selected_emd = st.selectbox(
        "📍 3. 읍면동을 선택하세요",
        emd_list
    )

    selected_df = sigungu_df[
        sigungu_df["읍면동"] == selected_emd
    ].copy()

    selected_name = (
        selected_sido
        + " "
        + selected_sigungu
        + " "
        + selected_emd
    )

else:

    selected_df = sigungu_df.copy()

    selected_name = (
        selected_sido
        + " "
        + selected_sigungu
    )


# ==================================================
# 선택 지역 데이터 확인
# ==================================================
if selected_df.empty:
    st.warning("선택한 지역의 데이터가 없습니다.")
    st.stop()


# ==================================================
# 연령대 설정
# ==================================================
age_groups = {
    "0~9세": range(0, 10),
    "10~19세": range(10, 20),
    "20~29세": range(20, 30),
    "30~39세": range(30, 40),
    "40~49세": range(40, 50),
    "50~59세": range(50, 60),
    "60~69세": range(60, 70),
    "70~79세": range(70, 80),
    "80세 이상": range(80, 101)
}


# ==================================================
# 연령대별 인구 계산
# ==================================================
result = []


for group_name, ages in age_groups.items():

    total = 0

    for age in ages:

        # 100세 이상
        if age == 100:

            possible_cols = [
                "계_100세 이상",
                "계_100세이상"
            ]

        else:

            possible_cols = [
                f"계_{age}세"
            ]

        for col in possible_cols:

            if col in selected_df.columns:

                values = pd.to_numeric(
                    selected_df[col],
                    errors="coerce"
                ).fillna(0)

                total += values.sum()

                break

    result.append({
        "연령대": group_name,
        "인구": int(total)
    })


age_df = pd.DataFrame(result)


# ==================================================
# 결과 표시
# ==================================================
st.divider()

st.subheader(
    f"📊 {selected_name}"
)

st.caption(
    "2026년 기준 · 0~9세부터 80세 이상까지 10세 단위로 집계"
)


# ==================================================
# 그래프
# ==================================================
fig = px.bar(
    age_df,
    x="연령대",
    y="인구",
    text="인구",
    title="연령대별 인구 분포"
)

fig.update_traces(
    texttemplate="%{text:,}명",
    textposition="outside"
)

fig.update_layout(
    height=550,
    xaxis_title="연령대",
    yaxis_title="인구 수",
    margin=dict(
        l=20,
        r=20,
        t=70,
        b=20
    )
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# ==================================================
# 표
# ==================================================
st.subheader("📋 연령대별 인구")

display_df = age_df.copy()

display_df["인구"] = display_df["인구"].apply(
    lambda x: f"{x:,}명"
)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)


# ==================================================
# 전체 인구
# ==================================================
total_population = int(
    age_df["인구"].sum()
)


st.metric(
    "👥 선택 지역 전체 인구",
    f"{total_population:,}명"
)


# ==================================================
# 가장 많은 연령대
# ==================================================
max_row = age_df.loc[
    age_df["인구"].idxmax()
]


st.success(
    f"📌 가장 많은 연령대는 "
    f"**{max_row['연령대']}**이며 "
    f"**{int(max_row['인구']):,}명**입니다."
)
```
