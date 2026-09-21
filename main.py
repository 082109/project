import io
import requests
import pandas as pd
import plotly.express as px
import streamlit as st


# ---------------------------------------------------------
# 기본 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="전국 고령화 지도",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ 전국 고령화 지도")
st.caption("시군구별 65세 이상 인구 비율 · 최신 연도 기준")


# ---------------------------------------------------------
# 데이터 주소
# ---------------------------------------------------------
POPULATION_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/"
    "main/data/population_yearly.csv.gz"
)

GEOJSON_URL = (
    "https://raw.githubusercontent.com/greatsong/modudata/"
    "main/data/boundaries/sigungu_kr.geojson"
)


# ---------------------------------------------------------
# 데이터 불러오기
# ---------------------------------------------------------
@st.cache_data
def load_population():
    """인구 데이터를 다운로드하고 읽어 옵니다."""

    response = requests.get(POPULATION_URL, timeout=60)
    response.raise_for_status()

    # gzip 압축 파일을 메모리에서 바로 읽습니다.
    df = pd.read_csv(
        io.BytesIO(response.content),
        compression="gzip",
        dtype={"코드": str}
    )

    # 코드는 계산용 숫자가 아니라 행정구역을 연결하는 이름표입니다.
    # 혹시 숫자로 읽힌 경우에도 앞자리 0이 사라지지 않도록 처리합니다.
    df["코드"] = (
        df["코드"]
        .astype(str)
        .str.replace(".0", "", regex=False)
        .str.zfill(10)
    )

    return df


@st.cache_data
def load_geojson():
    """전국 시군구 경계 GeoJSON을 불러옵니다."""

    response = requests.get(GEOJSON_URL, timeout=60)
    response.raise_for_status()

    return response.json()


# ---------------------------------------------------------
# 고령화율 계산
# ---------------------------------------------------------
@st.cache_data
def make_sigungu_data(df):
    """읍·면·동 인구를 시군구 단위로 합쳐 고령화율을 계산합니다."""

    # 가장 최신 연도를 자동으로 선택합니다.
    latest_year = df["연도"].max()
    latest = df[df["연도"] == latest_year].copy()

    # '계_0세', '계_1세' ... 형태의 남녀 합계 나이별 열만 사용합니다.
    age_columns = [
        col for col in df.columns
        if col.startswith("계_")
    ]

    # 65세 이상에 해당하는 열을 찾습니다.
    elderly_columns = []

    for col in age_columns:
        age_text = col.replace("계_", "")

        if age_text == "100세 이상":
            elderly_columns.append(col)

        else:
            try:
                age = int(age_text)

                if age >= 65:
                    elderly_columns.append(col)

            except ValueError:
                pass

    # 모든 연령의 전체 인구
    latest["전체인구"] = latest[age_columns].sum(axis=1)

    # 65세 이상 인구
    latest["65세이상인구"] = latest[elderly_columns].sum(axis=1)

    # 행정동 코드의 앞 5자리가 시군구 코드입니다.
    latest["시군구코드"] = latest["코드"].str[:5]

    # 읍·면·동 인구를 시군구별로 합칩니다.
    sigungu = (
        latest
        .groupby("시군구코드", as_index=False)
        .agg(
            전체인구=("전체인구", "sum"),
            **{"65세이상인구": ("65세이상인구", "sum")}
        )
    )

    # 고령화율 = 65세 이상 인구 / 전체 인구 × 100
    sigungu["고령화율"] = (
        sigungu["65세이상인구"]
        / sigungu["전체인구"]
        * 100
    )

    return sigungu, latest_year


# ---------------------------------------------------------
# 단계구분 색상 만들기
# ---------------------------------------------------------
def classify_rate(rate):
    """고령화율을 5개의 구간으로 나눕니다."""

    if rate < 19:
        return "19% 미만"

    elif rate < 23:
        return "19% 이상 ~ 23% 미만"

    elif rate < 28:
        return "23% 이상 ~ 28% 미만"

    elif rate < 38:
        return "28% 이상 ~ 38% 미만"

    else:
        return "38% 이상"


# ---------------------------------------------------------
# 데이터 준비
# ---------------------------------------------------------
try:
    population_df = load_population()
    geojson = load_geojson()

    sigungu_df, latest_year = make_sigungu_data(population_df)

except Exception as e:
    st.error("데이터를 불러오는 중 문제가 발생했습니다.")
    st.exception(e)
    st.stop()


# ---------------------------------------------------------
# GeoJSON의 시군구 코드와 데이터 연결
# ---------------------------------------------------------
# GeoJSON의 코드도 문자열로 맞춰 줍니다.
for feature in geojson["features"]:
    code = str(feature["properties"]["코드"])
    feature["properties"]["코드"] = code.zfill(5)

sigungu_df["시군구코드"] = (
    sigungu_df["시군구코드"]
    .astype(str)
    .str.zfill(5)
)


# 지도 경계에 있는 시군구 정보와 인구 데이터를 코드로 연결합니다.
geo_properties = pd.DataFrame([
    {
        "시군구코드": str(feature["properties"]["코드"]).zfill(5),
        "시군구": feature["properties"]["시군구"],
        "시도": feature["properties"]["시도"]
    }
    for feature in geojson["features"]
])

map_df = geo_properties.merge(
    sigungu_df,
    on="시군구코드",
    how="left"
)


# ---------------------------------------------------------
# 고령화율 구간 만들기
# ---------------------------------------------------------
map_df["구간"] = map_df["고령화율"].apply(
    lambda x: classify_rate(x) if pd.notna(x) else "자료 없음"
)

category_order = [
    "19% 미만",
    "19% 이상 ~ 23% 미만",
    "23% 이상 ~ 28% 미만",
    "28% 이상 ~ 38% 미만",
    "38% 이상"
]


# ---------------------------------------------------------
# 지도 그리기
# ---------------------------------------------------------
st.subheader(f"{latest_year}년 시군구별 65세 이상 인구 비율")

fig = px.choropleth(
    map_df,
    geojson=geojson,
    locations="시군구코드",
    featureidkey="properties.코드",
    color="구간",
    category_orders={"구간": category_order},
    color_discrete_map={
        "19% 미만": "#edf5e8",
        "19% 이상 ~ 23% 미만": "#c9dfbf",
        "23% 이상 ~ 28% 미만": "#a4c98f",
        "28% 이상 ~ 38% 미만": "#75a95e",
        "38% 이상": "#3f7135"
    },
    custom_data=[
        "시군구",
        "시도",
        "고령화율"
    ]
)

# 배경 타일 없이 대한민국 시군구 경계만 표시합니다.
fig.update_geos(
    fitbounds="locations",
    visible=False,
    showland=False,
    showcountries=False,
    showcoastlines=False,
    showframe=False
)

# 시군구 사이의 경계선을 표시합니다.
fig.update_traces(
    marker_line_color="white",
    marker_line_width=0.5,
    hovertemplate=(
        "<b>%{customdata[0]}</b><br>"
        "시도: %{customdata[1]}<br>"
        "고령화율: %{customdata[2]:.2f}%"
        "<extra></extra>"
    )
)

fig.update_layout(
    height=750,
    margin=dict(l=0, r=0, t=20, b=0),
    legend_title_text="고령화율 구간",
    legend=dict(
        orientation="v",
        yanchor="top",
        y=0.98,
        xanchor="left",
        x=0.01,
        bgcolor="rgba(255,255,255,0.85)"
    )
)

st.plotly_chart(
    fig,
    use_container_width=True,
    config={
        "displayModeBar": False
    }
)


# ---------------------------------------------------------
# 지도 아래 통계 표
# ---------------------------------------------------------
st.subheader("📊 고령화율이 높은 지역과 낮은 지역")

# 실제 고령화율이 계산된 지역만 사용합니다.
ranking_df = map_df.dropna(
    subset=["고령화율"]
).copy()

ranking_df["고령화율"] = ranking_df["고령화율"].round(2)


# 높은 곳 10개
high_df = (
    ranking_df
    .sort_values("고령화율", ascending=False)
    .head(10)
    [["시도", "시군구", "고령화율"]]
    .reset_index(drop=True)
)

high_df.index = high_df.index + 1
high_df.index.name = "순위"


# 낮은 곳 10개
low_df = (
    ranking_df
    .sort_values("고령화율", ascending=True)
    .head(10)
    [["시도", "시군구", "고령화율"]]
    .reset_index(drop=True)
)

low_df.index = low_df.index + 1
low_df.index.name = "순위"


# 두 표를 나란히 배치합니다.
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🔴 고령화율 높은 곳 TOP 10")
    st.dataframe(
        high_df,
        use_container_width=True
    )

with col2:
    st.markdown("### 🟢 고령화율 낮은 곳 TOP 10")
    st.dataframe(
        low_df,
        use_container_width=True
    )


# ---------------------------------------------------------
# 간단한 설명
# ---------------------------------------------------------
st.caption(
    f"※ {latest_year}년 전국 읍·면·동 인구를 시군구 단위로 합산하여 "
    "65세 이상 인구 비율을 계산했습니다."
)
