#!/usr/bin/env python3
"""Mappa globale degli incidenti: PNG, SVG e pagina HTML, senza rete a runtime.

Esecuzione: conda run -n smt python Mario/mappa_incidenti.py
Dipendenze: matplotlib, numpy, pyproj, shapely. Dati e asset risolti rispetto al file.
Estetica ispirata a Digital Violence; nessuna affiliazione al progetto originale.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib-cache"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon
from matplotlib.lines import Line2D
from pyproj import Transformer
from shapely.geometry import Polygon as GeoPolygon, box
from shapely.affinity import translate

BG, LAND, EDGE = "#030416", "#181c30", "#697086"
WHITE, MUTED, RED, CYAN = "#f6f7ff", "#a5adc5", "#ff315d", "#26ddf3"
PROJECT = Transformer.from_crs("EPSG:4326", "+proj=robin +datum=WGS84", always_xy=True)
PLATFORM_COLORS = {
    "ChatGPT": "#ff315d", "Character.AI": "#26ddf3", "Chai AI": "#ffd166",
    "Meta AI": "#76e39b", "Gemini": "#b69aff", "DeepSeek": "#ff994f",
}


def topology_polygons(path, object_name):
    """Decode quantized TopoJSON arcs, including reversed arcs and multipolygons."""
    data = json.loads(path.read_text())
    sx, sy = data["transform"]["scale"]
    tx, ty = data["transform"]["translate"]
    arcs = []
    for arc in data["arcs"]:
        xy = np.cumsum(np.asarray(arc, dtype=float), axis=0)
        arcs.append(xy * [sx, sy] + [tx, ty])
    result = []
    for geom in data["objects"][object_name]["geometries"]:
        polygons = [geom["arcs"]] if geom["type"] == "Polygon" else geom["arcs"]
        rings = []
        for polygon in polygons:
            # Exterior rings suffice for this small-scale geographic basemap.
            segments = []
            for idx in polygon[0]:
                segment = arcs[idx] if idx >= 0 else arcs[~idx][::-1]
                segments.append(segment if not segments else segment[1:])
            ring = np.concatenate(segments)
            if np.any(np.abs(np.diff(ring[:, 0])) > 180):
                ring[:, 0] = np.degrees(np.unwrap(np.radians(ring[:, 0])))
                polygon = GeoPolygon(ring).buffer(0)
                for offset in (-360, 0, 360):
                    part = polygon.intersection(box(-180 + offset, -90, 180 + offset, 90))
                    if part.is_empty:
                        continue
                    part = translate(part, xoff=-offset)
                    for piece in getattr(part, "geoms", [part]):
                        if piece.geom_type == "Polygon":
                            rings.append(np.asarray(piece.exterior.coords))
            else:
                rings.append(ring)
        result.append({"id": int(geom.get("id", -1)), "name": geom.get("properties", {}).get("name", ""), "rings": rings})
    return result


def representative_point(feature):
    """Centroid of the largest exterior ring; a representative area, not an address."""
    rings = feature["rings"]
    def area(r):
        return np.sum(r[:-1, 0] * r[1:, 1] - r[1:, 0] * r[:-1, 1]) / 2
    r = max(rings, key=lambda ring: abs(area(ring)))
    cross = r[:-1, 0] * r[1:, 1] - r[1:, 0] * r[:-1, 1]
    return tuple(np.sum((r[:-1] + r[1:]) * cross[:, None], axis=0) / (6 * area(r)))


def load_cases(csv_path, world, states):
    cities = json.loads((ROOT / "assets/city_coordinates.json").read_text())
    city_lookup = {(p["city"], p["state"]): (p["lon"], p["lat"]) for p in cities}
    extra = json.loads((ROOT / "assets/global_coordinates.json").read_text())
    state_lookup = {f["name"]: f for f in states}
    country_lookup = {f["id"]: f for f in world}
    cases = []
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            location = row["Location"]
            parts = [x.strip() for x in location.split(",")]
            row["fatalities"] = int(row["Fatalities"] or 0)
            row["survived"] = int(row["Survived-Attempt Victims"] or 0)
            row["coords"] = None
            row["precision"] = "non localizzato"
            row["country"] = ("USA" if "USA" in location else "Canada" if "Canada" in location
                              else "Regno Unito" if "United Kingdom" in location else
                              "Corea del Sud" if "South Korea" in location else "Belgio" if location == "Belgium" else location)
            key = tuple(parts[:2])
            if key in city_lookup:
                row["coords"], row["precision"] = city_lookup[key], "località"
            elif location == "Miami area, Florida, USA":
                row["coords"], row["precision"] = city_lookup[("Miami", "Florida")], "area urbana"
            elif row["country"] == "USA":
                state = parts[-2] if len(parts) > 1 else ""
                if state in state_lookup:
                    row["coords"] = representative_point(state_lookup[state])
                    row["precision"] = "solo Stato"
            elif location in extra:
                row["coords"] = (extra[location]["longitude"], extra[location]["latitude"])
                row["precision"] = "area urbana" if location.startswith("Seoul") else "località"
            elif location == "Belgium":
                row["coords"] = representative_point(country_lookup[56])
                row["precision"] = "solo paese"
            date = row["Date"]
            if len(date) == 4:
                row["start"], row["end"] = datetime(int(date), 1, 1), datetime(int(date), 12, 31)
            elif len(date) == 7:
                year, month = map(int, date.split("-"))
                row["start"], row["end"] = datetime(year, month, 1), datetime(year, month, calendar.monthrange(year, month)[1])
            else:
                row["start"] = row["end"] = datetime.strptime(date, "%Y-%m-%d")
            cases.append(row)
    return cases


def base_map(ax, features, projection, linewidth=.35):
    ax.set_facecolor(BG)
    for feature in features:
        if feature["name"] == "Antarctica":
            continue
        for ring in feature["rings"]:
            x, y = projection.transform(ring[:, 0], ring[:, 1])
            ax.add_patch(Polygon(np.column_stack([x, y]), facecolor=LAND,
                                 edgecolor=EDGE, linewidth=linewidth, alpha=.94, zorder=1))
    ax.set_aspect("equal")
    ax.axis("off")


def number_cases(cases):
    # Partial dates sort by the start of their known interval, never by an invented date.
    fatal = sorted((c for c in cases if c["fatalities"] > 0),
                   key=lambda c: (c["start"], c["ID"]))
    for index, case in enumerate(fatal, 1):
        case["number"] = f"#{index:02d}"
    return fatal


def make_figure(cases, world, output, dpi, by_platform=False):
    plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": WHITE,
                         "svg.fonttype": "none", "savefig.facecolor": BG})
    fig = plt.figure(figsize=(20, 11), facecolor=BG)
    fig.text(.045, .937, "AI / INCIDENT ATLAS", fontsize=29, weight="bold")
    ax = fig.add_axes([.02, .13, .96, .75])
    base_map(ax, world, PROJECT)
    ax.set_xlim(-17400000, 17400000)
    ax.set_ylim(-6300000, 9200000)
    located = [c for c in cases if c["coords"] is not None]
    groups = defaultdict(list)
    for c in located:
        groups[(tuple(c["coords"]), c["Platform"] if by_platform else "all")].append(c)
    for (coords, platform), group in groups.items():
        x,y = PROJECT.transform(*coords)
        color = PLATFORM_COLORS[platform] if by_platform else RED
        size = 28 * sum(c["fatalities"] for c in group)
        for factor, opacity in [(12,.025),(6,.055),(3,.1)]:
            ax.scatter(x,y,s=size*factor,color=color,alpha=opacity,linewidths=0,zorder=4)
        ax.scatter(x,y,s=size,facecolors=color,
                   edgecolors=color,linewidths=1.3,zorder=6)
    if by_platform:
        platforms = [p for p in PLATFORM_COLORS if any(c["Platform"]==p for c in cases)]
        handles = [Line2D([],[],marker="o",color=PLATFORM_COLORS[p],linestyle="none",markersize=6,label=p) for p in platforms]
    else:
        handles = [Line2D([],[],marker="o",color=RED,linestyle="none",markersize=6,label="Incidente con decessi")]
    for deaths in (1,2,9):
        handles.append(Line2D([],[],marker="o",color=MUTED,linestyle="none",
                              markersize=np.sqrt(28*deaths),label=f"{deaths} decess{'o' if deaths==1 else 'i'}"))
    missing=[c for c in cases if c["coords"] is None]
    if missing:
        handles.append(Line2D([],[],color="none",label=f"{sum(c['fatalities'] for c in missing)} decessi · località ignota"))
    fig.legend(handles=handles,loc="lower left",bbox_to_anchor=(.038,.026),frameon=False,
               ncol=6,fontsize=10,labelcolor=WHITE,columnspacing=1.8,labelspacing=1.6)
    output.mkdir(parents=True,exist_ok=True)
    name="mappa_globale_chatbot" if by_platform else "mappa_globale"
    metadata={"Title":"AI / Incident Atlas", "Description":"Fonte: H. Karman, AI Companion Mortality Database, aimortality.org, CC BY 4.0. Localizzazioni indicative; coinvolgimento dei chatbot segnalato, non causalità accertata."}
    fig.savefig(output/f"{name}.png",dpi=dpi,metadata=metadata)
    fig.savefig(output/f"{name}.svg",metadata=metadata)
    plt.close(fig)


def export_audit(cases, output):
    fields=["number","ID","Name","Date","Location","precision","Platform","longitude","latitude","Fatalities"]
    with (output/"localizzazioni.csv").open("w",encoding="utf-8",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader()
        for case in cases:
            row={key:case.get(key,"") for key in fields}
            row["longitude"],row["latitude"]=case["coords"] or ("","")
            writer.writerow(row)
    for name in ("mappa_globale","mappa_globale_chatbot"):
        document = f'''<!doctype html><html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI / Incident Atlas</title>
<style>body{{margin:0;background:#030416}}img{{width:100%;display:block}}</style>
<img src="{name}.svg" alt="Mappa globale degli incidenti con decessi. Tutte le posizioni usano lo stesso simbolo; i decessi senza località sono indicati in legenda."></html>'''
        (output/f"{name}.html").write_text(document,encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=ROOT / "dataset/incidents.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "output")
    parser.add_argument("--dpi", type=int, default=180)
    args = parser.parse_args()
    world = topology_polygons(ROOT / "assets/world-110m.topojson", "countries")
    states = topology_polygons(ROOT / "assets/us-states-10m.topojson", "states")
    cases = load_cases(args.csv, world, states)
    if not cases:
        parser.error("Il CSV non contiene incidenti.")
    cases = number_cases(cases)
    make_figure(cases, world, args.output, args.dpi)
    make_figure(cases, world, args.output, args.dpi, by_platform=True)
    export_audit(cases, args.output)
    print(f"{len(cases)} incidenti; {sum(c['coords'] is not None for c in cases)} localizzati; {sum(c['fatalities'] for c in cases)} decessi")
    print(f"Risultati: {args.output.resolve()}")


if __name__ == "__main__":
    main()
