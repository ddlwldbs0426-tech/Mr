import json
import re

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

# --------------------------------------------------
# 1. 페이지 기본 설정
# --------------------------------------------------
st.set_page_config(
    page_title="전국 고령화 단계구분도",
    page_icon="🗺️",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #FFF9F2;
    }
    h1, h2, h3 {
        color: #6D4938;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🗺️ 전국 고령화 단계구분도")
st.caption(
    "2026년 6월 기준 인구 자료를 이용해 시군구별 65세 이상 인구 비율을 살펴봅니다."
)

# --------------------------------------------------
# 2. 데이터 주소
# --------------------------------------------------
# raw.githubusercontent.com 주소를 사용하면 GitHub 로그인 화면이 아닌
# 실제 파일 내용을 내려받을 수 있습니다.
#
# 참고: 아래 파일 이름이 geojson.txt로 되어 있지만, 요청에 따라
# 압축 CSV 파일로 읽도록 설정했습니다. 실제 파일이 CSV ZIP이 아니라면
# 데이터 주소를 올바른 인구 CSV 파일 주소로 바꿔 주세요.
POPULATION_URL = (
    "https://raw.githubusercontent.com/"
    "ddlwldbs0426-tech/Mr/main/sigungu_kr.geojson.txt"
)

BOUNDARY_URL = (
    "https://raw.githubusercontent.com/"
    "first2022-cyber/contents/main/sigungu_kr.geojson"
)

TARGET_YEAR = 2026

# 65세부터 99세까지 + 100세 이상
ELDERLY_AGES = [f"{age}세" for age in range(65, 100)] + ["100세 이상"]


# --------------------------------------------------
# 3. 코드 형식 통일 함수
# --------------------------------------------------
def normalize_code(value):
    """지역 코드를 문자열로 바꾸고 앞의 5자리를 반환합니다."""
    if pd.isna(value):
        return None

    # CSV에서 코드가 11010.0처럼 읽히는 경우 소수점 부분 제거
    code = str(value).strip()
    if code.endswith(".0"):
        code = code[:-2]

    # 숫자 문자열로 정리한 뒤 5자리보다 짧으면 앞을 0으로 채움
    digits = re.sub(r"\D", "", code)
    if not digits:
        return None

    return digits.zfill(5)[:5]


# --------------------------------------------------
# 4. 인구 CSV 읽기 및 시군구별 고령화율 계산
# --------------------------------------------------
@st.cache_data(show_spinner="2026년 인구 데이터를 불러오는 중입니다...")
def load_population():
    # 사용자가 제공한 파일은 압축 CSV라고 가정하고 ZIP 압축을 지정합니다.
    # URL의 확장자가 .txt여도 compression="zip"이면 ZIP으로 읽습니다.
    population_df = pd.read_csv(
        POPULATION_URL,
        compression="zip",
        dtype={"코드": "string"},
    )

    population_df.columns = (
