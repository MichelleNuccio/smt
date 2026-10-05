"""Prepare the supplied census record. Run: conda run -n smt python prepare.py.

Original files are read only. No slider-dependent quantities are computed here.
"""
from pathlib import Path
import json
import math
import hashlib
import pandas as pd
import geopandas as gpd
from pyproj import network

ROOT = Path(__file__).resolve().parent
ORIGINAL = ROOT / "data" / "original"
if not ORIGINAL.exists():
    ORIGINAL = ROOT / "data" / "Original"
OUT = ROOT / "data" / "Processed"
OUT.mkdir(parents=True, exist_ok=True)
network.set_network_enabled(False)  # Installed PROJ resources; preparation stays offline.
counts = {}

def report(step, frame, **notes):
    counts[step] = {"rows": len(frame), **notes}
    print(f"{step}: {len(frame):,} rows; " + "; ".join(f"{k}={v}" for k, v in notes.items()))

# 1. Read the original tree rows, original block polygons, and species equations.
tree_path = ORIGINAL / "2015_street_tree_census" / "2015_Street_Tree_Census_subset_um.csv"
block_path = ORIGINAL / "nycb2010_subset_um" / "nycb2010_um.gpkg"
equation_path = ORIGINAL / "queens_tree_equations.csv"
t = pd.read_csv(tree_path, keep_default_na=False)
b = gpd.read_file(block_path)
e = pd.read_csv(equation_path)
assert t.tree_id.is_unique and b.BCTCB2010.is_unique
report("1a original trees", t, alive=int((t.status == "Alive").sum()),
       dead=int((t.status == "Dead").sum()), stumps=int((t.status == "Stump").sum()))
report("1b original blocks", b, crs=str(b.crs))
report("1c original equations", e, species=int(e.SpCode.nunique()))

# 2. Retain all observed statuses; flag unusable DBH, without imputing a value.
assert set(t.status) <= {"Alive", "Dead", "Stump"}
t["dbh_in"] = pd.to_numeric(t.tree_dbh, errors="coerce")
invalid = (t.status == "Alive") & ((t.dbh_in > 60) | (t.dbh_in <= 0) | t.dbh_in.isna())
t.loc[invalid | (t.status != "Alive"), "dbh_in"] = float("nan")
t.loc[invalid, ["tree_id", "address", "status", "tree_dbh"]].to_csv(OUT / "missing_dbh.csv", index=False)
report("2 diameter validation", t, missing_alive_dbh=int(invalid.sum()), dropped=0)
if invalid.any():
    print(t.loc[invalid, ["tree_id", "address", "tree_dbh"]].to_string(index=False))

# 3. Assign census blocks with strict point-in-polygon, in projected feet (EPSG:2263).
points = gpd.GeoDataFrame(t, geometry=gpd.points_from_xy(t.longitude, t.latitude), crs="EPSG:4326")
points = points.to_crs(b.crs)
assert all(math.isfinite(v) for v in points.total_bounds)
joined = gpd.sjoin(points, b[["BCTCB2010", "geometry"]], how="left", predicate="within")
assert len(joined) == len(t) and not joined.index.duplicated().any()
unmatched = joined.BCTCB2010.isna()
joined.loc[unmatched, ["tree_id", "address", "status", "latitude", "longitude"]].to_csv(OUT / "unmatched_blocks.csv", index=False)
report("3 point-in-polygon", joined, matched=int((~unmatched).sum()), unmatched=int(unmatched.sum()), dropped=0)
print("Unmatched rows by status:", joined.loc[unmatched].status.value_counts().to_dict())

# 4. Apply the species substitutions agreed with the student; retain original species.
species = e[["SpCode", "scientific_name", "common_name"]].drop_duplicates("SpCode")
exact = dict(zip(species.scientific_name, species.SpCode))
aliases = {"Gleditsia triacanthos var. inermis": "GLTR", "Malus": "MA2"}
specific = {"Acer nigrum": "ACSA2", "Acer platanoides 'Crimson King'": "ACPL",
            "Quercus coccinea": "QURU", "Quercus velutina": "QURU", "Quercus falcata": "QURU",
            "Quercus shumardii": "QURU", "Quercus acutissima": "QURU", "Quercus alba": "QUPA",
            "Quercus bicolor": "QUPA", "Quercus macrocarpa": "QUPA", "Quercus robur": "QUPA",
            "Quercus imbricaria": "QUPH", "Tilia americana": "TICO"}
genus = {"Acer": "ACRU", "Aesculus": "AEHI", "Fraxinus": "FRPE", "Prunus": "PRSE2",
         "Pinus": "PIST", "Ulmus": "ULAM", "Tilia": "TICO", "Malus": "MA2"}
def match(name):
    if name in exact:
        return exact[name], "exact species"
    if name in aliases:
        return aliases[name], "same species / genus label"
    if name in specific:
        return specific[name], "agreed genus proxy"
    first = str(name).split()[0] if name else ""
    if first in genus:
        return genus[first], "agreed genus proxy"
    return "GLTR", "honeylocust fallback"
mapping = []
for (latin, common), group in t[t.status == "Alive"].groupby(["spc_latin", "spc_common"]):
    code, method = match(latin)
    mapping.append({"scientific_name": latin, "species": common, "trees": len(group),
                    "equation_code": code, "equation_species": species.set_index("SpCode").loc[code, "common_name"], "method": method})
pd.DataFrame(mapping).to_csv(OUT / "species_mapping.csv", index=False)
report("4 species assignment", joined, original_species=len(mapping), dropped=0)

# 5. Keep only the three equation types used by this model, with original coefficients.
required = {"age_from_dbh", "dbh_from_age", "crown_diameter_from_dbh"}
equations = {}
for row in e[e.predicts.isin(required)].itertuples(index=False):
    equations.setdefault(row.SpCode, {})[row.predicts] = {
        "form": row.form, **{key: (None if pd.isna(getattr(row, key)) else float(getattr(row, key)))
                              for key in ["a", "b", "c", "d", "x_max"]}}
assert all(set(v) == required for v in equations.values())
report("5 relevant equations", e[e.predicts.isin(required)], species=len(equations), unused_equations=int((~e.predicts.isin(required)).sum()))

# 6. Serialize all rows and complete polygon rings; no simplification or sampled trees.
blocks = []
block_index = {}
for row in b.itertuples():
    block_index[row.BCTCB2010] = len(blocks)
    polygons = list(row.geometry.geoms) if row.geometry.geom_type == "MultiPolygon" else [row.geometry]
    rings = [[[round(x, 3), round(y, 3)] for x, y in ring.coords]
             for polygon in polygons for ring in [polygon.exterior, *polygon.interiors]]
    blocks.append({"id": row.BCTCB2010, "rings": rings})
trees = []
for row in joined.itertuples():
    code, method = match(row.spc_latin) if row.status == "Alive" else ("GLTR", "new planting")
    trees.append({"id": int(row.tree_id), "address": row.address, "status": row.status,
                  "species": row.spc_common, "dbh": None if pd.isna(row.dbh_in) else float(row.dbh_in),
                  "block": block_index.get(row.BCTCB2010, -1), "equation": code, "match": method,
                  "lat": float(row.latitude), "lon": float(row.longitude),
                  "x": round(row.geometry.x, 3), "y": round(row.geometry.y, 3)})
payload = {"trees": trees, "blocks": blocks, "equations": equations,
           "equationSpecies": dict(zip(species.SpCode, species.common_name)),
           "bounds": [float(v) for v in b.total_bounds], "crs": str(b.crs), "counts": counts,
           "sources": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in [tree_path, block_path, equation_path]}}
(OUT / "sandbox.json").write_text(json.dumps(payload, separators=(",", ":"), allow_nan=False), encoding="utf-8")
report("6 embedded record", trees, blocks=len(blocks), dropped=0)
(OUT / "preparation_report.json").write_text(json.dumps(counts, indent=2), encoding="utf-8")
print("Saved data/Processed/sandbox.json and audit CSV files. No original was changed.")
