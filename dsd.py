import io
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go

# ---------- Page Config ----------
st.set_page_config(
    page_title="월별 매출 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- Sidebar: File Upload ----------
st.sidebar.title("📥 데이터 업로드")
uploaded = st.sidebar.file_uploader(
    "CSV 파일을 업로드하세요 (필수 컬럼: 월, 매출액, 전년동월, 증감률)",
    type=["csv"]
)
st.sidebar.markdown("---")
st.sidebar.caption("• '월'은 YYYY-MM 형식 권장\n• 숫자 컬럼의 쉼표는 자동 제거됩니다.")

# ---------- Helpers ----------
COLUMN_MAP = {
    '월': '월', 'month':'월', 'Month': '월',
    '매출액':'매출액', '매출':'매출액', 'sales':'매출액', 'Sales':'매출액',
    '전년동월':'전년동월', '전년':'전년동월', 'prev':'전년동월', '전년_동월':'전년동월',
    '증감률':'증감률', '증감(%)':'증감률', '성장률':'증감률', 'growth':'증감률'
}

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = {}
    for c in df.columns:
        key = str(c).strip()
        cols[c] = COLUMN_MAP.get(key, key)
    out = df.rename(columns=cols).copy()
    # cast numeric and clean commas
    for col in ['매출액', '전년동월', '증감률']:
        if col in out.columns:
            out[col] = (out[col]
                        .astype(str)
                        .str.replace(',', '', regex=False)
                        .str.replace(' ', '', regex=False)
                        .replace('', np.nan)
                        .astype(float))
    # ensure string month
    if '월' in out.columns:
        out['월'] = out['월'].astype(str).str.strip()
    return out

def require_columns(df: pd.DataFrame):
    must = ['월','매출액','전년동월','증감률']
    missing = [c for c in must if c not in df.columns]
    if missing:
        st.error(f"필수 컬럼이 없습니다: {', '.join(missing)}")
        st.stop()

def make_indicator(total, last_year_total):
    growth = ((total - last_year_total) / last_year_total * 100) if last_year_total else 0.0
    fig = go.Figure(go.Indicator(
        mode="number+delta",
        value=total,
        delta={"reference": last_year_total, "relative": True, "valueformat": ".2%"},
        number={"valueformat": ",.0f"},
        title={"text": f"총 매출액 (원)<br><span style='font-size:0.8em;color:gray'>전년 대비 {growth:.2f}%</span>"}
    ))
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=180)
    return fig

def line_sales(df):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['월'], y=df['매출액'], mode='lines+markers', name='매출액',
        line=dict(width=3), marker=dict(size=7)
    ))
    fig.add_trace(go.Scatter(
        x=df['월'], y=df['전년동월'], mode='lines+markers', name='전년동월',
        line=dict(width=3, dash='dot'), marker=dict(size=6)
    ))
    fig.update_layout(
        title="월별 매출액 추이 (전년 비교)",
        xaxis_title="월", yaxis_title="매출액(원)",
        hovermode="x unified", height=380, margin=dict(t=50, l=60, r=20, b=40)
    )
    fig.update_yaxes(tickformat=",d")
    return fig

def bar_growth(df):
    colors = ['rgba(58,174,216,0.9)' if v >= 0 else 'rgba(225,84,84,0.9)' for v in df['증감률']]
    fig = go.Figure(go.Bar(x=df['월'], y=df['증감률'], marker=dict(color=colors), name="증감률(%)"))
    fig.update_layout(
        title="전년 대비 증감률 추이",
        xaxis_title="월", yaxis_title="증감률(%)",
        shapes=[dict(type='line', x0=-1, x1=len(df['월'])+1, y0=0, y1=0, line=dict(width=1, dash='dot'))],
        height=380, margin=dict(t=50, l=60, r=20, b=40)
    )
    return fig

def hbar_diff(df):
    tmp = df.assign(전년대비_증감액=lambda x: x['매출액'] - x['전년동월']).sort_values('전년대비_증감액', ascending=True)
    top3 = set(tmp.tail(3)['월'])
    bottom3 = set(tmp.head(3)['월'])
    colors = ['rgba(255,176,32,0.95)' if (m in top3 or m in bottom3) else 'rgba(200,210,225,0.7)' for m in tmp['월']]
    fig = go.Figure(go.Bar(
        x=tmp['전년대비_증감액'], y=tmp['월'], orientation='h',
        marker=dict(color=colors),
        hovertemplate='%{y}<br>증감액: %{x:,d}원<extra></extra>'
    ))
    fig.update_layout(
        title="전년 대비 증감액 (상위 3개월 / 하위 3개월 하이라이트)",
        xaxis_title="증감액(원)", yaxis_title="월",
        height=380, margin=dict(t=50, l=70, r=20, b=40)
    )
    fig.update_xaxes(tickformat=",d")
    return fig

# ---------- Load Data ----------
if uploaded is None:
    st.info("좌측 사이드바에서 CSV 파일을 업로드하면 대시보드가 렌더링됩니다.")
    st.stop()

try:
    df = pd.read_csv(uploaded)
except Exception:
    uploaded.seek(0)
    df = pd.read_csv(uploaded, encoding='utf-8-sig')

df = normalize_columns(df)
require_columns(df)

# sort by month lexicographically (YYYY-MM assumed)
df = df.sort_values('월').reset_index(drop=True)

# ---------- KPIs (top row) ----------
total_sales = float(df['매출액'].sum())
last_year_sales = float(df['전년동월'].sum())
avg_sales = float(df['매출액'].mean())
max_idx = int(df['매출액'].idxmax())
min_idx = int(df['매출액'].idxmin())
growth_pct = ((total_sales - last_year_sales) / last_year_sales * 100) if last_year_sales else 0.0

c1,c2,c3,c4 = st.columns(4)
with c1:
    st.metric("총 매출액(원)", f"{total_sales:,.0f}", f"{growth_pct:.2f}%")
with c2:
    st.metric("평균 매출(원)", f"{avg_sales:,.0f}")
with c3:
    st.metric("최고 매출월", f"{df.loc[max_idx, '매출액']:,.0f}", df.loc[max_idx, '월'])
with c4:
    st.metric("최저 매출월", f"{df.loc[min_idx, '매출액']:,.0f}", df.loc[min_idx, '월'])

st.markdown("---")

# ---------- Charts (4 plots) ----------
# 1) KPI Indicator Figure
fig_indicator = make_indicator(total_sales, last_year_sales)
# 2) Sales Trend (YoY compare)
fig_sales = line_sales(df)
# 3) Growth Rate Bars
fig_growth = bar_growth(df)
# 4) YoY Difference Horizontal Bars
fig_diff = hbar_diff(df)

# Layout: 2x2 grid
row1_col1, row1_col2 = st.columns((1.4,1))
with row1_col1:
    st.plotly_chart(fig_sales, use_container_width=True)
with row1_col2:
    st.plotly_chart(fig_indicator, use_container_width=True)

row2_col1, row2_col2 = st.columns(2)
with row2_col1:
    st.plotly_chart(fig_growth, use_container_width=True)
with row2_col2:
    st.plotly_chart(fig_diff, use_container_width=True)

# ---------- Raw Data (optional) ----------
with st.expander("원본 데이터 보기"):
    st.dataframe(df, use_container_width=True)
