```python
import streamlit as st
import pandas as pd

# ==========================================
# 기본 설정
# ==========================================

st.set_page_config(
    page_title="2026 지역별 연령대 인구",
    page_icon="👥",
    layout="wide"
)

DATA_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/population_yearly.csv.gz"


# ==========================================
# 데이터 불러오기
# ==========================================

@st.cache_data
def load_data():
    return pd.read_csv(
        DATA_URL,
        compression="gzip"
    )


df = load_data()


# ==========================================
# 제목
# ==========================================

st.title("👥 2026 지역별 연령대 인구 분포")

st.write(
    "시·도 → 시·군·구 → 읍·면·동을 선택하면 "
    "해당 지역의 연령대별 인구를 확인할 수 있습니다."
)

st.info("📅 기준 연도: 2026년")


# ==========================================
# 컬럼 이름 확인
# ==========================================

columns = list(df.columns)


# 지역 관련 컬럼 자동 찾기
def find_column(candidates):
    for candidate in candidates:
        for col in columns:
            if candidate in str(col):
                return col
    return None


year_col = find_column([
    "연도",
    "년도",
    "year",
    "YEAR"
])

sido_col = find_column([
    "시도",
    "시도명"
])

sigungu_col = find_column([
    "시군구",
    "시군구명"
])

emd_col = find_column([
    "읍면동",
    "읍·면·동",
    "읍면동명"
])


# ==========================================
# 2026년 데이터만 사용
# ==========================================

if year_col is not None:

    # 연도 컬럼을 문자열로 변환
    df[year_col] = df[year_col].astype(str)

    df_2026 = df[
        df[year_col].str.contains("2026", na=False)
    ].copy()

else:
    # 연도 컬럼을 찾지 못한 경우
    # 데이터 자체가 2026년 자료라고 가정
    df_2026 = df.copy()


if df_2026.empty:
    st.error("2026년 데이터를 찾을 수 없습니다.")
    st.stop()


# ==========================================
# 지역 컬럼 확인
# ==========================================

if sido_col is None or sigungu_col is None or emd_col is None:

    st.error(
        "시도 / 시군구 / 읍면동 컬럼을 찾지 못했습니다."
    )

    st.write("현재 데이터의 컬럼:")
    st.write(columns)

    st.stop()


# ==========================================
# 시·도 선택
# ==========================================

sido_list = sorted(
    df_2026[sido_col]
    .dropna()
    .astype(str)
    .unique()
)

selected_sido = st.selectbox(
    "① 시·도를 선택하세요",
    sido_list
)


# ==========================================
# 시·군·구 선택
# ==========================================

sido_data = df_2026[
    df_2026[sido_col].astype(str) == selected_sido
].copy()


sigungu_list = sorted(
    sido_data[sigungu_col]
    .dropna()
    .astype(str)
    .unique()
)

selected_sigungu = st.selectbox(
    "② 시·군·구를 선택하세요",
    sigungu_list
)


# ==========================================
# 읍·면·동 선택
# ==========================================

sigungu_data = sido_data[
    sido_data[sigungu_col].astype(str) == selected_sigungu
].copy()


emd_list = sorted(
    sigungu_data[emd_col]
    .dropna()
    .astype(str)
    .unique()
)

selected_emd = st.selectbox(
    "③ 읍·면·동을 선택하세요",
    emd_list
)


# ==========================================
# 최종 지역 데이터
# ==========================================

region_data = sigungu_data[
    sigungu_data[emd_col].astype(str) == selected_emd
].copy()


st.divider()

st.subheader(
    f"📊 {selected_sido} {selected_sigungu} {selected_emd}"
)

st.caption("2026년 연령대별 인구 분포")


# ==========================================
# 연령 컬럼 찾기
# ==========================================

age_columns = []

for col in columns:

    col_text = str(col)

    # '0세', '1세', '2세' 등
    if "세" in col_text:

        # 지역/기타 컬럼 제외
        if (
            "연령" not in col_text
            or True
        ):
            age_columns.append(col)


# 실제 숫자형 인구 컬럼만 선택
valid_age_columns = []

for col in age_columns:

    values = pd.to_numeric(
        region_data[col],
        errors="coerce"
    )

    if values.notna().sum() > 0:
        valid_age_columns.append(col)


# ==========================================
# 연령별 숫자 추출
# ==========================================

age_population = {}

for col in valid_age_columns:

    col_text = str(col)

    number = ""

    for char in col_text:

        if char.isdigit():
            number += char
        else:
            if number:
                break

    if number:

        age = int(number)

        value = pd.to_numeric(
            region_data[col],
            errors="coerce"
        ).sum()

        age_population[age] = value


# ==========================================
# 10세 단위로 묶기
# ==========================================

age_groups = {
    "0~9세": 0,
    "10~19세": 0,
    "20~29세": 0,
    "30~39세": 0,
    "40~49세": 0,
    "50~59세": 0,
    "60~69세": 0,
    "70~79세": 0,
    "80세 이상": 0
}


for age, population in age_population.items():

    if 0 <= age <= 9:
        age_groups["0~9세"] += population

    elif 10 <= age <= 19:
        age_groups["10~19세"] += population

    elif 20 <= age <= 29:
        age_groups["20~29세"] += population

    elif 30 <= age <= 39:
        age_groups["30~39세"] += population

    elif 40 <= age <= 49:
        age_groups["40~49세"] += population

    elif 50 <= age <= 59:
        age_groups["50~59세"] += population

    elif 60 <= age <= 69:
        age_groups["60~69세"] += population

    elif 70 <= age <= 79:
        age_groups["70~79세"] += population

    elif age >= 80:
        age_groups["80세 이상"] += population


# ==========================================
# 그래프용 데이터
# ==========================================

chart_df = pd.DataFrame(
    {
        "연령대": list(age_groups.keys()),
        "인구": list(age_groups.values())
    }
)

chart_df["인구"] = chart_df["인구"].round().astype(int)


# ==========================================
# 그래프
# ==========================================

st.bar_chart(
    chart_df,
    x="연령대",
    y="인구",
    horizontal=False
)


# ==========================================
# 숫자로 확인
# ==========================================

st.subheader("📋 연령대별 인구")

st.dataframe(
    chart_df,
    use_container_width=True,
    hide_index=True
)


# ==========================================
# 총인구
# ==========================================

total_population = chart_df["인구"].sum()

st.metric(
    "👥 선택 지역 총인구",
    f"{total_population:,}명"
)


# ==========================================
# 가장 많은 연령대
# ==========================================

if total_population > 0:

    max_index = chart_df["인구"].idxmax()

    max_age_group = chart_df.loc[
        max_index,
        "연령대"
    ]

    max_population = chart_df.loc[
        max_index,
        "인구"
    ]

    st.success(
        f"📌 가장 많은 연령대는 "
        f"**{max_age_group}**이며 "
        f"인구는 **{max_population:,}명**입니다."
    )
```
