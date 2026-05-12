"""Port dari calculations.js — semua logika inti distribusi target & achievement."""

import re
from collections import defaultdict

BULAN_INDONESIA = {
    1: "JANUARI", 2: "FEBRUARI", 3: "MARET", 4: "APRIL",
    5: "MEI", 6: "JUNI", 7: "JULI", 8: "AGUSTUS",
    9: "SEPTEMBER", 10: "OKTOBER", 11: "NOVEMBER", 12: "DESEMBER",
}
BULAN_ORDER = list(BULAN_INDONESIA.values())
BULAN_REV   = {v: k for k, v in BULAN_INDONESIA.items()}

DEPT_MAP = {
    "B": "B - JKT", "C": "C - PUSAT", "D": "D - SMG",
    "E": "E - JOG", "F": "F - MLG", "G": "G - PROJECT",
    "H": "H - BALI", "X": "X",
}
CITY_MAP = {
    "A - ITC": "Surabaya", "A - RETAIL": "Surabaya",
    "C - PUSAT": "Surabaya", "G - PROJECT": "Surabaya",
    "B - JKT": "Jakarta", "D - SMG": "Semarang",
    "E - JOG": "Jogja", "F - MLG": "Malang", "H - BALI": "Bali",
}


# ── Formatter ─────────────────────────────────────────────────────────────────

def fmt_rupiah(val) -> str:
    if val is None or (isinstance(val, float) and val != val):
        return "Rp 0"
    return "Rp {:,.0f}".format(val).replace(",", ".")


def fmt_persen(val, dec=1) -> str:
    if val is None:
        return "0%"
    return f"{val:.{dec}f}%"


def fmt_short(val) -> str:
    val = val or 0
    if val >= 1e12: return f"Rp {val/1e12:.2f}T"
    if val >= 1e9:  return f"Rp {val/1e9:.1f}M"
    if val >= 1e6:  return f"Rp {val/1e6:.0f}jt"
    if val >= 1e3:  return f"Rp {val/1e3:.0f}rb"
    return f"Rp {val:.0f}"


def parse_rupiah(val) -> float:
    """Smart parser — handle ID/US number format."""
    if isinstance(val, (int, float)):
        return float(val)
    s = re.sub(r"[^0-9,.\-]", "", str(val).strip())
    if not s:
        return 0.0
    if "." in s and "," in s:
        last_dot   = s.rfind(".")
        last_comma = s.rfind(",")
        if last_dot > last_comma:               # US: 1,234.56
            return float(s.replace(",", "")) or 0
        else:                                    # ID: 1.234,56
            return float(s.replace(".", "").replace(",", ".")) or 0
    if "," in s and "." not in s:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            return float(s.replace(",", ".")) or 0
        return float(s.replace(",", "")) or 0
    if "." in s:
        parts = s.split(".")
        if len(parts) > 2:
            return float(s.replace(".", "")) or 0
        if len(parts[1]) <= 2:
            return float(s) or 0
        return float(s.replace(".", "")) or 0
    try:
        return float(s)
    except ValueError:
        return 0.0


# ── Achievement status ────────────────────────────────────────────────────────

def get_achievement_status(pct: float) -> dict:
    if pct >= 115: return {"label": "Melebihi Target", "color": "#c084fc"}
    if pct >= 100: return {"label": "Capai Target",    "color": "#4ade80"}
    if pct >= 80:  return {"label": "Hampir Capai",    "color": "#fbbf24"}
    return              {"label": "Di Bawah Target",   "color": "#f87171"}


def ach_color(pct: float) -> str:
    if pct >= 115: return "#c084fc"
    if pct >= 100: return "#4ade80"
    if pct >= 80:  return "#fbbf24"
    return "#f87171"


# ── Window historis ───────────────────────────────────────────────────────────

def get_12_bulan_historis(target_bulan: int, target_tahun: int) -> list[dict]:
    result = []
    m, y = target_bulan - 1, target_tahun
    for _ in range(12):
        if m < 1:
            m, y = 12, y - 1
        result.insert(0, {"bulan": BULAN_INDONESIA[m], "tahun": y})
        m -= 1
    return result


def get_3_bulan_historis(target_bulan: int, target_tahun: int) -> list[dict]:
    result = []
    m, y = target_bulan - 1, target_tahun
    for _ in range(3):
        if m < 1:
            m, y = 12, y - 1
        result.insert(0, {"bulan": BULAN_INDONESIA[m], "tahun": y})
        m -= 1
    return result


# ── Filter SO historis ────────────────────────────────────────────────────────

def filter_historis(df, target_bulan: int, target_tahun: int):
    """Filter DataFrame ke 12 bulan sebelum target_bulan."""
    import pandas as pd
    window = get_12_bulan_historis(target_bulan, target_tahun)
    keys   = {f"{w['bulan']}-{w['tahun']}" for w in window}
    mask   = (
        df["Bulan"].str.upper().str.strip() + "-" + df["Tahun"].astype(str)
    ).isin(keys)
    return df[mask].copy()


# ── Hitung % kontribusi per dimensi (historis) ────────────────────────────────

def hitung_pct_historis(df, brand: str, group_col: str) -> dict:
    """
    Hitung rata-rata % kontribusi tiap nilai group_col selama 12 bulan
    untuk brand tertentu. Output: {group_value: pct_avg}
    """
    bdf = df[df["BRAND Barang"].str.upper().str.strip() == brand.upper()].copy()
    if bdf.empty:
        return {}

    bdf["_month"] = bdf["Bulan"].str.upper().str.strip() + "-" + bdf["Tahun"].astype(str)

    pct_per_bulan: dict[str, list[float]] = defaultdict(list)

    for month, mdf in bdf.groupby("_month"):
        total = mdf["Jumlah"].sum()
        if total == 0:
            continue
        for grp, gdf in mdf.groupby(group_col):
            grp = str(grp).strip()
            pct_per_bulan[grp].append(gdf["Jumlah"].sum() / total * 100)

    result = {g: sum(p) / len(p) for g, p in pct_per_bulan.items()}

    total_pct = sum(result.values())
    if total_pct > 0:
        result = {g: v / total_pct * 100 for g, v in result.items()}

    return result


def _hitung_pct_rows(df, group_col: str, extra_col: str | None = None) -> dict:
    """Internal: pct dari subset rows yang sudah difilter 1 level."""
    if df.empty:
        return {}

    df = df.copy()
    df["_month"] = df["Bulan"].str.upper().str.strip() + "-" + df["Tahun"].astype(str)

    pct_per_bulan: dict[str, list] = defaultdict(list)
    extras: dict[str, str] = {}

    for _, mdf in df.groupby("_month"):
        total = mdf["Jumlah"].sum()
        if total == 0:
            continue
        for grp, gdf in mdf.groupby(group_col):
            grp = str(grp).strip()
            pct_per_bulan[grp].append(gdf["Jumlah"].sum() / total * 100)
            if extra_col and grp not in extras:
                extras[grp] = str(gdf[extra_col].iloc[0]).strip()

    result = {}
    for g, p in pct_per_bulan.items():
        result[g] = {"pct": sum(p) / len(p), "extra": extras.get(g, "")}

    total_pct = sum(v["pct"] for v in result.values())
    if total_pct > 0:
        for g in result:
            result[g]["pct"] = result[g]["pct"] / total_pct * 100

    return result


# ── Distribusi target 3-level ─────────────────────────────────────────────────

def distribusi_target(historis_df, target_brand: float, brand: str) -> dict:
    """
    Returns nested dict:
    {
      dealer: {
        pct, target,
        kategori: {
          kat: {
            pct, target,
            sku: { no_barang: { pct, target, nama_barang } }
          }
        }
      }
    }
    """
    pct_dealer = hitung_pct_historis(historis_df, brand, "Nama Pelanggan")

    result = {}
    brand_df = historis_df[
        historis_df["BRAND Barang"].str.upper().str.strip() == brand.upper()
    ]

    for dealer, pct in pct_dealer.items():
        target_dealer = pct / 100 * target_brand
        result[dealer] = {"pct": pct, "target": target_dealer, "kategori": {}}

        dealer_df = brand_df[brand_df["Nama Pelanggan"].str.strip() == dealer]
        pct_kat   = _hitung_pct_rows(dealer_df, "Kategori")

        for kat, kat_data in pct_kat.items():
            pct_k        = kat_data["pct"]
            target_kat   = pct_k / 100 * target_dealer
            result[dealer]["kategori"][kat] = {
                "pct": pct_k, "target": target_kat, "sku": {}
            }

            kat_df  = dealer_df[dealer_df["Kategori"].str.strip() == kat]
            pct_sku = _hitung_pct_rows(kat_df, "No. Barang", "Nama Barang")

            for no_brg, sku_data in pct_sku.items():
                target_sku = sku_data["pct"] / 100 * target_kat
                result[dealer]["kategori"][kat]["sku"][no_brg] = {
                    "pct": sku_data["pct"],
                    "target": target_sku,
                    "nama_barang": sku_data["extra"],
                }

    return result


# ── Hitung achievement dari SO berjalan ───────────────────────────────────────

def hitung_achievement(so_berjalan_df, distribusi: dict, brand: str) -> dict:
    """
    Cocokkan realisasi SO berjalan ke distribusi.
    Returns dict dengan struktur mirip distribusi tapi ada realisasi & achievement.
    """
    bdf = so_berjalan_df[
        so_berjalan_df["BRAND Barang"].str.upper().str.strip() == brand.upper()
    ]

    # Agregasi realisasi per dealer → kategori → sku
    real_dealer: dict = defaultdict(lambda: {"total": 0, "kategori": defaultdict(lambda: {"total": 0, "sku": defaultdict(float)})})

    for _, row in bdf.iterrows():
        dealer = str(row.get("Nama Pelanggan", "")).strip()
        kat    = str(row.get("Kategori", "")).strip()
        sku    = str(row.get("No. Barang", "")).strip()
        jml    = float(row.get("Jumlah", 0) or 0)
        real_dealer[dealer]["total"] += jml
        real_dealer[dealer]["kategori"][kat]["total"] += jml
        real_dealer[dealer]["kategori"][kat]["sku"][sku] += jml

    result = {}
    for dealer, info in distribusi.items():
        real  = real_dealer[dealer]["total"]
        pct_a = (real / info["target"] * 100) if info["target"] > 0 else 0
        result[dealer] = {
            "pct": info["pct"],
            "target": info["target"],
            "realisasi": real,
            "achievement": pct_a,
            "status": get_achievement_status(pct_a),
            "kategori": {},
        }

        for kat, kat_info in info["kategori"].items():
            real_k  = real_dealer[dealer]["kategori"][kat]["total"]
            pct_ak  = (real_k / kat_info["target"] * 100) if kat_info["target"] > 0 else 0
            result[dealer]["kategori"][kat] = {
                "pct": kat_info["pct"],
                "target": kat_info["target"],
                "realisasi": real_k,
                "achievement": pct_ak,
                "status": get_achievement_status(pct_ak),
                "sku": {},
            }

            for no_brg, sku_info in kat_info["sku"].items():
                real_s  = real_dealer[dealer]["kategori"][kat]["sku"][no_brg]
                pct_as  = (real_s / sku_info["target"] * 100) if sku_info["target"] > 0 else 0
                result[dealer]["kategori"][kat]["sku"][no_brg] = {
                    "nama_barang": sku_info["nama_barang"],
                    "pct": sku_info["pct"],
                    "target": sku_info["target"],
                    "realisasi": real_s,
                    "achievement": pct_as,
                    "status": get_achievement_status(pct_as),
                }

    return result


# ── Auto-target dari SO berjalan (rata-rata × 115%) ───────────────────────────

def auto_target_dari_so(so_df) -> list[dict]:
    """Hitung target otomatis per brand dari SO Berjalan: avg/bulan × 115%."""
    if so_df is None or so_df.empty:
        return []

    result = []
    for brand, bdf in so_df.groupby("BRAND Barang"):
        brand = str(brand).strip()
        if not brand:
            continue
        bdf = bdf.copy()
        bdf["_month"] = bdf["Bulan"].str.upper().str.strip() + "-" + bdf["Tahun"].astype(str)
        monthly = bdf.groupby("_month")["Jumlah"].sum()
        avg     = monthly.mean() if len(monthly) > 0 else 0
        result.append({
            "brand": brand,
            "avg_bulanan": round(avg),
            "target": round(avg * 1.15),
        })

    return sorted(result, key=lambda x: -x["target"])
