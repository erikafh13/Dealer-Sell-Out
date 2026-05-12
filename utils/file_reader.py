"""Port dari fileReader.js — baca & normalisasi file SO Excel/CSV."""

import re
import io
from datetime import datetime
import pandas as pd

from utils.calculations import parse_rupiah, BULAN_INDONESIA
from utils.brand_cleaner import clean_brand

BULAN_REV = {v: k for k, v in BULAN_INDONESIA.items()}

NAMA_DEPT_MAP = {
    "B": "B - JKT", "C": "C - PUSAT", "D": "D - SMG",
    "E": "E - JOG", "F": "F - MLG", "G": "G - PROJECT",
    "H": "H - BALI",
}
CITY_MAP = {
    "A - ITC": "Surabaya", "A - RETAIL": "Surabaya",
    "C - PUSAT": "Surabaya", "G - PROJECT": "Surabaya",
    "B - JKT": "Jakarta", "D - SMG": "Semarang",
    "E - JOG": "Jogja", "F - MLG": "Malang", "H - BALI": "Bali",
}
DEPT_A_SPECIAL = {"A - CASH", "AIRPAY INTERNATIONAL INDONESIA", "TOKOPEDIA"}


def map_nama_dept(dept: str, pelanggan: str) -> str:
    d = dept.strip().upper()
    if d == "A":
        return "A - ITC" if pelanggan.strip().upper() in DEPT_A_SPECIAL else "A - RETAIL"
    return NAMA_DEPT_MAP.get(d, "X")


def map_city(nama_dept: str) -> str:
    return CITY_MAP.get(nama_dept, "Others")


def _parse_tgl(s: str):
    """Parse tanggal dalam berbagai format ke datetime atau None."""
    if not s:
        return None
    s = str(s).strip()
    # "02 Jan 2025" / "02 JAN 2025"
    m = re.match(r"^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", s)
    if m:
        try:
            return datetime.strptime(f"{m[1]} {m[2]} {m[3]}", "%d %b %Y")
        except ValueError:
            pass
    # "2025-01-02"
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return datetime(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            pass
    # "02/01/2025"
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        try:
            return datetime(int(m[3]), int(m[2]), int(m[1]))
        except ValueError:
            pass
    # Excel serial number
    try:
        n = float(s)
        if n > 40000:
            return datetime(1899, 12, 30) + __import__("datetime").timedelta(days=n)
    except ValueError:
        pass
    return None


def _bulan_tahun_from_tgl(tgl_str: str, bulan_fallback: str, tahun_fallback):
    d = _parse_tgl(tgl_str)
    if d:
        return BULAN_INDONESIA.get(d.month, ""), d.year
    return str(bulan_fallback).upper().strip(), int(tahun_fallback or 0)


def _read_raw(uploaded_file) -> pd.DataFrame:
    """Baca file Excel atau CSV ke DataFrame mentah."""
    name = uploaded_file.name.lower()
    data = uploaded_file.read()
    uploaded_file.seek(0)

    if name.endswith(".csv"):
        try:
            return pd.read_csv(io.BytesIO(data), dtype=str, encoding="utf-8").fillna("")
        except UnicodeDecodeError:
            return pd.read_csv(io.BytesIO(data), dtype=str, encoding="latin-1").fillna("")
    else:
        return pd.read_excel(io.BytesIO(data), dtype=str).fillna("")


def _detect_format(df: pd.DataFrame) -> str:
    cols = [c.strip() for c in df.columns]
    if "No. Faktur" in cols and "Tgl Faktur" in cols and "No. Barang" in cols:
        return "B"
    return "A"


def _normalize_row_A(row: pd.Series) -> dict | None:
    brand     = str(row.get("BRAND Barang", "")).strip()
    pelanggan = str(row.get("Nama Pelanggan", "")).strip()
    if not brand and not pelanggan:
        return None

    tgl_str = str(row.get("Tgl Faktur", "")).strip()
    bulan, tahun = _bulan_tahun_from_tgl(
        tgl_str,
        row.get("Bulan", ""),
        row.get("Tahun", 0),
    )

    dept_str = str(row.get("Dept.", "")).strip()
    nama_dept = str(row.get("Nama Dept.", "")).strip() or map_nama_dept(dept_str, pelanggan)
    city      = str(row.get("City", "")).strip() or map_city(nama_dept)
    brand_clean = clean_brand(brand) or brand.upper()

    return {
        "No. Faktur":   str(row.get("No. Faktur", "")).strip(),
        "Tgl Faktur":   tgl_str,
        "Bulan":        bulan,
        "Tahun":        tahun,
        "Nama Pelanggan": pelanggan,
        "No. Barang":   str(row.get("No. Barang", "")).strip(),
        "BRAND Barang": brand_clean,
        "Kategori":     str(row.get("Nama Kategori Barang Barang", row.get("Kategori", ""))).strip(),
        "Nama Barang":  str(row.get("Keterangan Barang", row.get("Nama Barang", ""))).strip(),
        "Qty":          parse_rupiah(row.get("Kuantitas", row.get("Qty", 0))),
        "Jumlah":       parse_rupiah(row.get("Jumlah", 0)),
        "Sales":        str(row.get("Sales", "")).strip(),
        "Dept.":        dept_str,
        "Nama Dept.":   nama_dept,
        "City":         city,
        "Market Place": str(row.get("Market Place", "")).strip(),
    }


def _normalize_row_B(row: pd.Series) -> dict | None:
    faktur    = str(row.get("No. Faktur", "")).strip()
    pelanggan = str(row.get("Nama Pelanggan", "")).strip()
    if not faktur and not pelanggan:
        return None

    tgl_str = str(row.get("Tgl Faktur", "")).strip()
    bulan, tahun = _bulan_tahun_from_tgl(
        tgl_str,
        row.get("Bulan", ""),
        row.get("Tahun", 0),
    )

    dept_str  = str(row.get("Dept.", "")).strip()
    nama_dept = str(row.get("Nama Dept.", "")).strip() or map_nama_dept(dept_str, pelanggan)
    city      = str(row.get("City", "")).strip() or map_city(nama_dept)
    brand_raw = str(row.get("BRAND Barang", "")).strip()
    brand_clean = clean_brand(brand_raw) or brand_raw.upper()

    return {
        "No. Faktur":   faktur,
        "Tgl Faktur":   tgl_str,
        "Bulan":        bulan,
        "Tahun":        tahun,
        "Nama Pelanggan": pelanggan,
        "No. Barang":   str(row.get("No. Barang", "")).strip(),
        "BRAND Barang": brand_clean,
        "Kategori":     str(row.get("Kategori", "")).strip(),
        "Nama Barang":  str(row.get("Nama Barang", "")).strip(),
        "Qty":          parse_rupiah(row.get("Qty", 0)),
        "Jumlah":       parse_rupiah(row.get("Jumlah", 0)),
        "Sales":        str(row.get("Sales", "")).strip(),
        "Dept.":        dept_str,
        "Nama Dept.":   nama_dept,
        "City":         city,
        "Market Place": str(row.get("Market Place", "")).strip(),
    }


def read_so_files(uploaded_files) -> pd.DataFrame:
    """Baca 1+ file SO (historis atau berjalan), normalisasi, dedup."""
    if not isinstance(uploaded_files, list):
        uploaded_files = [uploaded_files]

    all_rows = []
    for f in uploaded_files:
        raw = _read_raw(f)
        raw.columns = [c.strip() for c in raw.columns]
        fmt    = _detect_format(raw)
        norm   = _normalize_row_B if fmt == "B" else _normalize_row_A
        for _, row in raw.iterrows():
            r = norm(row)
            if r:
                all_rows.append(r)

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    df["Jumlah"] = pd.to_numeric(df["Jumlah"], errors="coerce").fillna(0)
    df["Tahun"]  = pd.to_numeric(df["Tahun"],  errors="coerce").fillna(0).astype(int)
    df["Qty"]    = pd.to_numeric(df["Qty"],    errors="coerce").fillna(0)

    # Dedup
    key_cols = ["No. Faktur", "No. Barang", "Bulan", "Tahun", "Nama Pelanggan", "Jumlah"]
    key_cols = [c for c in key_cols if c in df.columns]
    df = df.drop_duplicates(subset=key_cols)
    return df.reset_index(drop=True)


def read_target_file(uploaded_file) -> list[dict]:
    """Baca file target brand → [{brand, target}]."""
    raw = _read_raw(uploaded_file)
    raw.columns = [c.strip() for c in raw.columns]
    cols_lower  = {c.lower(): c for c in raw.columns}

    brand_col  = cols_lower.get("brand",  raw.columns[0])
    target_col = cols_lower.get("target", raw.columns[1] if len(raw.columns) > 1 else raw.columns[0])

    result = []
    for _, row in raw.iterrows():
        brand  = clean_brand(str(row[brand_col]).strip())
        target = parse_rupiah(row[target_col])
        if brand and target > 0:
            result.append({"brand": brand, "target": target})

    # Dedup (gabung jika brand sama)
    dedup: dict = {}
    for r in result:
        k = r["brand"].upper().strip()
        dedup[k] = dedup.get(k, 0) + r["target"]
    return [{"brand": k, "target": v} for k, v in sorted(dedup.items(), key=lambda x: -x[1])]
