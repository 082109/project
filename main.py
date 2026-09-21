```python
import streamlit as st
import pandas as pd

# =====================================
# 페이지 설정
# =====================================
st.set_page_config(
    page_title="2026 지역별 인구 분포",
    page_icon="👥",
    layout="wide"
)

st.title("👥 2026년 지역별 연령 인구 분포")
st.write("시도 → 시군구 → 읍면동을 선택하면 연령대별 인구를 확인할 수 있습니다.")

# =====================================
# 2026년 실제 데이터
# =====================================
DATA_URL = "https://raw.githubusercontent.com/greatsong/2026-pop/main/202606_202606_%EC%97%B0%EB%A0%B9%EB%B3%84%EC%9D%B8%EA%B5%AC%ED%98%84%ED%99%A9_%EC%9B%94%EA%B0%84.csv"

# =====================================
# 데이터 불러오기
# =====================================
@st.cache_data
def load_data():
    return pd.read_csv(
        DATA_URL,
        encoding="cp949"
    )

try:
    df = load_data()
except Exception as e:
    st.error("데이터를 불러오지 못했습니다.")
    st.write("잠시 후 다시 실행해 주세요.")
    st.stop()

# =====================================
# 행정구역 이름
# =====================================
region_col = "행정구역"

if region_col not in df.columns:
    st.error("행정구역 데이터를 찾을 수 없습니다.")
    st.stop()

# =====================================
# 행정구역 문자열 정리
# =====================================
df["지역"] = (
    df[region_col]
    .astype(str)
    .str.replace('"', '', regex=False)
    .str.strip()
)

# =====================================
# 지역 단계 자동 분리
# =====================================
def get_parts(region):
    return [
        x.strip()
        for x in region.split()
        if x.strip()
    ]


df["parts"] = df["지역"].apply(get_parts)

# =====================================
# 시도 목록
# =====================================
sido_list = sorted(
    df["parts"]
    .apply(lambda x: x[0] if len(x) >= 1 else "")
    .unique()
)

selected_sido = st.selectbox(
    "📍 1. 시도",
    sido_list
)

# =====================================
# 시군구 목록
# =====================================
sido_df = df[
    df["parts"].apply(
        lambda x: len(x) >= 1 and x[0] == selected_sido
    )
]

sigungu_list = sorted(
    sido_df["parts"]
    .apply(lambda x: x[1] if len(x) >= 2 else "")
    .unique()
)

sigungu_list = [
    x for x in sigungu_list if x != ""
]

selected_sigungu = st.selectbox(
    "📍 2. 시군구",
    sigungu_list
)

# =====================================
# 읍면동 목록
# =====================================
sigungu_df = sido_df[
    sido_df["parts"].apply(
        lambda x: len(x) >= 2 and x[1] == selected_sigungu
    )
]

emd_list = sorted(
    sigungu_df["parts"]
    .apply(lambda x: " ".join(x[2:]) if len(x) >= 3 else "")
    .unique()
)

emd_list = [
    x for x in emd_list if x != ""
]

if emd_list:
    selected_emd = st.selectbox(
        "📍 3. 읍면동",
        emd_list
    )

    selected_region = (
        selected_sido
        + " "
        + selected_sigungu
        + " "
        + selected_emd
    )

else:
    selected_region = (
        selected_sido
        + " "
        + selected_sigungu
    )

# =====================================
# 선택 지역 찾기
# =====================================
target = df[
    df["지역"] == selected_region
]

if target.empty:
    st.warning("선택한 지역의 데이터를 찾지 못했습니다.")
    st.stop()

row = target.iloc[0]

# =====================================
# 연령별 데이터
# =====================================
age_data = {
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

# =====================================
# 0세 ~ 100세 이상 데이터 읽기
# =====================================
for age in range(101):

    if age == 100:
        column = "2026년06월_계_100세 이상"
    else:
        column = f"2026년06월_계_{age}세"

    if column not in df.columns:
        continue

    value = str(row[column])

    # 쉼표 제거
    value = value.replace(",", "")
    value = value.strip()

    try:
        value = int(float(value))
    except:
        value = 0

    if age <= 9:
        age_data["0~9세"] += value

    elif age <= 19:
        age_data["10~19세"] += value

    elif age <= 29:
        age_data["20~29세"] += value

    elif age <= 39:
        age_data["30~39세"] += value

    elif age <= 49:
        age_data["40~49세"] += value

    elif age <= 59:
        age_data["50~59세"] += value

    elif age <= 69:
        age_data["60~69세"] += value

    elif age <= 79:
        age_data["70~79세"] += value

    else:
        age_data["80세 이상"] += value

# =====================================
# 그래프용 데이터
# =====================================
chart_df = pd.DataFrame(
    {
        "연령대": list(age_data.keys()),
        "인구": list(age_data.values())
    }
)

# =====================================
# 결과
# =====================================
st.divider()

st.subheader(
    f"📊 {selected_region}"
)

st.caption("2026년 6월 기준 · 행정안전부 연령별 인구현황")

# =====================================
# 막대그래프
# =====================================
st.bar_chart(
    chart_df.set_index("연령대"),
    height=500
)

# =====================================
# 숫자 표
# =====================================
st.subheader("📋 연령대별 인구")

display_df = chart_df.copy()

display_df["인구"] = display_df["인구"].apply(
    lambda x: f"{x:,}명"
)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)

# =====================================
# 전체 인구
# =====================================
total = sum(age_data.values())

st.metric(
    "👥 선택 지역 인구",
    f"{total:,}명"
)

# =====================================
# 가장 많은 연령대
# =====================================
max_age = max(
    age_data,
    key=age_data.get
)

st.success(
    f"📌 가장 많은 연령대: **{max_age}** "
    f"({age_data[max_age]:,}명)"
)
```
