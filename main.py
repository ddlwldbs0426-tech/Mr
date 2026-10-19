
import re

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# --------------------------------------------------
# 1. 페이지 설정
# --------------------------------------------------
st.set_page_config(
    page_title="전국 고령화 단계구분도",
    page_icon="🗺️",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #FFF9F2; }
    h1, h2, h3 { color: #6D4938; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🗺️ 전국 고령화 단계구분도")
st.caption("2026년 6월 기준 · 시군구별 65세 이상 인구 비율")

# --------------------------------------------------
# 2. 데이터 주소
# --------------------------------------------------
POPULATION_URL = (
    "https://raw.githubusercontent.com/"
    "ddlwldbs0426-tech/Mr/main/sigungu_kr.geojson.txt"
)
BOUNDARY_URL = (
    "https://raw.githubusercontent.com/"
    "first2022-cyber/contents/main/sigungu_kr.geojson"
)

TARGET_YEAR = 2026
ELDERLY_AGES = [f"{age}세" for age in range(65, 100)] + ["100세 이상"]


# --------------------------------------------------
# 3. 지역 코드 표준화
# --------------------------------------------------
def normalize_code(value):
    """지역 코드를 문자열로 변환하고 앞 5자리를 시군구 코드로 사용합니다."""
    if pd.isna(value):
        return None

    code = str(value).strip()

    # 숫자형으로 읽힌 코드가 11010.0처럼 보이는 경우 처리
    if code.endswith(".0"):
        code = code[:-2]

    digits = re.sub(r"\D", "", code)
    if not digits:
        return None

    return digits.zfill(5)[:5]


# --------------------------------------------------
# 4. 인구 데이터 읽기 및 시군구별 계산
# --------------------------------------------------
@st.cache_data(show_spinner="2026년 인구 데이터를 불러오는 중입니다...")
def load_population():
    # 제공된 인구 파일을 ZIP 압축 CSV로 읽습니다.
    df = pd.read_csv(
        POPULATION_URL,
        compression="zip",
        dtype={"코드": "string"},
    )
    df.columns = df.columns.astype(str).str.strip()

    required = ["연도", "코드"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"필수 열이 없습니다: {', '.join(missing)}")

    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df = df[df["연도"] == TARGET_YEAR].copy()

    if df.empty:
        raise ValueError(f"{TARGET_YEAR}년 인구 자료를 찾을 수 없습니다.")

    # 전체 인구는 '계_'로 시작하는 열만 합산합니다.
    total_columns = [
        col for col in df.columns if col.startswith("계_")
    ]
    if not total_columns:
        raise ValueError("'계_0세' 형식의 인구 열을 찾지 못했습니다.")

    # 65세 이상은 계_65세부터 계_100세 이상까지 합산합니다.
    elderly_columns = [f"계_{age}" for age in ELDERLY_AGES]
    missing_elderly = [
        col for col in elderly_columns if col not in df.columns
    ]
    if missing_elderly:
        raise ValueError(
            "65세 이상 인구 열이 누락되었습니다: "
            + ", ".join(missing_elderly[:8])
        )

    # 인구 열은 숫자로 변환하고 결측값은 0으로 처리합니다.
    for col in total_columns:
        df[col] = pd.to_numeric(
            df[col], errors="coerce"
        ).fillna(0)

    # 동 코드 앞 5자리를 시군구 코드로 사용합니다.
    df["시군구코드"] = df["코드"].apply(normalize_code)
    df = df.dropna(subset=["시군구코드"])

    # 남성·여성 열은 더하지 않고 계_ 열만 사용합니다.
    df["전체인구"] = df[total_columns].sum(axis=1)
    df["고령인구"] = df[elderly_columns].sum(axis=1)

    # 시군구별로 인구를 합산한 다음 고령화율을 계산합니다.
    result = (
        df.groupby("시군구코드", as_index=False)
        .agg(
            전체인구=("전체인구", "sum"),
            고령인구=("고령인구", "sum"),
        )
    )

    result["고령화율"] = (
        result["고령인구"]
        .div(result["전체인구"].where(result["전체인구"] > 0))
        .mul(100)
    )

    return result


# --------------------------------------------------
# 5. 경계 GeoJSON 다운로드
# --------------------------------------------------
@st.cache_data(show_spinner="시군구 경계 지도를 불러오는 중입니다...")
def load_geojson():
    response = requests.get(
        BOUNDARY_URL,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()
    geojson = response.json()

    if not isinstance(geojson, dict) or "features" not in geojson:
        raise ValueError("경계 파일이 올바른 GeoJSON 형식이 아닙니다.")

    # 경계 코드도 문자열 5자리로 통일합니다.
    for feature in geojson["features"]:
        props = feature.setdefault("properties", {})

        if "코드" not in props:
            raise ValueError("GeoJSON feature에 '코드' 속성이 없습니다.")

        props["코드"] = normalize_code(props["코드"])

        if "시군구" not in props:
            raise ValueError("GeoJSON feature에 '시군구' 속성이 없습니다.")

    return geojson


# --------------------------------------------------
# 6. 데이터 불러오기
# --------------------------------------------------
try:
    population_df = load_population()
    geojson = load_geojson()

except Exception as exc:
    st.error("데이터를 불러오거나 처리하지 못했습니다.")
    st.markdown(
        """
        **확인 사항:** 인구 데이터 주소의 파일명은
        `sigungu_kr.geojson.txt`입니다. 실제 내용이 ZIP 압축 CSV여야
        `compression="zip"`으로 읽을 수 있습니다.

        파일이 일반 CSV라면 `compression="zip"`을 제거하고,
        GeoJSON이라면 실제 인구 CSV 주소로 `POPULATION_URL`을 바꿔 주세요.
        """
    )
    st.exception(exc)
    st.stop()


# --------------------------------------------------
# 7. 코드로 지도와 인구 데이터 연결
# --------------------------------------------------
# 이름이 아니라 시군구 5자리 코드로 연결합니다.
geojson_codes = {
    feature["properties"]["코드"]
    for feature in geojson["features"]
    if feature["properties"].get("코드")
}

population_df = population_df[
    population_df["시군구코드"].isin(geojson_codes)
].copy()

# 시군구 이름은 GeoJSON의 속성에서 코드 기준으로 가져옵니다.
name_by_code = {
    feature["properties"]["코드"]: feature["properties"]["시군구"]
    for feature in geojson["features"]
    if feature["properties"].get("코드")
}

population_df["시군구"] = population_df["시군구코드"].map(name_by_code)

# 전체 인구가 0이어서 비율을 계산할 수 없는 지역은 제외합니다.
map_df = population_df.dropna(subset=["고령화율"]).copy()

if map_df.empty:
    st.warning(
        "인구 데이터와 GeoJSON의 코드가 일치하지 않습니다. "
        "두 파일의 코드가 동일한 5자리 체계인지 확인해 주세요."
    )
    st.stop()


# --------------------------------------------------
# 8. 전국 요약 지표
# --------------------------------------------------
national_total = int(map_df["전체인구"].sum())
national_elderly = int(map_df["고령인구"].sum())

national_rate = (
    national_elderly / national_total * 100
    if national_total > 0
    else 0
)

st.subheader("📌 전국 요약")

metric1, metric2, metric3 = st.columns(3)
metric1.metric("전체 인구", f"{national_total:,}명")
metric2.metric("65세 이상 인구", f"{national_elderly:,}명")
metric3.metric("전국 고령화율", f"{national_rate:.1f}%")

highest = map_df.loc[map_df["고령화율"].idxmax()]
lowest = map_df.loc[map_df["고령화율"].idxmin()]

st.caption(
    f"고령화율이 가장 높은 지역: {highest['시군구']} "
    f"({highest['고령화율']:.1f}%) · "
    f"가장 낮은 지역: {lowest['시군구']} "
    f"({lowest['고령화율']:.1f}%)"
)


# --------------------------------------------------
# 9. Plotly 단계구분도
# --------------------------------------------------
st.subheader("🧭 시군구별 고령화율")

fig = go.Figure(
    go.Choropleth(
        geojson=geojson,
        featureidkey="properties.코드",
        locations=map_df["시군구코드"].astype(str),
        z=map_df["고령화율"],
        customdata=map_df[["시군구"]].to_numpy(),
        colorscale=[
            [0.00, "#FFF1DF"],
            [0.25, "#F7C995"],
            [0.50, "#E99A63"],
            [0.75, "#C96645"],
            [1.00, "#873B32"],
        ],
        zmin=0,
        zmax=max(40, float(map_df["고령화율"].max())),
        marker=dict(
            line=dict(color="#FFFFFF", width=0.45)
        ),
        colorbar=dict(
            title=dict(text="고령화율 (%)"),
            ticksuffix="%",
            thickness=18,
            len=0.75,
        ),
        hovertemplate=(
            "시군구: %{customdata[0]}<br>"
            "고령화율: %{z:.2f}%"
            "<extra></extra>"
        ),
    )
)

# 배경 타일 없이 GeoJSON 경계만 표시합니다.
fig.update_geos(
    visible=False,
    fitbounds="locations",
    showcountries=False,
    showcoastlines=False,
    showland=False,
    showocean=False,
    showlakes=False,
    showrivers=False,
    showframe=False,
)

fig.update_layout(
    title=dict(
        text="2026년 시군구별 고령화율 (65세 이상 인구 비율)",
        x=0.5,
        xanchor="center",
        font=dict(size=21, color="#6D4938"),
    ),
    paper_bgcolor="#FFF9F2",
    plot_bgcolor="#FFF9F2",
    font=dict(
        family="Arial, sans-serif",
        color="#5C514A",
    ),
    margin=dict(l=10, r=10, t=65, b=10),
    height=780,
)

st.plotly_chart(fig, use_container_width=True)

st.caption(
    "색이 진할수록 고령화율이 높습니다. "
    "지도는 제공된 시군구 GeoJSON 경계를 사용하며 배경 타일은 표시하지 않습니다."
)


# --------------------------------------------------
# 10. 시군구별 고령화율 표
# --------------------------------------------------
with st.expander("시군구별 고령화율 표 보기"):
    display_df = map_df[
        ["시군구코드", "시군구", "전체인구", "고령인구", "고령화율"]
    ].copy()

    display_df = display_df.sort_values(
        "고령화율", ascending=False
    )

    display_df = display_df.rename(
        columns={
            "시군구코드": "코드",
            "전체인구": "전체 인구",
            "고령인구": "65세 이상 인구",
            "고령화율": "고령화율 (%)",
        }
    )

    display_df["고령화율 (%)"] = display_df["고령화율 (%)"].round(2)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

st.caption(
    "고령화율 = (65세 이상 인구 ÷ 전체 인구) × 100. "
    "전체 인구는 '계_'로 시작하는 열만 합산하고 남성·여성 열은 더하지 않습니다."
)
