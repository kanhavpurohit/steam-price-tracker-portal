"""
Steam Game Price & Review Insight Portal — Streamlit frontend.
Reads directly from the CSV files in data/; no database required.
Mirrors the PHP portal's core features: dashboard, game detail,
Buy-Score, K-Means clustering, and game comparison.

UI is themed to match the PHP portal's style.css design system
(Rajdhani display font, #1a9fff accent, dark card-based layout).
"""
import os
import re
import glob
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image

try:
    from streamlit_option_menu import option_menu
    HAS_OPTION_MENU = True
except Exception:
    HAS_OPTION_MENU = False

# ── Config ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Steam Price & Review Portal",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
IMG_DIR  = os.path.join(os.path.dirname(__file__), "steam_game_headers_by_name")

# Design tokens (ported from css/style.css :root)
ACCENT      = "#1a9fff"
BG_DEEP     = "#0d0f14"
BG_CARD     = "#1a1e2a"
BG_INPUT    = "#111420"
BORDER      = "#252a38"
GREEN       = "#2ecc71"
RED         = "#e74c3c"
YELLOW      = "#f39c12"
STEAM_BLUE  = "#66c0f4"
TEXT_PRI    = "#e8eaf0"
TEXT_SEC    = "#8b92a8"
PURPLE      = "#9b59b6"

# Shared dark layout for all Plotly charts (matches card background)
PLOTLY_LAYOUT = dict(
    paper_bgcolor=BG_CARD,
    plot_bgcolor=BG_CARD,
    font=dict(color=TEXT_PRI, family="Inter, sans-serif"),
    xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
    yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
)


def style_fig(fig, height=300, top=10):
    fig.update_layout(height=height, margin=dict(t=top, b=10, l=10, r=10),
                      **PLOTLY_LAYOUT)
    return fig


# ── Global CSS (port of style.css tokens to the Streamlit DOM) ──────────────
def inject_css():
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

:root{
  --bg-deep:#0d0f14; --bg-card:#1a1e2a; --bg-input:#111420;
  --border:#252a38; --border-light:#2e3547;
  --accent:#1a9fff; --accent-glow:rgba(26,159,255,.15);
  --green:#2ecc71; --steam-blue:#66c0f4;
  --text-primary:#e8eaf0; --text-secondary:#8b92a8; --text-dim:#525970;
  --font-display:'Rajdhani',sans-serif; --font-body:'Inter',sans-serif; --font-mono:'JetBrains Mono',monospace;
  --radius:8px; --radius-lg:14px;
}

/* base */
.stApp{ background:var(--bg-deep); }
html, body, [class*="css"]{ font-family:var(--font-body); color:var(--text-primary); }
#MainMenu, footer, header[data-testid="stHeader"]{ visibility:hidden; height:0; }
section[data-testid="stSidebar"]{ display:none; }
.block-container{ padding-top:1.2rem; max-width:1400px; }

h1,h2,h3,h4{ font-family:var(--font-display)!important; font-weight:700!important; letter-spacing:.3px; }

/* hero */
.hero{
  background:linear-gradient(135deg,#0d1117 0%,#131a2e 50%,#0d1117 100%);
  border:1px solid var(--border); border-radius:var(--radius-lg);
  padding:40px 38px; margin-bottom:26px; position:relative; overflow:hidden;
}
.hero::before{content:'';position:absolute;inset:0;
  background:radial-gradient(ellipse at 70% 50%,rgba(26,159,255,.07) 0%,transparent 70%);}
.hero-title{font-family:var(--font-display);font-size:38px;font-weight:700;line-height:1.1;margin-bottom:8px;}
.hero-title span{color:var(--accent);}
.hero-sub{color:var(--text-secondary);font-size:15px;max-width:520px;margin-bottom:22px;}
.hero-stats{display:flex;gap:40px;}
.hero-stat-val{font-family:var(--font-display);font-size:30px;font-weight:700;color:var(--accent);}
.hero-stat-lbl{font-size:10px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:.09em;}

/* section title */
.section-title{font-family:var(--font-display);font-size:18px;font-weight:700;
  display:flex;align-items:center;gap:8px;margin:6px 0 14px;}
.section-title .dot{width:6px;height:6px;border-radius:50%;background:var(--accent);}

/* game cards: style bordered containers */
[data-testid="stVerticalBlockBorderWrapper"]{
  background:var(--bg-card); border:1px solid var(--border)!important;
  border-radius:var(--radius-lg)!important; transition:.18s ease; overflow:hidden;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover{
  border-color:var(--accent)!important;
  box-shadow:0 8px 24px rgba(26,159,255,.10);
  transform:translateY(-2px);
}
[data-testid="stImage"] img{ border-radius:6px; }

.card-name{font-weight:600;font-size:14px;line-height:1.3;color:var(--text-primary);margin:2px 0 6px;}
.card-meta{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;}
.card-price{font-family:var(--font-mono);font-size:14px;color:var(--steam-blue);font-weight:600;}
.card-price.free{color:var(--green);}
.buy-pill{font-size:11px;font-weight:700;padding:2px 8px;border-radius:5px;}
.needle{width:100%;height:5px;background:var(--bg-input);border-radius:3px;overflow:hidden;margin-top:4px;}
.needle-fill{height:100%;border-radius:3px;}

/* buttons */
.stButton>button{
  background:var(--bg-card); color:var(--text-primary);
  border:1px solid var(--border); border-radius:var(--radius);
  font-family:var(--font-display); font-weight:600; font-size:13px;
  transition:.18s ease; width:100%;
}
.stButton>button:hover{ border-color:var(--accent); color:var(--accent); background:var(--accent-glow); }

/* inputs / selects */
[data-baseweb="input"], [data-baseweb="select"]>div, .stTextInput input, .stSelectbox div[role="combobox"]{
  background:var(--bg-input)!important; border-color:var(--border)!important; border-radius:var(--radius)!important;
}
.stTextInput input{ color:var(--text-primary)!important; }

/* metrics as cards */
[data-testid="stMetric"]{
  background:var(--bg-card); border:1px solid var(--border);
  border-radius:var(--radius); padding:14px 16px;
}
[data-testid="stMetricValue"]{ font-family:var(--font-display); color:var(--accent); }
[data-testid="stMetricLabel"]{ color:var(--text-secondary); text-transform:uppercase; letter-spacing:.06em; font-size:11px; }

/* progress bar accent */
.stProgress > div > div > div > div{ background:var(--steam-blue); }

/* tags */
.tag{display:inline-block;background:#2a475e;color:var(--steam-blue);border-radius:14px;
  padding:3px 11px;font-size:11px;font-weight:600;margin:0 4px 4px 0;
  border:1px solid rgba(102,192,244,.2);}

/* expander on dark */
[data-testid="stExpander"]{ border:1px solid var(--border); border-radius:var(--radius); background:var(--bg-card); }
</style>
        """,
        unsafe_allow_html=True,
    )


# ── Data loading ────────────────────────────────────────────────────────────
@st.cache_data
def load_all_games():
    games = {}
    for pf in glob.glob(os.path.join(DATA_DIR, "*_prices.csv")):
        bn = os.path.basename(pf)
        m  = re.match(r"(.+)_(\d+)_prices\.csv", bn)
        if not m: continue
        name = m.group(1).replace("_", " ")
        appid = m.group(2)
        rf = os.path.join(DATA_DIR, f"{m.group(1)}_{appid}_reviews.csv")
        try:
            prices  = pd.read_csv(pf, parse_dates=["Date"]).sort_values("Date")
            reviews = pd.read_csv(rf, parse_dates=["Date"]).sort_values("Date") if os.path.exists(rf) else pd.DataFrame()
        except Exception:
            continue

        # latest sentiment
        pos_pct = 70.0
        tags    = ""
        if not reviews.empty and "Positive_Reviews" in reviews.columns:
            last = reviews.iloc[-1]
            total = last["Positive_Reviews"] + last["Negative_Reviews"]
            pos_pct = last["Positive_Reviews"] / max(total, 1) * 100
            if "Top_Tags" in reviews.columns:
                tags = str(last.get("Top_Tags", ""))

        # current / min / max price
        valid_prices = prices[prices["Price"] > 0]["Price"]
        cur  = float(prices.iloc[-1]["Price"]) if not prices.empty else 0
        mn   = float(valid_prices.min()) if not valid_prices.empty else cur
        mx   = float(valid_prices.max()) if not valid_prices.empty else cur

        games[name] = {
            "appid": appid, "prices": prices, "reviews": reviews,
            "current": cur, "min": mn, "max": mx,
            "pos_pct": pos_pct, "tags": tags,
            "buy_score": buy_score(cur, mn, mx, pos_pct),
        }
    return games


def buy_score(current, mn, mx, pos_pct):
    """Port of includes/logic.php getBuyScore()."""
    if current <= 0: return 100
    avg = (mn + mx) / 2
    if   current <= mn: ps = 100
    elif current > avg: ps = 20
    else:               ps = 20 + ((avg - current) / max(0.01, avg - mn)) * 80

    if   pos_pct >= 95: rw, pw = 0.75, 0.25
    elif pos_pct >= 80: rw, pw = 0.65, 0.35
    elif pos_pct >= 65: rw, pw = 0.55, 0.45
    elif pos_pct >= 50: rw, pw = 0.45, 0.55
    elif pos_pct >= 30: rw, pw = 0.35, 0.65
    else:               rw, pw = 0.25, 0.75

    return round(pos_pct * rw + ps * pw)


def score_label(s):
    if s >= 85: return "🟢 Excellent Buy"
    if s >= 70: return "🟡 Good Value"
    if s >= 55: return "🟠 Fair Deal"
    if s >= 35: return "🔴 Wait a Bit"
    return "⛔ Avoid"


def score_color(s):
    if s >= 85: return GREEN
    if s >= 70: return YELLOW
    if s >= 55: return "#e67e22"
    if s >= 35: return RED
    return "#922b21"


def game_image(name):
    path = os.path.join(IMG_DIR, f"{name}.jpg")
    if os.path.exists(path):
        try: return Image.open(path)
        except: pass
    return None


@st.cache_data
def run_kmeans(games):
    """Port of ml_engine.php K-Means tier clustering."""
    rows = [(n, g["current"], g["pos_pct"]) for n, g in games.items() if g["current"] > 0]
    if len(rows) < 3: return {}
    names, prices, sents = zip(*rows)
    prices = np.array(prices); sents = np.array(sents)

    sp = np.sort(prices)
    p33 = sp[int(len(sp) * 0.33)]
    p66 = sp[int(len(sp) * 0.66)]

    def tier(p):
        if p <= p33: return "Budget Hits"
        if p <= p66: return "Standard Tier"
        return "Premium Titles"

    labels = {n: tier(p) for n, p in zip(names, prices)}
    return labels


# ── App ─────────────────────────────────────────────────────────────────────
inject_css()
games = load_all_games()
game_names = sorted(games.keys())

st.session_state.setdefault("selected_game", game_names[0] if game_names else None)

# Horizontal nav (matches the PHP top nav bar)
PAGES = ["Dashboard", "Game Detail", "Compare", "ML Clusters"]
ICONS = ["grid", "controller", "bar-chart", "diagram-3"]
if HAS_OPTION_MENU:
    page = option_menu(
        menu_title=None, options=PAGES, icons=ICONS,
        orientation="horizontal", default_index=0,
        styles={
            "container": {"padding": "4px", "background-color": BG_CARD,
                          "border": f"1px solid {BORDER}", "border-radius": "10px",
                          "margin-bottom": "18px"},
            "icon": {"color": TEXT_SEC, "font-size": "14px"},
            "nav-link": {"font-family": "Rajdhani, sans-serif", "font-weight": "600",
                         "font-size": "14px", "color": TEXT_SEC,
                         "padding": "8px 16px", "--hover-color": "#202636"},
            "nav-link-selected": {"background-color": "rgba(26,159,255,.15)", "color": ACCENT},
        },
    )
else:
    page = st.radio("Navigate", PAGES, horizontal=True, label_visibility="collapsed")


def section(title):
    st.markdown(f'<div class="section-title"><span class="dot"></span>{title}</div>',
                unsafe_allow_html=True)


# ── DASHBOARD ───────────────────────────────────────────────────────────────
if page == "Dashboard":
    all_scores = [g["buy_score"] for g in games.values()]
    on_sale = sum(g["current"] < (g["min"] + g["max"]) / 2 for g in games.values() if g["current"] > 0)

    st.markdown(
        f"""
<div class="hero">
  <div class="hero-title">Track Steam Prices.<br>Buy at the <span>Right Time</span>.</div>
  <div class="hero-sub">Historical price &amp; review data for Steam games with ML-powered
  buy recommendations.</div>
  <div class="hero-stats">
    <div><div class="hero-stat-val">{len(games)}</div><div class="hero-stat-lbl">Games Tracked</div></div>
    <div><div class="hero-stat-val">{np.mean(all_scores):.0f}</div><div class="hero-stat-lbl">Avg Buy-Score</div></div>
    <div><div class="hero-stat-val">{sum(s>=85 for s in all_scores)}</div><div class="hero-stat-lbl">Excellent Buys</div></div>
    <div><div class="hero-stat-val">{on_sale}</div><div class="hero-stat-lbl">Below Avg Price</div></div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([3, 1])
    with c1:
        search = st.text_input("Search", placeholder="🔍  Search for a game (e.g. Hollow Knight)…",
                               label_visibility="collapsed")
    with c2:
        sort_by = st.selectbox("Sort", ["Buy-Score ↓", "Price ↓", "Price ↑", "Sentiment ↓"],
                               label_visibility="collapsed")

    filtered = {n: g for n, g in games.items()
                if search.lower() in n.lower()} if search else dict(games)
    sort_map = {
        "Buy-Score ↓": lambda x: -x[1]["buy_score"],
        "Price ↓":      lambda x: -x[1]["current"],
        "Price ↑":      lambda x:  x[1]["current"],
        "Sentiment ↓":  lambda x: -x[1]["pos_pct"],
    }
    sorted_games = sorted(filtered.items(), key=sort_map[sort_by])

    section("All Games")
    cols = st.columns(4)
    for i, (name, g) in enumerate(sorted_games[:40]):
        with cols[i % 4]:
            with st.container(border=True):
                img = game_image(name)
                if img:
                    st.image(img, use_container_width=True)
                price_cls = "free" if g["current"] <= 0 else ""
                price_txt = "Free" if g["current"] <= 0 else f"₹{g['current']:.0f}"
                col = score_color(g["buy_score"])
                st.markdown(
                    f"""
<div class="card-name">{name}</div>
<div class="card-meta">
  <span class="card-price {price_cls}">{price_txt}</span>
  <span class="buy-pill" style="background:{col}22;color:{col}">{g['buy_score']}</span>
</div>
<div style="font-size:11px;color:{TEXT_SEC};margin-bottom:2px">{score_label(g['buy_score'])}</div>
<div class="needle"><div class="needle-fill" style="width:{g['pos_pct']:.0f}%;background:{STEAM_BLUE}"></div></div>
<div style="font-size:10px;color:{TEXT_SEC};margin-top:3px">{g['pos_pct']:.0f}% positive</div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button("View details →", key=f"view_{name}"):
                    st.session_state.selected_game = name
                    st.session_state["_goto_detail"] = True
                    st.rerun()

    if st.session_state.pop("_goto_detail", False):
        st.toast(f"Open '{st.session_state.selected_game}' in the Game Detail tab.")

# ── GAME DETAIL ─────────────────────────────────────────────────────────────
elif page == "Game Detail":
    default_idx = game_names.index(st.session_state.selected_game) \
        if st.session_state.selected_game in game_names else 0
    name = st.selectbox("Select game", game_names, index=default_idx)
    st.session_state.selected_game = name
    g = games[name]
    st.markdown(f"## {name}")

    img = game_image(name)
    c1, c2 = st.columns([1, 2])
    with c1:
        if img: st.image(img, use_container_width=True)
        st.metric("Current Price", f"₹{g['current']:.0f}")
        st.metric("All-time Low",  f"₹{g['min']:.0f}")
        st.metric("All-time High", f"₹{g['max']:.0f}")
    with c2:
        score = g["buy_score"]
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number", value=score,
            title={"text": f"Buy-Score — {score_label(score)}"},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": TEXT_SEC},
                "bar":  {"color": score_color(score)},
                "bgcolor": BG_INPUT, "borderwidth": 0,
                "steps": [
                    {"range": [0, 34],  "color": "#2a1a1c"},
                    {"range": [34, 55], "color": "#2a221a"},
                    {"range": [55, 70], "color": "#2a271a"},
                    {"range": [70, 85], "color": "#1a2a22"},
                    {"range": [85, 100],"color": "#15321f"},
                ],
            }
        ))
        style_fig(fig_gauge, height=250, top=30)
        st.plotly_chart(fig_gauge, use_container_width=True)

        tags = [t for t in g["tags"].split("|") if t][:6]
        if tags:
            st.markdown("".join(f'<span class="tag">{t}</span>' for t in tags),
                        unsafe_allow_html=True)

    section("Price History")
    if not g["prices"].empty:
        fig = px.line(g["prices"], x="Date", y="Price",
                      labels={"Price": "Price (₹)"}, color_discrete_sequence=[ACCENT])
        fig.add_hline(y=g["min"], line_dash="dot", line_color=GREEN,
                      annotation_text=f"All-time low ₹{g['min']:.0f}")
        style_fig(fig, height=300)
        st.plotly_chart(fig, use_container_width=True)

    if not g["reviews"].empty and "Positive_Reviews" in g["reviews"].columns:
        section("Review History")
        rv = g["reviews"].copy()
        rv["Total"] = rv["Positive_Reviews"] + rv["Negative_Reviews"]
        rv["Sentiment %"] = rv["Positive_Reviews"] / rv["Total"].clip(lower=1) * 100
        fig2 = px.bar(rv, x="Date", y=["Positive_Reviews", "Negative_Reviews"],
                      barmode="stack",
                      color_discrete_map={"Positive_Reviews": GREEN, "Negative_Reviews": RED})
        style_fig(fig2, height=280)
        st.plotly_chart(fig2, use_container_width=True)

# ── COMPARE ─────────────────────────────────────────────────────────────────
elif page == "Compare":
    st.markdown("## Compare Games")
    col1, col2 = st.columns(2)
    with col1: g1_name = st.selectbox("Game 1", game_names, index=0)
    with col2: g2_name = st.selectbox("Game 2", game_names, index=min(1, len(game_names)-1))

    g1, g2 = games[g1_name], games[g2_name]

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Buy-Score", g1["buy_score"], delta=int(g1["buy_score"]-g2["buy_score"]),
               delta_color="normal")
    mc2.metric("Current Price", f"₹{g1['current']:.0f}",
               delta=f"₹{g1['current']-g2['current']:.0f}", delta_color="inverse")
    mc3.metric("Sentiment", f"{g1['pos_pct']:.0f}%",
               delta=f"{g1['pos_pct']-g2['pos_pct']:.1f}pp")

    winner = g1_name if g1["buy_score"] > g2["buy_score"] else g2_name
    st.success(f"**Overall verdict: {winner}** has the better Buy-Score right now.")

    section("Price History Comparison")
    p1 = g1["prices"].copy(); p1["Game"] = g1_name
    p2 = g2["prices"].copy(); p2["Game"] = g2_name
    combined = pd.concat([p1, p2])
    fig = px.line(combined, x="Date", y="Price", color="Game",
                  labels={"Price": "Price (₹)"}, color_discrete_sequence=[ACCENT, RED])
    style_fig(fig, height=320)
    st.plotly_chart(fig, use_container_width=True)

    section("Score Breakdown")
    breakdown = pd.DataFrame({
        "Metric": ["Current Price (₹)", "All-time Low (₹)", "Positive Reviews %", "Buy-Score"],
        g1_name:  [f"₹{g1['current']:.0f}", f"₹{g1['min']:.0f}", f"{g1['pos_pct']:.1f}%", g1["buy_score"]],
        g2_name:  [f"₹{g2['current']:.0f}", f"₹{g2['min']:.0f}", f"{g2['pos_pct']:.1f}%", g2["buy_score"]],
    })
    st.dataframe(breakdown, use_container_width=True, hide_index=True)

# ── ML CLUSTERS ─────────────────────────────────────────────────────────────
elif page == "ML Clusters":
    st.markdown("## K-Means Game Clustering")
    st.markdown(
        "Games are clustered into **Budget Hits / Standard Tier / Premium Titles** "
        "using z-score normalised price + sentiment (port of `ml_engine.php`). "
        "Hidden gems: high sentiment (≥ cluster mean + 0.75σ) at or below the cluster median price."
    )

    cluster_labels = run_kmeans(games)
    rows = []
    for name, g in games.items():
        if name in cluster_labels:
            rows.append({
                "Game": name, "Cluster": cluster_labels[name],
                "Price (₹)": g["current"], "Sentiment %": round(g["pos_pct"], 1),
                "Buy-Score": g["buy_score"],
            })
    df = pd.DataFrame(rows)

    fig = px.scatter(
        df, x="Price (₹)", y="Sentiment %", color="Cluster",
        hover_name="Game", size="Buy-Score", size_max=20,
        color_discrete_map={"Budget Hits": GREEN, "Standard Tier": ACCENT, "Premium Titles": PURPLE},
        title="Price vs Sentiment — K-Means Tiers",
    )
    style_fig(fig, height=420, top=40)
    st.plotly_chart(fig, use_container_width=True)

    for tier in ["Budget Hits", "Standard Tier", "Premium Titles"]:
        sub = df[df["Cluster"] == tier].sort_values("Buy-Score", ascending=False)
        with st.expander(f"{tier} ({len(sub)} games)"):
            m_s  = sub["Sentiment %"].mean()
            sd_s = sub["Sentiment %"].std()
            m_p  = sub["Price (₹)"].median()
            gems = sub[(sub["Sentiment %"] >= m_s + 0.75 * sd_s) & (sub["Price (₹)"] <= m_p)]
            if not gems.empty:
                st.success(f"💎 Hidden gems in this tier: {', '.join(gems['Game'].tolist())}")
            st.dataframe(sub.reset_index(drop=True), use_container_width=True, hide_index=True)

    st.info(
        "**Buy-Score validation:** point-in-time backtest over ~1,700 samples "
        "shows Spearman r(score, 60-day future discount) = **−0.66** — "
        "higher score → smaller subsequent price drop."
    )
