"""
Sell-Out Monitor & Target Distribution
Streamlit version — port dari Vue dashboard
"""

import io
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from utils.calculations import (
    BULAN_INDONESIA, BULAN_ORDER,
    fmt_rupiah, fmt_short, fmt_persen, ach_color,
    get_achievement_status, get_12_bulan_historis, get_3_bulan_historis,
    filter_historis, distribusi_target, hitung_achievement, auto_target_dari_so,
)
from utils.file_reader import read_so_files, read_target_file
from utils.brand_cleaner import clean_brand

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sell-Out Monitor",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Hide default Streamlit header */
#MainMenu, footer, header { visibility: hidden; }

/* Metric cards */
div[data-testid="metric-container"] {
    background: #13161e;
    border: 1px solid #252a38;
    border-radius: 10px;
    padding: 14px 18px;
}
div[data-testid="metric-container"] label { font-size: 11px !important; color: #4a5168 !important; text-transform: uppercase; letter-spacing: .06em; }
div[data-testid="metric-container"] [data-testid="stMetricValue"] { font-size: 20px !important; font-weight: 700; }

/* Dataframe */
.stDataFrame { border: 1px solid #252a38; border-radius: 8px; }

/* Expander */
details summary { font-weight: 600; }

/* Tag badges */
.tag { display:inline-block; padding:2px 10px; border-radius:20px; font-size:11px; font-weight:600; }
.tag-purple { background:rgba(192,132,252,.15); color:#c084fc; }
.tag-green  { background:rgba(74,222,128,.12);  color:#4ade80; }
.tag-yellow { background:rgba(251,191,36,.12);  color:#fbbf24; }
.tag-red    { background:rgba(248,113,113,.12); color:#f87171; }

/* Brand row separator */
.brand-block { border-left: 3px solid #6ee7b7; padding-left: 12px; margin-bottom: 6px; }
</style>
""", unsafe_allow_html=True)


# ── Session state helpers ─────────────────────────────────────────────────────
def ss():
    return st.session_state

def init_state():
    defaults = {
        "so_historis": None,    # pd.DataFrame
        "so_berjalan": None,    # pd.DataFrame
        "data_target": [],      # [{brand, target}]
        "target_bulan": 0,
        "target_tahun": 0,
        "page": "input",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ── Computed helpers (cached per session) ─────────────────────────────────────
@st.cache_data(show_spinner=False)
def get_historis_filtered(_so_hist_json, _so_berj_json, bulan, tahun):
    """Filter gabungan SO ke jendela 12 bulan."""
    frames = []
    if _so_hist_json:
        frames.append(pd.read_json(io.StringIO(_so_hist_json)))
    if _so_berj_json:
        frames.append(pd.read_json(io.StringIO(_so_berj_json)))
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    return filter_historis(combined, bulan, tahun)


def get_effective_target() -> list[dict]:
    if ss().data_target:
        return ss().data_target
    if ss().so_berjalan is not None and not ss().so_berjalan.empty:
        return auto_target_dari_so(ss().so_berjalan)
    return []


def get_brand_summary():
    """Hitung summary semua brand."""
    targets = get_effective_target()
    if not targets or ss().target_bulan == 0:
        return []

    hist_json  = ss().so_historis.to_json() if ss().so_historis is not None else None
    berj_json  = ss().so_berjalan.to_json() if ss().so_berjalan is not None else None
    hist_df    = get_historis_filtered(hist_json, berj_json, ss().target_bulan, ss().target_tahun)
    berj_df    = ss().so_berjalan if ss().so_berjalan is not None else pd.DataFrame()

    result = []
    for t in targets:
        brand  = t["brand"]
        target = t["target"]
        dist   = distribusi_target(hist_df, target, brand)
        ach    = hitung_achievement(berj_df, dist, brand)
        total_real = sum(d["realisasi"] for d in ach.values())
        pct_ach    = (total_real / target * 100) if target > 0 else 0
        result.append({
            "brand": brand,
            "target": target,
            "realisasi": total_real,
            "achievement": pct_ach,
            "status": get_achievement_status(pct_ach),
            "_dist": dist,
            "_ach": ach,
        })

    return sorted(result, key=lambda x: -x["realisasi"])


def data_ready() -> bool:
    return ss().so_berjalan is not None and not ss().so_berjalan.empty and ss().target_bulan > 0


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ◈ SellOut")
    st.caption("Monitor & Target Distribution")
    st.divider()

    pages = {
        "input":     ("⬡", "Input Data"),
        "dashboard": ("◎", "Dashboard"),
        "insight":   ("📊", "Insight"),
    }
    for key, (icon, label) in pages.items():
        disabled = (key != "input") and not data_ready()
        if st.button(
            f"{icon}  {label}",
            key=f"nav_{key}",
            use_container_width=True,
            disabled=disabled,
            type="primary" if ss().page == key else "secondary",
        ):
            ss().page = key
            st.rerun()

    st.divider()
    # Status panel
    berj = ss().so_berjalan
    hist = ss().so_historis
    if berj is not None and not berj.empty:
        st.success(f"✓ SO Berjalan  {len(berj):,} baris")
    else:
        st.caption("○ SO Berjalan belum diupload")

    if hist is not None and not hist.empty:
        st.success(f"✓ SO Historis  {len(hist):,} baris")
    else:
        st.caption("○ SO Historis belum diupload")

    if ss().data_target:
        st.success(f"✓ Target  {len(ss().data_target)} brand")
    else:
        st.caption("○ Target akan dihitung otomatis")

    if ss().target_bulan:
        st.info(f"⊙ Target: {BULAN_INDONESIA[ss().target_bulan]} {ss().target_tahun}")
    else:
        st.caption("○ Bulan target belum diset")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: INPUT DATA
# ══════════════════════════════════════════════════════════════════════════════
if ss().page == "input":
    st.title("Input Data")
    st.caption("Upload data SO dan pilih bulan target sebelum membuka dashboard.")

    col_a, col_b = st.columns(2, gap="large")

    # ── SO Berjalan ───────────────────────────────────────────────────────────
    with col_a:
        st.subheader("01 · Data SO Berjalan *")
        st.caption("Data penjualan bulan berjalan. Bisa multi-file.")
        f_berj = st.file_uploader(
            "Upload SO Berjalan", type=["xlsx", "xls", "csv"],
            accept_multiple_files=True, key="up_berjalan",
            label_visibility="collapsed",
        )
        if f_berj:
            with st.spinner("Membaca file SO Berjalan..."):
                try:
                    df = read_so_files(f_berj)
                    ss().so_berjalan = df
                    st.success(f"✓ {len(df):,} baris dimuat · {df['BRAND Barang'].nunique()} brand")
                except Exception as e:
                    st.error(f"Gagal: {e}")

        if ss().so_berjalan is not None and not ss().so_berjalan.empty:
            st.caption(f"**Brand terdeteksi:** {', '.join(sorted(ss().so_berjalan['BRAND Barang'].unique()))}")

    # ── SO Historis ───────────────────────────────────────────────────────────
    with col_b:
        st.subheader("02 · Data SO Historis")
        st.caption("Data penjualan historis (opsional — dipakai untuk distribusi 12 bulan). Multi-file.")
        f_hist = st.file_uploader(
            "Upload SO Historis", type=["xlsx", "xls", "csv"],
            accept_multiple_files=True, key="up_historis",
            label_visibility="collapsed",
        )
        if f_hist:
            with st.spinner("Membaca file SO Historis..."):
                try:
                    df = read_so_files(f_hist)
                    ss().so_historis = df
                    st.success(f"✓ {len(df):,} baris dimuat")
                except Exception as e:
                    st.error(f"Gagal: {e}")

    st.divider()

    # ── Data Target ───────────────────────────────────────────────────────────
    col_c, col_d = st.columns(2, gap="large")

    with col_c:
        st.subheader("03 · Data Target Brand")
        st.caption("Opsional — jika tidak diupload, target dihitung otomatis dari rata-rata SO × 115%.")
        f_target = st.file_uploader(
            "Upload Target", type=["xlsx", "xls", "csv"],
            key="up_target", label_visibility="collapsed",
        )
        if f_target:
            try:
                targets = read_target_file(f_target)
                ss().data_target = targets
                st.success(f"✓ {len(targets)} brand dimuat")
            except Exception as e:
                st.error(f"Gagal: {e}")

        # Input manual juga
        with st.expander("Input Target Manual"):
            n_brand = st.number_input("Jumlah brand", 1, 50, 3, key="n_manual")
            manual_targets = []
            for i in range(int(n_brand)):
                c1, c2 = st.columns([2, 3])
                with c1:
                    b = st.text_input(f"Brand {i+1}", key=f"mb_{i}")
                with c2:
                    t = st.number_input(f"Target {i+1} (Rp)", 0, None, 0, key=f"mt_{i}", format="%d")
                if b and t > 0:
                    manual_targets.append({"brand": clean_brand(b) or b.upper(), "target": t})
            if st.button("Simpan Target Manual") and manual_targets:
                ss().data_target = manual_targets
                st.success(f"✓ {len(manual_targets)} brand disimpan")

    # ── Bulan Target ──────────────────────────────────────────────────────────
    with col_d:
        st.subheader("04 · Bulan Target *")
        st.caption("Menentukan jendela 12 bulan historis untuk distribusi.")

        b_col, y_col, btn_col = st.columns([2, 1, 1])
        with b_col:
            bulan_names = [BULAN_INDONESIA[i] for i in range(1, 13)]
            sel_bulan   = st.selectbox("Bulan", bulan_names, index=None, placeholder="-- pilih --", key="sel_bulan")
        with y_col:
            sel_tahun = st.number_input("Tahun", 2020, 2030, 2026, key="sel_tahun")
        with btn_col:
            st.write("")
            st.write("")
            if st.button("Set Bulan", use_container_width=True, type="primary"):
                if sel_bulan:
                    num = bulan_names.index(sel_bulan) + 1
                    ss().target_bulan = num
                    ss().target_tahun = int(sel_tahun)
                    st.rerun()

        if ss().target_bulan:
            w = get_12_bulan_historis(ss().target_bulan, ss().target_tahun)
            st.info(f"ⓘ Jendela historis: **{w[0]['bulan']} {w[0]['tahun']}** – **{w[11]['bulan']} {w[11]['tahun']}**")

        # Preview target otomatis
        if ss().target_bulan and ss().so_berjalan is not None:
            targets = get_effective_target()
            if targets:
                st.caption("**Preview target per brand:**")
                preview = pd.DataFrame(targets[:8]).rename(columns={
                    "brand": "Brand", "target": "Target (Rp)", "avg_bulanan": "Avg/Bulan"
                })
                if "Avg/Bulan" in preview.columns:
                    preview["Avg/Bulan"] = preview["Avg/Bulan"].apply(fmt_short)
                preview["Target (Rp)"] = preview["Target (Rp)"].apply(fmt_short)
                st.dataframe(preview, hide_index=True, use_container_width=True)
                if len(targets) > 8:
                    st.caption(f"+ {len(targets)-8} brand lainnya")

    st.divider()

    # CTA
    if data_ready():
        st.success("✅ Data siap! Buka Dashboard untuk analisis.")
        if st.button("Buka Dashboard →", type="primary", use_container_width=False):
            ss().page = "dashboard"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif ss().page == "dashboard":
    if not data_ready():
        st.warning("Upload SO Berjalan dan set bulan target dulu.")
        st.stop()

    st.title("Dashboard Sell-Out")
    w = get_12_bulan_historis(ss().target_bulan, ss().target_tahun)
    st.caption(f"Target {BULAN_INDONESIA[ss().target_bulan]} {ss().target_tahun}  ·  Basis historis: {w[0]['bulan'][:3]} {str(w[0]['tahun'])[2:]} – {w[11]['bulan'][:3]} {str(w[11]['tahun'])[2:]}")

    with st.spinner("Menghitung achievement..."):
        summary = get_brand_summary()

    if not summary:
        st.info("Tidak ada data brand untuk ditampilkan.")
        st.stop()

    # ── Scorecard ─────────────────────────────────────────────────────────────
    total_target    = sum(s["target"]    for s in summary)
    total_real      = sum(s["realisasi"] for s in summary)
    avg_ach         = (total_real / total_target * 100) if total_target > 0 else 0
    brand_capai     = sum(1 for s in summary if s["achievement"] >= 100)
    brand_bawah     = len(summary) - brand_capai

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("Total Brand",      len(summary))
    c2.metric("Total Target",     fmt_short(total_target))
    c3.metric("Total Realisasi",  fmt_short(total_real))
    c4.metric("Achievement Rate", fmt_persen(avg_ach))
    c5.metric("Brand ≥ Target",   brand_capai)
    c6.metric("Brand < Target",   brand_bawah)
    c7.metric("Avg Omset/Brand",  fmt_short(total_real / len(summary) if summary else 0))

    st.divider()

    # ── Filter bar ─────────────────────────────────────────────────────────────
    berj_df = ss().so_berjalan
    all_brands = [s["brand"] for s in summary]

    f1, f2, f3, f4 = st.columns([2, 2, 2, 2])
    with f1:
        search = st.text_input("🔍 Cari brand...", key="dash_search", label_visibility="collapsed", placeholder="Cari brand...")
    with f2:
        sel_brand = st.selectbox("Filter Brand", ["Semua Brand"] + all_brands, key="dash_brand", label_visibility="collapsed")
    with f3:
        cabang_opts = sorted(berj_df["Nama Dept."].dropna().unique().tolist())
        sel_cabang  = st.selectbox("Filter Cabang", ["Semua Cabang"] + cabang_opts, key="dash_cab", label_visibility="collapsed")
    with f4:
        kat_opts   = sorted(berj_df["Kategori"].dropna().unique().tolist())
        sel_kat    = st.selectbox("Filter Kategori", ["Semua Kategori"] + kat_opts, key="dash_kat", label_visibility="collapsed")

    # Apply filters
    filtered = summary
    if sel_brand != "Semua Brand":
        filtered = [s for s in filtered if s["brand"] == sel_brand]
    if search:
        filtered = [s for s in filtered if search.upper() in s["brand"]]

    filt_real = sum(s["realisasi"] for s in filtered)
    filt_ach  = (filt_real / sum(s["target"] for s in filtered) * 100) if filtered and sum(s["target"] for s in filtered) > 0 else 0
    st.caption(f"{len(filtered)} brand · {fmt_short(filt_real)} realisasi · {fmt_persen(filt_ach)} ach")

    st.divider()

    # ── Brand list ────────────────────────────────────────────────────────────
    for idx, s in enumerate(filtered):
        brand = s["brand"]
        color = ach_color(s["achievement"])
        status_lbl = s["status"]["label"]

        with st.expander(
            f"**#{idx+1}  {brand}**  —  {fmt_short(s['realisasi'])}  ·  "
            f":{'violet' if s['achievement']>=115 else 'green' if s['achievement']>=100 else 'orange' if s['achievement']>=80 else 'red'}[{fmt_persen(s['achievement'])}]  ·  {status_lbl}",
            expanded=False,
        ):
            m1, m2, m3 = st.columns(3)
            m1.metric("Target",      fmt_rupiah(s["target"]))
            m2.metric("Realisasi",   fmt_rupiah(s["realisasi"]))
            m3.metric("Achievement", fmt_persen(s["achievement"]))

            # Progress bar
            bar_val = min(s["achievement"] / 100, 2.0)
            st.progress(min(bar_val, 1.0))

            # Dealer table
            ach_data = s["_ach"]
            if ach_data:
                st.caption("**Per Dealer:**")
                dealer_rows = []
                for dealer, dinfo in sorted(ach_data.items(), key=lambda x: -x[1]["realisasi"]):
                    dealer_rows.append({
                        "Dealer":      dealer,
                        "% Hist":      fmt_persen(dinfo["pct"]),
                        "Target":      fmt_rupiah(dinfo["target"]),
                        "Realisasi":   fmt_rupiah(dinfo["realisasi"]),
                        "Achievement": fmt_persen(dinfo["achievement"]),
                        "Status":      dinfo["status"]["label"],
                    })
                st.dataframe(
                    pd.DataFrame(dealer_rows),
                    hide_index=True, use_container_width=True,
                    column_config={
                        "Achievement": st.column_config.TextColumn("Achievement"),
                    }
                )

                # Kategori & SKU drill-down per dealer
                for dealer, dinfo in sorted(ach_data.items(), key=lambda x: -x[1]["realisasi"]):
                    if dinfo["kategori"]:
                        with st.expander(f"↳ {dealer} — per Kategori & SKU", expanded=False):
                            for kat, kinfo in sorted(dinfo["kategori"].items(), key=lambda x: -x[1]["realisasi"]):
                                st.markdown(f"**{kat or '(tanpa kategori)'}** — {fmt_rupiah(kinfo['realisasi'])} / {fmt_rupiah(kinfo['target'])} ({fmt_persen(kinfo['achievement'])})")
                                if kinfo["sku"]:
                                    sku_rows = []
                                    for no_brg, sinfo in sorted(kinfo["sku"].items(), key=lambda x: -x[1]["realisasi"]):
                                        sku_rows.append({
                                            "No. Barang":  no_brg,
                                            "Nama Barang": sinfo["nama_barang"],
                                            "Target":      fmt_rupiah(sinfo["target"]),
                                            "Realisasi":   fmt_rupiah(sinfo["realisasi"]),
                                            "Ach %":       fmt_persen(sinfo["achievement"]),
                                        })
                                    st.dataframe(pd.DataFrame(sku_rows), hide_index=True, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: INSIGHT
# ══════════════════════════════════════════════════════════════════════════════
elif ss().page == "insight":
    if not data_ready():
        st.warning("Upload SO Berjalan dan set bulan target dulu.")
        st.stop()

    berj_df = ss().so_berjalan
    hist_df = ss().so_historis

    st.title("Brand Insight")
    w = get_12_bulan_historis(ss().target_bulan, ss().target_tahun)
    window_lbl = f"{w[0]['bulan'][:3]} {str(w[0]['tahun'])[2:]} – {w[11]['bulan'][:3]} {str(w[11]['tahun'])[2:]}"
    st.caption(f"Rata-rata penjualan bulanan per brand · basis historis {window_lbl}")

    # Gunakan gabungan historis + berjalan untuk insight
    source_dfs = [df for df in [hist_df, berj_df] if df is not None and not df.empty]
    source_df  = pd.concat(source_dfs, ignore_index=True) if source_dfs else pd.DataFrame()

    if source_df.empty:
        st.info("Tidak ada data SO untuk dianalisis.")
        st.stop()

    # Filter controls
    f1, f2, f3 = st.columns([3, 2, 2])
    with f1:
        search_insight = st.text_input("🔍 Cari brand...", key="ins_search", label_visibility="collapsed", placeholder="Cari brand...")
    with f2:
        cab_opts = sorted(source_df["Nama Dept."].dropna().unique().tolist())
        sel_cab  = st.selectbox("Cabang", ["Semua"] + cab_opts, key="ins_cab", label_visibility="collapsed")
    with f3:
        kat_opts = sorted(source_df["Kategori"].dropna().unique().tolist())
        sel_kat  = st.selectbox("Kategori", ["Semua"] + kat_opts, key="ins_kat", label_visibility="collapsed")

    # Apply filters
    src = source_df.copy()
    if sel_cab != "Semua":
        src = src[src["Nama Dept."] == sel_cab]
    if sel_kat != "Semua":
        src = src[src["Kategori"] == sel_kat]

    # Hitung stats per brand
    src["_month"] = src["Bulan"].str.upper().str.strip() + " " + src["Tahun"].astype(str)
    brands_list   = sorted(src["BRAND Barang"].dropna().unique().tolist())

    if search_insight:
        brands_list = [b for b in brands_list if search_insight.upper() in b.upper()]

    # Sort by avg monthly desc
    def brand_avg(brand):
        bdf    = src[src["BRAND Barang"] == brand]
        monthly = bdf.groupby("_month")["Jumlah"].sum()
        return monthly.mean() if len(monthly) > 0 else 0

    brands_sorted = sorted(brands_list, key=brand_avg, reverse=True)

    st.markdown(f"**{len(brands_sorted)} brand** ditemukan")
    st.divider()

    # ── Per brand ─────────────────────────────────────────────────────────────
    MONTH_ORDER_MAP = {v: i for i, v in enumerate(BULAN_ORDER)}

    for brand in brands_sorted:
        bdf = src[src["BRAND Barang"] == brand].copy()
        if bdf.empty:
            continue

        monthly    = bdf.groupby("_month")["Jumlah"].sum().reset_index()
        monthly.columns = ["Bulan-Tahun", "Jumlah"]

        # Sort bulan kronologis
        def sort_key(bt):
            parts = str(bt).split()
            if len(parts) == 2:
                bname, yr = parts
                return int(yr) * 100 + MONTH_ORDER_MAP.get(bname.upper(), 0)
            return 0
        monthly = monthly.sort_values("Bulan-Tahun", key=lambda s: s.apply(sort_key))

        total      = bdf["Jumlah"].sum()
        bulan_aktif = monthly["Jumlah"].gt(0).sum()
        avg_bln    = monthly["Jumlah"].mean() if bulan_aktif > 0 else 0
        auto_tgt   = round(avg_bln * 1.15)

        with st.expander(
            f"**{brand}**  ·  Avg {fmt_short(avg_bln)}/bln  ·  Total {fmt_short(total)}  ·  {bulan_aktif} bulan aktif",
            expanded=False,
        ):
            # ── Chart bar ─────────────────────────────────────────────────────
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=monthly["Bulan-Tahun"],
                y=monthly["Jumlah"],
                marker_color="#6ee7b7",
                marker_opacity=0.85,
                hovertemplate="%{x}<br>Rp %{y:,.0f}<extra></extra>",
            ))
            fig.update_layout(
                title=f"Penjualan Per Bulan — {brand}",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e8eaf0", size=11),
                height=260,
                margin=dict(t=40, b=40, l=0, r=0),
                xaxis=dict(gridcolor="#252a38", tickfont=dict(size=10)),
                yaxis=dict(gridcolor="#252a38", tickformat=",.0f"),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            # Saran target
            st.info(f"💡 Saran target awal: **{fmt_rupiah(auto_tgt)}**/bulan  (avg {bulan_aktif} bulan aktif dalam {window_lbl})")

            # ── Breakdown grid ─────────────────────────────────────────────────
            col_d, col_k, col_s = st.columns(3)

            # Top Dealer (semua, scrollable via dataframe)
            with col_d:
                st.caption("**TOP DEALER**")
                dealers = (
                    bdf.groupby("Nama Pelanggan")["Jumlah"].sum()
                    .sort_values(ascending=False)
                    .reset_index()
                )
                dealers["% Share"] = (dealers["Jumlah"] / total * 100).round(1)
                dealers["Jumlah"]  = dealers["Jumlah"].apply(fmt_short)
                dealers.columns    = ["Dealer", "Omset", "% Share"]
                st.dataframe(dealers, hide_index=True, use_container_width=True, height=280)

            # Per Kategori
            with col_k:
                st.caption("**PER KATEGORI**")
                kats = (
                    bdf.groupby("Kategori")["Jumlah"].sum()
                    .sort_values(ascending=False)
                    .reset_index()
                )
                kats["% Share"] = (kats["Jumlah"] / total * 100).round(1)
                kats["Jumlah"]  = kats["Jumlah"].apply(fmt_short)
                kats.columns    = ["Kategori", "Omset", "% Share"]
                st.dataframe(kats, hide_index=True, use_container_width=True, height=280)

            # Top SKU
            with col_s:
                st.caption("**TOP SKU**")
                skus = (
                    bdf.groupby(["No. Barang", "Nama Barang"])["Jumlah"].sum()
                    .sort_values(ascending=False)
                    .reset_index()
                )
                skus["% Share"] = (skus["Jumlah"] / total * 100).round(1)
                skus["Jumlah"]  = skus["Jumlah"].apply(fmt_short)
                skus.columns    = ["No. Barang", "Nama Barang", "Omset", "% Share"]
                st.dataframe(skus, hide_index=True, use_container_width=True, height=280)
