"""Normalisasi nama brand duplikat/typo ke nama canonical."""

BRAND_MAP = {
    "ACER ": "ACER", "Acer": "ACER",
    "ANKER ": "ANKER", "Anker": "ANKER",
    "BRATECK": "BRATECK", "Brateck": "BRATECK", "Brateck ": "BRATECK",
    "DAHUA ": "DAHUA",
    "DEEPCOOL": "DEEPCOOL", "DeepCool": "DEEPCOOL",
    "DarkFlash": "DARKFLASH",
    "EPSON ": "EPSON",
    "FANTECH ": "FANTECH",
    "GAMEN ": "GAMEN",
    "GENIUS": "GENIUS", "Genius": "GENIUS", "Genius ": "GENIUS",
    "GIGABYTE": "GIGABYTE", "Gigabyte": "GIGABYTE",
    "HIKVISION ": "HIKVISION",
    "HP ": "HP",
    "INTEL ": "INTEL",
    "Kassen": "KASSEN",
    "SecureBox ": "SECUREBOX",
    "KINGSTON ": "KINGSTON", "Kingston": "KINGSTON",
    "Lenovo": "LENOVO", "LENOVO ": "LENOVO",
    "LOGITECH ": "LOGITECH", "Logitech": "LOGITECH",
    "MSI ": "MSI",
    "M-TECH": "MTECH",
    "NYK NEMESIS ": "NYK NEMESIS",
    "PANORAMA ": "PANORAMA",
    "PATRIOT ": "PATRIOT", "Patriot": "PATRIOT",
    "Ripjaws": "RIPJAWS", "RIPJAWS": "RIPJAWS",
    "G. Skill Trident": "GSKILL",
    "ROBOT": "ROBOT",
    "SAMSUNG ": "SAMSUNG",
    "SONY ": "SONY", "Sony": "SONY", "ONY": "SONY",
    "Soundcore (Anker)": "SOUNDCORE", "SOUNDCORE (ANKER)": "SOUNDCORE",
    "Tecware": "TECWARE", "TECWARE": "TECWARE",
    "Trindent": "TRIDENT", "TRIDENT": "TRIDENT",
    "TP-LINK": "TPLINK", "TPLink": "TPLINK",
    "UBIQUITI ": "UBIQUITI",
    "UGREEN ": "UGREEN", "Ugreen": "UGREEN", "UGreen": "UGREEN",
    "VENTION ": "VENTION", "Vention": "VENTION",
    "Viewsonic": "VIEWSONIC",
    "XIOMI": "XIAOMI", "Xiaomi": "XIAOMI",
    "ASUSA": "ASUS", "Asus": "ASUS",
    "RUIJI": "RUIJIE",
    "MERCUCYS": "MERCUSYS",
    "WD GREEN": "WD",
    "MasterLiquid": "COOLER MASTER", "MASTERBOX": "COOLER MASTER",
    "(blank)": None, "": None,
}


def clean_brand(raw: str) -> str | None:
    if not raw:
        return None
    s = str(raw).strip()
    if not s or s == "(blank)":
        return None
    if s in BRAND_MAP:
        return BRAND_MAP[s]
    return s.upper()
