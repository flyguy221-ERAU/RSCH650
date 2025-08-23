import pandas as pd
import warnings


def parse_flexible_datetime(s: pd.Series, formats: list[str]) -> pd.Series:
    s = s.astype("string").str.strip()
    s_norm = s.str.replace(r"\s+at\s+", " ", regex=True)
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    for fmt in formats:
        mask = out.isna()
        if not mask.any():
            break
        out[mask] = pd.to_datetime(s_norm[mask], format=fmt, errors="coerce")
    mask = out.isna()
    if mask.any():
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Could not infer format")
            out[mask] = pd.to_datetime(s_norm[mask], errors="coerce")
    return out


def normalize_make_model(df: pd.DataFrame) -> pd.DataFrame:
    if "acft_make" in df:
        df["acft_make"] = df["acft_make"].astype("string").str.upper().str.strip()
        repl = {
            r"\bROBINSON HELICOPTER COMPANY\b": "ROBINSON",
            r"\bROBINSON HELICOPTER\b": "ROBINSON",
            r"\bCESSNA AIRCRAFT CO(MPANY)?\b": "CESSNA",
            r"\bPIPER AIRCRAFT( CO(MPANY)?)?\b": "PIPER",
        }
        for pat, sub in repl.items():
            df["acft_make"] = df["acft_make"].str.replace(pat, sub, regex=True)
    if "acft_model" in df:
        df["acft_model"] = df["acft_model"].astype("string").str.upper().str.strip()
    return df


def split_finding_description(desc: pd.Series) -> pd.DataFrame:
    s = desc.astype("string").fillna("")
    parts = s.str.split("/", n=4, expand=True)
    parts = parts.rename(
        columns={
            0: "cat_text",
            1: "subcat_text",
            2: "section_text",
            3: "subsection_text",
            4: "modifier_text",
        }
    )
    for col in [
        "cat_text",
        "subcat_text",
        "section_text",
        "subsection_text",
        "modifier_text",
    ]:
        if col in parts:
            parts[col] = parts[col].fillna("").str.strip()
            parts[col] = parts[col].str.replace(r"\s*-\s*[A-Z]$", "", regex=True)
        else:
            parts[col] = ""
    for k in [
        "cat_text",
        "subcat_text",
        "section_text",
        "subsection_text",
        "modifier_text",
    ]:
        if k not in parts:
            parts[k] = ""
    return parts[["cat_text", "subcat_text", "section_text", "subsection_text", "modifier_text"]]
