# 고령화율이 없는(전체 인구 0명) 지역은 지도에서 제외
map_df = population_by_sigungu.dropna(subset=["고령화율"]).copy()

if map_df.empty:
    st.warning("고령화율을 계산할 수 있는 시군구가 없습니다.")
    st.stop()


# --------------------------------------------------
# 8. 요약 지표
# --------------------------------------------------
total_population = int(map_df["전체인구"].sum())
total_elderly = int(map_df["고령인구"].sum())
national_aging_rate = (
    total_elderly / total_population * 100
    if total_population > 0
    else 0
)
highest_row = map_df.loc[map_df["고령화율"].idxmax()]
lowest_row = map_df.loc[map_df["고령화율"].idxmin()]

st.subheader("📌 전국 요약")
card1, card2, card3 = st.columns(3)

card1.metric("전체 인구", f"{total_population:,}명")
card2.metric("65세 이상 인구", f"{total_elderly:,}명")
card3.metric("전국 고령화율", f"{national_aging_rate:.1f}%")

st.caption(
    f"고령화율이 가장 높은 지역: {highest_row['시군구']} "
    f"({highest_row['고령화율']:.1f}%) · "
    f"가장 낮은 지역: {lowest_row['시군구']} "
    f"({lowest_row['고령화율']:.1f}%)"
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
        customdata=map_df[["시군구", "고령화율"]].to_numpy(),
        colorscale=[
            [0.0, "#FFF1DF"],
            [0.25, "#F7C995"],
            [0.50, "#E99A63"],
            [0.75, "#C96645"],
            [1.0, "#873B32"],
        ],
        zmin=0,
        zmax=max(40, float(map_df["고령화율"].max())),
        marker=dict(
            line=dict(color="#FFFFFF", width=0.45),
        ),
        colorbar=dict(
            title=dict(text="고령화율 (%)"),
            ticksuffix="%",
            thickness=18,
            len=0.75,
        ),
        hovertemplate=(
            "시군구: %{customdata[0]}<br>"
            "고령화율: %{customdata[1]:.2f}%"
            "<extra></extra>"
        ),
    )
)

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
    font=dict(family="Arial, sans-serif", color="#5C514A"),
    margin=dict(l=10, r=10, t=65, b=10),
    height=780,
)

st.plotly_chart(fig, use_container_width=True)

st.caption(
    "색이 진할수록 65세 이상 인구 비율이 높습니다. "
    "지도에는 타일 배경을 사용하지 않고 제공된 시군구 GeoJSON 경계를 사용합니다."
)

# --------------------------------------------------
# 10. 시군구별 수치 표
# --------------------------------------------------
with st.expander("시군구별 고령화율 표 보기"):
    display_df = map_df[
        ["시군구코드", "시군구", "전체인구", "고령인구", "고령화율"]
    ].copy()
    display_df = display_df.sort_values("고령화율", ascending=False)
    display_df = display_df.rename(
        columns={
            "시군구코드": "코드",
            "전체인구": "전체 인구",
            "고령인구": "65세 이상 인구",
            "고령화율": "고령화율 (%)",
        }
    )
    display_df["고령화율 (%)"] = display_df["고령화율 (%)"].round(2)
    st.dataframe(display_df, use_container_width=True, hide_index=True)

st.caption(
    "고령화율 = (65세 이상 인구 ÷ 전체 인구) × 100. "
