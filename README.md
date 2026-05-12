# ◈ Sell-Out Monitor & Target Distribution

Dashboard analisis sell-out berbasis Streamlit — port dari Vue dashboard.

## Fitur
- Upload SO Historis + SO Berjalan (Excel/CSV, multi-file)
- Target brand: upload file atau input manual (jika tidak diupload, dihitung otomatis dari rata-rata SO × 115%)
- Dashboard: scorecard, filter brand/cabang/kategori, drill-down dealer → kategori → SKU
- Insight: chart omset per bulan, top dealer, top kategori, top SKU (semua scrollable)
- Normalisasi nama brand otomatis (dedup typo/spasi/casing)

## Deploy ke Streamlit Cloud

1. Push repo ini ke GitHub
2. Buka [streamlit.io/cloud](https://streamlit.io/cloud) → New app
3. Pilih repo ini, branch `main`, file `app.py`
4. Deploy — selesai

## Jalankan lokal

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Struktur file

```
app.py                  ← entry point utama
requirements.txt
.streamlit/
  config.toml           ← dark theme
utils/
  calculations.py       ← logika distribusi target & achievement
  file_reader.py        ← baca & normalisasi Excel/CSV
  brand_cleaner.py      ← dedup nama brand
```

## Format file yang didukung

**SO Historis / Berjalan:**
- Format Lama: kolom `Nama Dept.`, `Keterangan Barang`, `Kuantitas`, `Bulan`, `Tahun`
- Format Baru: kolom `No. Faktur`, `Tgl Faktur`, `No. Barang`, `BRAND Barang`

**Target Brand:**
- Kolom: `brand` | `Target` (dalam Rupiah)
- Contoh: `LOGITECH | 4000000000`
