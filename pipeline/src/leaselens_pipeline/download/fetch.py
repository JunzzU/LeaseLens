"""Download City of Toronto source files and keep an untouched, versioned copy.

Layout: raw/<source>/<YYYY-MM-DD>/source.csv plus meta.json describing where the
file came from. A file already downloaded today is reused, so reruns are cheap.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import requests

CKAN = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show"


@dataclass(frozen=True)
class Source:
    key: str          # our name, used for the raw/ folder and data_imports.dataset_name
    package: str      # CKAN dataset id
    resource: str     # resource name on the portal


SOURCES = {
    s.key: s
    for s in [
        Source("registration", "apartment-building-registration", "Apartment Building Registration Data.csv"),
        Source("evaluations_v2023", "apartment-building-evaluation", "Apartment Building Evaluations 2023 - current.csv"),
        Source("evaluations_pre2023", "apartment-building-evaluation", "Pre-2023 Apartment Building Evaluations.csv"),
    ]
}


@dataclass(frozen=True)
class RawFile:
    source: Source
    path: Path
    sha256: str
    source_version: str   # portal last_modified of the resource
    url: str


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(source: Source, raw_dir: Path) -> RawFile:
    folder = raw_dir / source.key / date.today().isoformat()
    path, meta_path = folder / "source.csv", folder / "meta.json"

    if not path.exists():
        meta = requests.get(CKAN, params={"id": source.package}, timeout=60).json()["result"]
        res = next(r for r in meta["resources"] if r["name"] == source.resource)
        folder.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".part")
        with requests.get(res["url"], stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
        tmp.rename(path)
        meta_path.write_text(json.dumps({
            "package": source.package,
            "resource": source.resource,
            "url": res["url"],
            "last_modified": res.get("last_modified"),
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "sha256": sha256_of(path),
        }, indent=2))

    meta = json.loads(meta_path.read_text())
    return RawFile(source, path, meta["sha256"], meta["last_modified"] or "", meta["url"])
