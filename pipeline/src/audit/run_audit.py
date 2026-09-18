"""Week 1 data audit for LeaseLens Toronto.

Downloads the current City of Toronto source files into ./raw and prints the
checks recorded in docs/data-audit.md. Run from the repo root:

    pip install -r pipeline/requirements.txt
    python pipeline/src/audit/run_audit.py
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import requests

CKAN = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show"
RAW = Path("raw")

# dataset id -> {local name: resource name on the portal}
SOURCES = {
    "apartment-building-evaluation": {
        "eval_2023": "Apartment Building Evaluations 2023 - current.csv",
        "eval_pre2023": "Pre-2023 Apartment Building Evaluations.csv",
    },
    "apartment-building-registration": {
        "registration": "Apartment Building Registration Data.csv",
    },
    "building-permits-active-permits": {
        "permits_active": "building-permits-active-permits.csv",
    },
    "building-permits-cleared-permits": {
        "permits_cleared": "Cleared Building Permits since 2017.csv",
    },
}


def download() -> dict[str, Path]:
    RAW.mkdir(exist_ok=True)
    paths = {}
    for dataset, files in SOURCES.items():
        meta = requests.get(CKAN, params={"id": dataset}, timeout=60).json()["result"]
        by_name = {r["name"]: r for r in meta["resources"]}
        for local, res_name in files.items():
            path = RAW / f"{local}.csv"
            if not path.exists():
                print(f"downloading {res_name} ...")
                with requests.get(by_name[res_name]["url"], stream=True, timeout=600) as r:
                    r.raise_for_status()
                    with open(path, "wb") as f:
                        for chunk in r.iter_content(1 << 20):
                            f.write(chunk)
            paths[local] = path
        print(f"{dataset}: portal last_refreshed={meta.get('last_refreshed')}")
    return paths


def registration_address_keys(addr: str) -> list[str]:
    """'85-95  THORNCLIFFE PARK DR ' -> ['85|THORNCLIFFE PARK DR', '87|...', ...]"""
    addr = re.sub(r"\s+", " ", str(addr).upper()).strip()
    m = re.match(r"^(\d+)(?:\s*-\s*(\d+))?\s+(.*)$", addr)
    if not m:
        return []
    lo, hi, street = int(m.group(1)), int(m.group(2) or m.group(1)), m.group(3)
    nums = range(lo, hi + 1, 2) if hi - lo <= 40 else [lo, hi]
    return [f"{n}|{street}" for n in nums]


def audit_evaluations(p):
    e23 = pd.read_csv(p["eval_2023"], low_memory=False)
    ep = pd.read_csv(p["eval_pre2023"], low_memory=False)
    print("\n== EVALUATIONS")
    print("2023+ rows", len(e23), "score:", e23["CURRENT BUILDING EVAL SCORE"].describe().round(1).to_dict())
    print("pre   rows", len(ep), "score:", ep["SCORE"].describe().round(1).to_dict())
    d23 = pd.to_datetime(e23["EVALUATION COMPLETED ON"], errors="coerce")
    dp = pd.to_datetime(ep["EVALUATION_COMPLETED_ON"], errors="coerce")
    print("date ranges:", d23.min().date(), "->", d23.max().date(), "|", dp.min().date(), "->", dp.max().date())
    print("duplicate (RSN, date): 2023+", pd.Series(list(zip(e23.RSN, d23))).duplicated().sum(),
          "pre", pd.Series(list(zip(ep.RSN, dp))).duplicated().sum())
    print("RSNs evaluated in both eras:", len(set(e23.RSN) & set(ep.RSN)))
    print("'CREATED IN ERROR' rows:",
          ep.SITE_ADDRESS.str.contains("ERROR", na=False).sum()
          + e23["SITE ADDRESS"].str.contains("ERROR", na=False).sum())
    print("2023+ rows missing lat/lon:", e23.LATITUDE.isna().sum())
    print("reactive score non-zero:", (pd.to_numeric(e23["CURRENT REACTIVE SCORE"], errors="coerce") > 0).sum())
    return e23, ep, d23


def audit_registration(p, e23, ep):
    reg = pd.read_csv(p["registration"], dtype=str)
    print("\n== REGISTRATION")
    print("rows", len(reg), "unique RSN", reg.RSN.nunique())
    ev = set(e23.RSN.astype(str)) | set(ep.RSN.astype(str))
    print("evaluated RSNs missing from registration:", len(ev - set(reg.RSN)))
    print("registered RSNs never evaluated:", len(set(reg.RSN) - ev))
    print("NO_OF_STOREYS null:", reg.NO_OF_STOREYS.isna().sum(), "NO_OF_UNITS null:", reg.NO_OF_UNITS.isna().sum())
    print("property types:", reg.PROPERTY_TYPE.value_counts().to_dict())
    print("range addresses:", reg.SITE_ADDRESS.str.contains(r"^\d+\s*-\s*\d+", na=False).sum())
    return reg


def audit_permits(p, reg):
    cols = ["PERMIT_NUM", "REVISION_NUM", "PERMIT_TYPE", "STREET_NUM", "STREET_NAME",
            "STREET_TYPE", "STREET_DIRECTION", "GEO_ID", "STATUS", "ISSUED_DATE"]
    a = pd.read_csv(p["permits_active"], usecols=cols, dtype=str).assign(src="active")
    c = pd.read_csv(p["permits_cleared"], usecols=cols, dtype=str).assign(src="cleared")
    print("\n== PERMITS")
    for name, df in (("active", a), ("cleared", c)):
        print(f"{name}: rows {len(df)}; REVISION_NUM lengths {df.REVISION_NUM.str.len().value_counts().to_dict()}; "
              f"non-numeric STREET_NUM {(~df.STREET_NUM.fillna('').str.fullmatch(r'\d+')).sum()}; "
              f"GEO_ID missing {df.GEO_ID.isna().sum()}; ISSUED_DATE missing {df.ISSUED_DATE.isna().sum()}")
    permits = pd.concat([a, c])
    rev = permits.REVISION_NUM.str.strip().str.zfill(2)
    k2 = permits.PERMIT_NUM.str.strip() + "|" + rev
    k3 = k2 + "|" + permits.PERMIT_TYPE
    print("dup (permit, rev) within a source:", (k2 + permits.src).duplicated().sum(),
          "| dup incl. PERMIT_TYPE:", (k3 + permits.src).duplicated().sum())
    print("(permit, rev, type) present in BOTH active and cleared:",
          len(set(k3[permits.src == "active"]) & set(k3[permits.src == "cleared"])))

    street = (permits.STREET_NAME.fillna("") + " " + permits.STREET_TYPE.fillna("") + " "
              + permits.STREET_DIRECTION.fillna("")).str.upper().str.replace(r"\s+", " ", regex=True).str.strip()
    pk = set(permits.STREET_NUM.fillna("").str.strip() + "|" + street)
    exact = rng = 0
    for addr in reg.SITE_ADDRESS:
        keys = registration_address_keys(addr)
        if keys and keys[0] in pk:
            exact += 1
        elif any(k in pk for k in keys):
            rng += 1
    print(f"registration -> permit address match: exact {exact}/{len(reg)}, via range expansion {rng}, "
          f"no permit {len(reg) - exact - rng}")


def audit_comparison(e23, d23):
    latest = e23.assign(d=d23).sort_values("d").groupby("RSN").tail(1).reset_index(drop=True)
    u = pd.to_numeric(latest["CONFIRMED UNITS"], errors="coerce")
    s = pd.to_numeric(latest["CONFIRMED STOREYS"], errors="coerce")
    sizes = pd.Series([
        ((latest.WARD == r.WARD) & u.between(u[i] * 0.75, u[i] * 1.25)
         & ((s - s[i]).abs() <= 3) & (latest.RSN != r.RSN)).sum()
        for i, r in latest.iterrows()
    ])
    print("\n== COMPARISON GROUPS (same ward, units +/-25%, storeys +/-3, 2023+ scores)")
    print(sizes.describe().round(1).to_dict(), f"share with <15 peers: {(sizes < 15).mean():.0%}")


if __name__ == "__main__":
    paths = download()
    e23, ep, d23 = audit_evaluations(paths)
    reg = audit_registration(paths, e23, ep)
    audit_permits(paths, reg)
    audit_comparison(e23, d23)
