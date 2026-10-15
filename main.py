
import re
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------
# 1. 기본 페이지 설정
# --------------------------------------------------
st.set_page_config(
    page_title="동네별 인구 피라미드",
    page_icon="🏘️",
    layout="wide",
)

# 따뜻한 색감과 읽기 쉬운 화면을 위한 CSS
st.markdown(
    """
    <style>
    .stApp {
        background-color: #FFF9F2;
    }
    h1, h2, h3 {
        color: #6D4938;
    }
    div[data-testid="stSelectbox"] label {
        color: #6D4938;
        font-weight: 600;
    }
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #F0DFCF;
        padding: 16px;
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🏘️ 동네별 인구 피라미드")
st.caption(
    "전국 읍·면·동의 연령별 인구를 확인하고 "
    "남녀 인구 구조를 비교해 보세요."
)

# --------------------------------------------------
# 2. 데이터 주소와 연령 목록 설정
# --------------------------------------------------
DATA_URL = (
    "https://raw.githubusercontent.com/"
    "ddlwldbs0426-tech/Mr/main/"
    "population_ts_yearly_gender.zip"
)

# 0세부터 99세까지, 마지막은 100세 이상으로 구성
AGES = [f"{age}세" for age in range(100)] + ["100세 이상"]

# --------------------------------------------------
# 3. ZIP 데이터 불러오기
# --------------------------------------------------
@st.cache_data(show_spinner="전국 인구 데이터를 불러오는 중입니다...")
def load_data():
    # pandas가 URL의 ZIP 파일을 직접 읽도록 설정
    df = pd.read_csv(DATA_URL, compression="zip")

    # 열 이름에 불필요한 공백이 있으면 제거
    df.columns = df.columns.astype(str).str.strip()

    # 연도 열이 문자열로 저장되어 있어도 숫자로 변환
    if "연도" not in df.columns:
        raise ValueError(
            "'연도' 열을 찾을 수 없습니다. "
            "실제 데이터의 열 이름을 확인해 주세요."
        )

    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df = df.dropna(subset=["연도"]).copy()
    df["연도"] = df["연도"].astype(int)

    # 연도별 데이터 중 가장 최신 연도만 선택
    latest_year = int(df["연도"].max())
    df = df[df["연도"] == latest_year].copy()

    # 지역 구분 열이 존재하는지 확인
    location_columns = ["시도", "시군구", "동"]
    missing_locations = [
        col for col in location_columns if col not in df.columns
    ]

    if missing_locations:
        raise ValueError(
            f"지역 열을 찾을 수 없습니다: {missing_locations}"
        )

    # 모든 연령의 남녀 인구 열이 있는지 확인
    age_columns = []
    for age in AGES:
        age_columns.extend([f"남_{age}", f"여_{age}"])

    missing_ages = [col for col in age_columns if col not in df.columns]

    if missing_ages:
        raise ValueError(
            "다음 인구 열을 찾을 수 없습니다: "
            + ", ".join(missing_ages[:10])
            + (" ..." if len(missing_ages) > 10 else "")
        )

    # 인구 열을 숫자로 변환하고 결측값은 0으로 처리
    for col in age_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # 지역 이름을 문자열로 통일
    for col in location_columns:
        df[col] = df[col].fillna("").astype(str).str.strip()

    return df, latest_year


# --------------------------------------------------
# 4. 데이터 불러오기 및 오류 처리
# --------------------------------------------------
try:
    df, latest_year = load_data()
except Exception as e:
    st.error("인구 데이터를 불러오지 못했습니다.")
    st.info(
        "GitHub 파일 주소, ZIP 내부 파일 구조, "
        "열 이름을 확인해 주세요."
    )
    st.exception(e)
    st.stop()

st.success(f"현재 표시 중인 데이터: {latest_year}년")

# --------------------------------------------------
# 5. 시도 → 시군구 → 동 순서로 지역 선택
# --------------------------------------------------
st.subheader("📍 지역 선택")

# 빈 지역명은 선택 목록에서 제외
sido_options = sorted(
    value for value in df["시도"].unique() if value
)

if not sido_options:
    st.warning("선택할 수 있는 시도 데이터가 없습니다.")
    st.stop()

col1, col2, col3 = st.columns(3)

with col1:
    selected_sido = st.selectbox(
        "① 시도",
        sido_options,
        key="sido",
    )

# 선택한 시도에 해당하는 시군구만 표시
sido_df = df[df["시도"] == selected_sido]
sigungu_options = sorted(
    value for value in sido_df["시군구"].unique() if value
)

with col2:
    selected_sigungu = st.selectbox(
        "② 시군구",
        sigungu_options,
        key="sigungu",
    )

# 선택한 시군구에 해당하는 동만 표시
sigungu_df = sido_df[
    sido_df["시군구"] == selected_sigungu
]
dong_options = sorted(
    value for value in sigungu_df["동"].unique() if value
)

with col3:
    selected_dong = st.selectbox(
        "③ 읍·면·동",
        dong_options,
        key="dong",
    )

# 세 가지 선택값이 모두 있어야 그래프를 그림
if not selected_sigungu or not selected_dong:
    st.warning("선택할 수 있는 시군구 또는 동 데이터가 없습니다.")
    st.stop()

# --------------------------------------------------
# 6. 선택한 동네의 인구 데이터 추출
# --------------------------------------------------
selected_df = df[
    (df["시도"] == selected_sido)
    & (df["시군구"] == selected_sigungu)
    & (df["동"] == selected_dong)
]

if selected_df.empty:
    st.warning("선택한 지역의 인구 데이터가 없습니다.")
    st.stop()

# 같은 지역이 여러 행으로 존재하면 연령별 인구를 합산
population = selected_df[
    [f"남_{age}" for age in AGES]
    + [f"여_{age}" for age in AGES]
].sum()

male_values = np.array(
    [population[f"남_{age}"] for age in AGES],
    dtype=float,
)
female_values = np.array(
    [population[f"여_{age}"] for age in AGES],
    dtype=float,
)

# 남성 인구는 음수로 변환해 왼쪽에 표시
male_left = -male_values

total_male = int(male_values.sum())
total_female = int(female_values.sum())
total_population = total_male + total_female

# --------------------------------------------------
# 7. 전체 인구 요약
# --------------------------------------------------
st.subheader(
    f"📊 {selected_sido} {selected_sigungu} {selected_dong}"
)

metric1, metric2, metric3 = st.columns(3)

with metric1:
    st.metric("전체 인구", f"{total_population:,}명")

with metric2:
    st.metric("남성 인구", f"{total_male:,}명")

with metric3:
    st.metric("여성 인구", f"{total_female:,}명")

# --------------------------------------------------
# 8. Plotly 인구 피라미드
# --------------------------------------------------
fig = go.Figure()

# 남성: 음수 값을 사용해 왼쪽으로 표시
fig.add_trace(
    go.Bar(
        y=AGES,
        x=male_left,
        name="남성",
        orientation="h",
        marker_color="#6D91B8",
        customdata=male_values,
        hovertemplate=(
            "나이: %{y}<br>"
            "남성 인구: %{customdata:,.0f}명"
            "<extra></extra>"
        ),
    )
)

# 여성: 양수 값을 사용해 오른쪽으로 표시
fig.add_trace(
    go.Bar(
        y=AGES,
        x=female_values,
        name="여성",
        orientation="h",
        marker_color="#D9959B",
        hovertemplate=(
            "나이: %{y}<br>"
            "여성 인구: %{x:,.0f}명"
            "<extra></extra>"
        ),
    )
)

# 좌우 축 범위를 대칭으로 설정해 비교하기 쉽게 함
max_population = max(
    float(male_values.max()) if len(male_values) else 0,
    float(female_values.max()) if len(female_values) else 0,
    1,
)
axis_limit = max_population * 1.12

fig.update_layout(
    title=dict(
        text=f"{latest_year}년 연령별 인구 피라미드",
        x=0.5,
        xanchor="center",
        font=dict(size=22, color="#6D4938"),
    ),
    barmode="overlay",
    bargap=0.12,
    height=1050,
    paper_bgcolor="#FFF9F2",
    plot_bgcolor="#FFF9F2",
    font=dict(
        family="Arial, sans-serif",
        size=12,
        color="#5C514A",
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="center",
        x=0.5,
    ),
    xaxis=dict(
        title="인구수 (명)",
        range=[-axis_limit, axis_limit],
        tickformat=",d",
        zeroline=True,
        zerolinecolor="#B7A99B",
        zerolinewidth=1.5,
        gridcolor="#EDE2D7",
        tickmode="array",
        tickvals=[
            -axis_limit,
            -axis_limit / 2,
            0,
            axis_limit / 2,
            axis_limit,
        ],
        ticktext=[
            f"{int(axis_limit):,}",
            f"{int(axis_limit / 2):,}",
            "0",
            f"{int(axis_limit / 2):,}",
            f"{int(axis_limit):,}",
        ],
    ),
    yaxis=dict(
        title="나이",
        # 나이 라벨을 0세부터 100세 이상까지 직접 고정
        categoryorder="array",
        categoryarray=AGES,
        # 축 반전 옵션을 사용하지 않음
        # Plotly 범주축은 categoryarray의 마지막 항목이 위에 놓임
        tickmode="array",
        tickvals=AGES,
        ticktext=AGES,
        gridcolor="#F3E9DF",
    ),
    margin=dict(l=90, r=50, t=100, b=70),
)

st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# 9. 나이 축 순서 확인
# --------------------------------------------------
# categoryarray의 마지막 범주가 맨 위에 배치되는 Plotly 특성을 이용해
# 0세가 아래, 100세 이상이 위에 표시되도록 설정했는지 확인
if fig.layout.yaxis.categoryarray is not None:
    axis_order = list(fig.layout.yaxis.categoryarray)
    if axis_order[0] == "0세" and axis_order[-1] == "100세 이상":
        st.caption(
            "나이 축 확인: 맨 아래 0세 · 맨 위 100세 이상"
        )
    else:
        st.warning("나이 축 순서를 다시 확인해 주세요.")

# --------------------------------------------------
# 10. 연령별 인구 표
# --------------------------------------------------
with st.expander("연령별 남녀 인구 표 보기"):
    age_table = pd.DataFrame(
        {
            "나이": AGES,
            "남성 인구": male_values.astype(int),
            "여성 인구": female_values.astype(int),
            "전체 인구": (male_values + female_values).astype(int),
        }
    )
    st.dataframe(
        age_table,
        use_container_width=True,
        hide_index=True,
    )

st.caption(
    "자료: 제공된 전국 읍·면·동 연령별 인구 ZIP 파일. "
    "최신 연도는 데이터에 포함된 연도 중 최댓값으로 자동 선택합니다."
)
