# UrbanAccessApp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a new standalone React+FastAPI web app (`UrbanAccessApp`) with three accessibility analysis modes — Transit (GTFS, default), Schools, and Parks.

**Architecture:** FastAPI backend with three independent analysis modules (schools/parks/gtfs) and a shared utils module. React+Vite+TypeScript frontend with a mode toggle on the landing page and mode-specific parameter controls in the analysis page. All three modes share the same result shape (`{aoi, pois, hexagons, edges, stats}`) and the same map/stats components.

**Tech Stack:** Python 3.12+, FastAPI, uvicorn, UrbanAccessAnalyzer (from GitHub), pyGTFSHandler (local, to be added), React 19, Vite 7, TypeScript 5.9, Tailwind CSS 4, react-leaflet 5, uv

---

## File Map

New repo at `/home/xabi9/Documents/Sources/UrbanAccessApp/`

```
UrbanAccessApp/
├── pyproject.toml
├── .gitignore
├── backend/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app, job queue, all endpoints
│   ├── utils.py                 # geocode, gdf_to_geojson, sanitize_filename
│   ├── analysis_schools.py      # Schools pipeline (port from Accessibility_tool_rural)
│   ├── analysis_parks.py        # Parks pipeline (new)
│   └── analysis_gtfs.py         # GTFS pipeline (pyGTFSHandler-guarded)
├── tests/
│   ├── __init__.py
│   ├── test_utils.py            # Unit tests for pure backend functions
│   └── test_api.py              # FastAPI integration tests
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── tsconfig.app.json
    ├── tsconfig.node.json
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── App.css
        ├── index.css
        ├── types.ts
        ├── api.ts
        └── components/
            ├── ErrorBoundary.tsx
            ├── LandingPage.tsx       # Mode toggle (default: Transit) + AOI input
            ├── AnalysisPage.tsx      # Mode-aware shell: polling, map, stats, controls
            ├── CityMap.tsx           # Map with LOS grade + accessibility band colors
            ├── StatsPanel.tsx        # Population per accessibility band or LOS grade
            ├── SchoolsControls.tsx   # Walk/bike/car sliders + kids toggle
            ├── ParksControls.tsx     # Walking distance slider
            └── GtfsControls.tsx      # Hour range + GTFS feed checkbox list
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `/home/xabi9/Documents/Sources/UrbanAccessApp/pyproject.toml`
- Create: `/home/xabi9/Documents/Sources/UrbanAccessApp/.gitignore`
- Create: `/home/xabi9/Documents/Sources/UrbanAccessApp/backend/__init__.py`
- Create: `/home/xabi9/Documents/Sources/UrbanAccessApp/tests/__init__.py`

- [ ] **Step 1: Create the project directory and initialise git**

```bash
mkdir -p /home/xabi9/Documents/Sources/UrbanAccessApp
cd /home/xabi9/Documents/Sources/UrbanAccessApp
git init
```

Expected: `Initialized empty Git repository in .../UrbanAccessApp/.git/`

- [ ] **Step 2: Write pyproject.toml**

```toml
[project]
name = "urban-access-app"
version = "0.1.0"
description = "Multi-mode urban accessibility web app (Transit, Schools, Parks)"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.129.2",
    "geopandas>=1.1.2",
    "numpy>=2.0.0",
    "osmnx>=2.1.0",
    "shapely>=2.1.2",
    "uvicorn>=0.41.0",
    "urbanaccessanalyzer[h3,osm,plot]",
    "pytest>=8.0.0",
    "httpx>=0.27.0",
]

[tool.uv.sources]
urbanaccessanalyzer = { git = "https://github.com/CityScope/UrbanAccessAnalyzer.git", rev = "v1.0.0" }
```

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/pyproject.toml`

- [ ] **Step 3: Write .gitignore**

```
__pycache__/
*.py[cod]
.venv/
*.egg-info/
output/
cache/
*.graphml
*.gpkg
*.tif
*.osm
.env
node_modules/
dist/
frontend/dist/
```

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/.gitignore`

- [ ] **Step 4: Create package init files and tests directory**

```bash
mkdir -p /home/xabi9/Documents/Sources/UrbanAccessApp/backend
mkdir -p /home/xabi9/Documents/Sources/UrbanAccessApp/tests
touch /home/xabi9/Documents/Sources/UrbanAccessApp/backend/__init__.py
touch /home/xabi9/Documents/Sources/UrbanAccessApp/tests/__init__.py
```

- [ ] **Step 5: Install dependencies**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
uv sync
```

Expected: uv creates `.venv/` and installs all packages.

- [ ] **Step 6: Commit scaffold**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
git add .
git commit -m "chore: initial project scaffold"
```

---

## Task 2: Backend Utils Module

**Files:**
- Create: `backend/utils.py`
- Create: `tests/test_utils.py`

- [ ] **Step 1: Write the failing tests**

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/tests/test_utils.py`:

```python
"""Tests for backend/utils.py pure functions."""
import json
import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon
from backend.utils import sanitize_filename, gdf_to_geojson


def test_sanitize_filename_basic():
    assert sanitize_filename("New York, USA") == "new_york__usa"


def test_sanitize_filename_accents():
    assert sanitize_filename("Bilbão") == "bilbao"


def test_sanitize_filename_spaces():
    result = sanitize_filename("São Paulo")
    assert " " not in result
    assert result == "sao_paulo"


def test_gdf_to_geojson_returns_feature_collection():
    gdf = gpd.GeoDataFrame(
        {"name": ["test"], "value": [42.0]},
        geometry=[Point(0, 0)],
        crs="EPSG:4326",
    )
    result = gdf_to_geojson(gdf)
    assert result["type"] == "FeatureCollection"
    assert len(result["features"]) == 1
    assert result["features"][0]["properties"]["name"] == "test"


def test_gdf_to_geojson_handles_nan():
    gdf = gpd.GeoDataFrame(
        {"value": [np.nan]},
        geometry=[Point(0, 0)],
        crs="EPSG:4326",
    )
    result = gdf_to_geojson(gdf)
    # Should not raise; nan becomes serialisable string or float
    assert json.dumps(result)  # no serialisation error


def test_gdf_to_geojson_handles_polygon():
    poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    gdf = gpd.GeoDataFrame({"accessibility": ["walk"]}, geometry=[poly], crs="EPSG:4326")
    result = gdf_to_geojson(gdf)
    assert result["features"][0]["geometry"]["type"] == "Polygon"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
uv run pytest tests/test_utils.py -v
```

Expected: `ImportError: cannot import name 'sanitize_filename' from 'backend.utils'`

- [ ] **Step 3: Write backend/utils.py**

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/backend/utils.py`:

```python
"""Shared utilities: geocoding, GeoDataFrame serialisation, filename sanitisation."""
import json
import re
import unicodedata

import geopandas as gpd
import numpy as np
import requests
from shapely.geometry import Point


def sanitize_filename(name: str) -> str:
    """Lowercase, strip accents, replace non-alphanumeric chars with underscore."""
    text = str(name).lower().strip()
    text = "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", text)


def geocode(q: str, results: int = 1, buffer: float = 0) -> gpd.GeoDataFrame | None:
    """Geocode a query string via Nominatim. Returns a GeoDataFrame or None."""
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": q, "format": "json", "limit": results},
            headers={"User-Agent": "urban-access-app/1.0"},
            timeout=8,
        )
        data = r.json()
        if not data:
            return None
        records = [
            {
                "query": q,
                "display_name": item["display_name"],
                "lat": float(item["lat"]),
                "lon": float(item["lon"]),
                "geometry": Point(float(item["lon"]), float(item["lat"])),
            }
            for item in data
        ]
        gdf = gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:4326")
        if buffer > 0:
            orig_crs = gdf.crs
            gdf = gdf.to_crs(gdf.estimate_utm_crs())
            gdf.geometry = gdf.geometry.buffer(buffer)
            gdf = gdf.to_crs(orig_crs)
        return gdf
    except Exception as e:
        print(f"Geocode error: {e}")
        return None


def gdf_to_geojson(gdf: gpd.GeoDataFrame) -> dict:
    """Convert a GeoDataFrame to a JSON-serialisable GeoJSON dict."""
    gdf = gdf.copy()
    for col in gdf.columns:
        if col == "geometry":
            continue
        if gdf[col].dtype == "object":
            gdf[col] = gdf[col].astype(str)
        elif np.issubdtype(gdf[col].dtype, np.integer):
            gdf[col] = gdf[col].astype(int)
        elif np.issubdtype(gdf[col].dtype, np.floating):
            gdf[col] = gdf[col].where(gdf[col].notna(), other=None)
        else:
            gdf[col] = gdf[col].astype(str)
    return json.loads(gdf.to_json())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
uv run pytest tests/test_utils.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
git add backend/utils.py tests/test_utils.py
git commit -m "feat: add backend utils (geocode, gdf_to_geojson, sanitize_filename)"
```

---

## Task 3: Schools Analysis Module

**Files:**
- Create: `backend/analysis_schools.py`

This is a direct port of `Accessibility_tool_rural/backend/analysis.py`, adapted to use `backend.utils` and renamed to `run_schools_analysis`.

- [ ] **Step 1: Write backend/analysis_schools.py**

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/backend/analysis_schools.py`:

```python
"""Schools accessibility pipeline. Port of Accessibility_tool_rural/backend/analysis.py."""
import os
import zipfile
from typing import Optional

import geopandas as gpd
import osmnx as ox
import pandas as pd
from shapely.geometry import mapping

import UrbanAccessAnalyzer.graph_processing as graph_processing
import UrbanAccessAnalyzer.h3_utils as h3_utils
import UrbanAccessAnalyzer.isochrones as isochrones
import UrbanAccessAnalyzer.osm as osm
import UrbanAccessAnalyzer.population as population
import UrbanAccessAnalyzer.utils as uaa_utils

from backend.utils import geocode, gdf_to_geojson, sanitize_filename

RESULTS_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "output"))
MIN_EDGE_LENGTH = 30
H3_RESOLUTION = 10


def _prepare_paths(aoi_key: str):
    city_filename = sanitize_filename(aoi_key)
    city_results_path = os.path.join(RESULTS_PATH, city_filename)
    os.makedirs(city_results_path, exist_ok=True)
    return city_results_path, {
        "poi": os.path.join(city_results_path, "schools.gpkg"),
        "osm_xml": os.path.join(city_results_path, "streets.osm"),
        "graph": os.path.join(city_results_path, "streets.graphml"),
        "streets": os.path.join(city_results_path, "streets.gpkg"),
        "los_streets": os.path.join(city_results_path, "level_of_service_streets.gpkg"),
        "population": os.path.join(city_results_path, "population.gpkg"),
        "pop_raster_ref": os.path.join(city_results_path, ".population_raster_path"),
    }


def _download_population_raster(aoi_download, kids_only: bool) -> str:
    if kids_only:
        pop_file = population.download_worldpop_population(
            aoi_download, 2025, folder=RESULTS_PATH, resolution="100m",
            dataset="age_structures", subset="U18",
        )
    else:
        pop_file = population.download_worldpop_population(
            aoi_download, 2025, folder=RESULTS_PATH, resolution="100m",
        )
    if ".zip" in pop_file:
        extract_dir = os.path.splitext(pop_file)[0]
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(pop_file, "r") as zip_ref:
            zip_ref.extractall(extract_dir)
        for file_name in os.listdir(extract_dir):
            if file_name.lower().endswith(".tif") and "_T_" in file_name:
                return os.path.join(extract_dir, file_name)
    return pop_file


def run_schools_analysis(
    city_name: Optional[str] = None,
    address: Optional[str] = None,
    buffer_m: float = 0,
    distance_steps: list[int] = None,
    accessibility_values: list[str] = None,
    kids_only: bool = False,
    progress_callback=None,
) -> dict:
    """Run schools accessibility pipeline. Returns GeoJSON-serialisable dict."""
    if distance_steps is None:
        distance_steps = [1000, 2500, 10000]
    if accessibility_values is None:
        accessibility_values = ["walk", "bike", "bus/car"]

    def _progress(msg: str):
        if progress_callback:
            progress_callback(msg)

    if not city_name and not address:
        raise ValueError("Provide either city_name or address")

    aoi_key = city_name if city_name else f"{address} r={int(round(buffer_m))}m"
    city_results_path, paths = _prepare_paths(aoi_key)
    os.makedirs(RESULTS_PATH, exist_ok=True)

    # 1. AOI
    if city_name:
        _progress("Fetching city geometry...")
        aoi_raw = uaa_utils.get_city_geometry(city_name)
        aoi = gpd.GeoDataFrame(geometry=[aoi_raw.union_all()], crs=aoi_raw.crs)
        aoi = aoi.to_crs(aoi.estimate_utm_crs())
    else:
        _progress("Geocoding address...")
        gdf = geocode(address, results=1, buffer=buffer_m)
        if gdf is None or gdf.empty:
            raise ValueError(f"Could not geocode: {address}")
        aoi = gpd.GeoDataFrame(geometry=[gdf.union_all()], crs=gdf.crs)
        aoi = aoi.to_crs(aoi.estimate_utm_crs())

    aoi_download = aoi.buffer(0)

    # 2. POIs (schools)
    if os.path.exists(paths["poi"]):
        _progress("Loading cached schools...")
        poi = gpd.read_file(paths["poi"]).to_crs(aoi.crs)
    else:
        _progress("Fetching schools from OSM...")
        query = """
        [out:xml] [timeout:25];
        (
            node["amenity"="school"]( {{bbox}});
            way["amenity"="school"]( {{bbox}});
            relation["amenity"="school"]( {{bbox}});
        );
        (._;>;);
        out body;
        """
        poi = osm.overpass_api_query(query, aoi_download)
        poi.geometry = poi.geometry.centroid
        poi = poi.to_crs(aoi.crs)
        poi.to_file(paths["poi"])
    poi = poi[poi.geometry.intersects(aoi_download.union_all())]

    # 3. Street network
    if os.path.exists(paths["graph"]):
        _progress("Loading cached street graph...")
        G = ox.load_graphml(paths["graph"])
    else:
        _progress("Downloading street network...")
        network_filter = osm.osmium_network_filter("walk+bike+primary")
        osm.geofabrik_to_osm(
            paths["osm_xml"],
            input_file=RESULTS_PATH,
            aoi=aoi_download,
            osmium_filter_args=network_filter,
            overwrite=False,
        )
        _progress("Building street graph...")
        G = ox.graph_from_xml(paths["osm_xml"])
        G = ox.project_graph(G, to_crs=aoi.estimate_utm_crs())
        _progress("Simplifying graph...")
        G = graph_processing.simplify_graph(
            G,
            min_edge_length=MIN_EDGE_LENGTH,
            min_edge_separation=MIN_EDGE_LENGTH * 2,
            undirected=True,
        )
        ox.save_graphml(G, paths["graph"])
        street_edges = ox.graph_to_gdfs(G, nodes=False).to_crs(aoi.crs)
        street_edges.to_file(paths["streets"])

    # 4. Add POIs to graph
    _progress("Adding schools to graph...")
    G, osmids = graph_processing.add_points_to_graph(
        poi, G, max_dist=100 + MIN_EDGE_LENGTH, min_edge_length=MIN_EDGE_LENGTH
    )
    poi["osmid"] = osmids

    # 5. Isochrones
    _progress("Computing isochrones...")
    accessibility_graph = isochrones.graph(
        G, poi, distance_steps,
        poi_quality_col=None,
        accessibility_values=accessibility_values,
        min_edge_length=MIN_EDGE_LENGTH,
    )
    _, accessibility_edges = ox.graph_to_gdfs(accessibility_graph)
    accessibility_edges.to_file(paths["los_streets"])

    # 6. H3
    _progress("Converting to H3 hexagons...")
    access_h3_df = h3_utils.from_gdf(
        accessibility_edges,
        resolution=H3_RESOLUTION,
        columns=["accessibility"],
        value_order=accessibility_values,
        contain="overlap",
        method="min",
        buffer=10,
    )

    # 7. Population
    pop_raster_ref = paths["pop_raster_ref"]
    population_file = None
    if os.path.exists(pop_raster_ref):
        with open(pop_raster_ref) as f:
            cached_path = f.read().strip()
        if os.path.exists(cached_path):
            _progress("Using cached population raster...")
            population_file = cached_path

    if population_file is None:
        _progress("Downloading population data...")
        population_file = _download_population_raster(aoi_download, kids_only)
        with open(pop_raster_ref, "w") as f:
            f.write(population_file)

    _progress("Processing population grid...")
    try:
        pop_h3_df = h3_utils.from_raster(population_file, aoi=aoi_download, resolution=H3_RESOLUTION)
    except Exception:
        _progress("Population file corrupted, re-downloading...")
        if os.path.exists(population_file):
            os.remove(population_file)
        population_file = _download_population_raster(aoi_download, kids_only)
        with open(pop_raster_ref, "w") as f:
            f.write(population_file)
        pop_h3_df = h3_utils.from_raster(population_file, aoi=aoi_download, resolution=H3_RESOLUTION)
    pop_h3_df = pop_h3_df.rename(columns={"value": "population"})

    # 8. Merge + stats
    _progress("Merging accessibility and population data...")
    results_h3_df = access_h3_df.merge(pop_h3_df, left_index=True, right_index=True, how="outer")
    results_h3_df = h3_utils.to_gdf(results_h3_df).to_crs(aoi.crs)
    results_h3_df = results_h3_df[results_h3_df.intersects(aoi.union_all())]
    results_h3_df.to_file(paths["population"])

    stats_df = results_h3_df.groupby("accessibility", as_index=False)["population"].sum()
    total_population = stats_df["population"].sum()
    stats_df = pd.concat(
        [stats_df, pd.DataFrame([{"accessibility": "total population", "population": total_population}])],
        ignore_index=True,
    )
    stats_df["population_pct"] = (stats_df["population"] * 100 / total_population).round(2)
    stats_df["population"] = stats_df["population"].round(0).astype(int)

    _progress("Building response...")
    return {
        "aoi": gdf_to_geojson(aoi.to_crs("EPSG:4326")),
        "pois": gdf_to_geojson(poi.to_crs("EPSG:4326")),
        "hexagons": gdf_to_geojson(results_h3_df.to_crs("EPSG:4326")),
        "edges": gdf_to_geojson(accessibility_edges.to_crs("EPSG:4326")),
        "stats": stats_df.to_dict(orient="records"),
    }
```

- [ ] **Step 2: Verify import works**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
uv run python -c "from backend.analysis_schools import run_schools_analysis; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
git add backend/analysis_schools.py
git commit -m "feat: add schools analysis pipeline"
```

---

## Task 4: Parks Analysis Module

**Files:**
- Create: `backend/analysis_parks.py`

- [ ] **Step 1: Write backend/analysis_parks.py**

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/backend/analysis_parks.py`:

```python
"""Parks accessibility pipeline. Uses osm.green_areas + poi_utils.polygons_to_points."""
import os
import zipfile
from typing import Optional

import geopandas as gpd
import osmnx as ox
import pandas as pd

import UrbanAccessAnalyzer.graph_processing as graph_processing
import UrbanAccessAnalyzer.h3_utils as h3_utils
import UrbanAccessAnalyzer.isochrones as isochrones
import UrbanAccessAnalyzer.osm as osm
import UrbanAccessAnalyzer.poi_utils as poi_utils
import UrbanAccessAnalyzer.population as population
import UrbanAccessAnalyzer.utils as uaa_utils

from backend.utils import geocode, gdf_to_geojson, sanitize_filename

RESULTS_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "output"))
MIN_EDGE_LENGTH = 30
H3_RESOLUTION = 10
ACCESSIBILITY_VALUES = ["walk"]


def _prepare_paths(aoi_key: str):
    city_filename = sanitize_filename(aoi_key)
    city_results_path = os.path.join(RESULTS_PATH, city_filename + "_parks")
    os.makedirs(city_results_path, exist_ok=True)
    return city_results_path, {
        "poi": os.path.join(city_results_path, "parks.gpkg"),
        "osm_xml": os.path.join(city_results_path, "streets.osm"),
        "graph": os.path.join(city_results_path, "streets.graphml"),
        "streets": os.path.join(city_results_path, "streets.gpkg"),
        "los_streets": os.path.join(city_results_path, "level_of_service_streets.gpkg"),
        "population": os.path.join(city_results_path, "population.gpkg"),
        "pop_raster_ref": os.path.join(city_results_path, ".population_raster_path"),
    }


def run_parks_analysis(
    city_name: Optional[str] = None,
    address: Optional[str] = None,
    buffer_m: float = 0,
    distance_walk: int = 500,
    progress_callback=None,
) -> dict:
    """Run parks accessibility pipeline. Returns GeoJSON-serialisable dict."""

    def _progress(msg: str):
        if progress_callback:
            progress_callback(msg)

    if not city_name and not address:
        raise ValueError("Provide either city_name or address")

    aoi_key = city_name if city_name else f"{address} r={int(round(buffer_m))}m"
    city_results_path, paths = _prepare_paths(aoi_key)
    os.makedirs(RESULTS_PATH, exist_ok=True)

    # 1. AOI
    if city_name:
        _progress("Fetching city geometry...")
        aoi_raw = uaa_utils.get_city_geometry(city_name)
        aoi = gpd.GeoDataFrame(geometry=[aoi_raw.union_all()], crs=aoi_raw.crs)
        aoi = aoi.to_crs(aoi.estimate_utm_crs())
    else:
        _progress("Geocoding address...")
        gdf = geocode(address, results=1, buffer=buffer_m)
        if gdf is None or gdf.empty:
            raise ValueError(f"Could not geocode: {address}")
        aoi = gpd.GeoDataFrame(geometry=[gdf.union_all()], crs=gdf.crs)
        aoi = aoi.to_crs(aoi.estimate_utm_crs())

    aoi_download = aoi.buffer(0)

    # 2. Street network (needed before park entry points)
    if os.path.exists(paths["graph"]):
        _progress("Loading cached street graph...")
        G = ox.load_graphml(paths["graph"])
    else:
        _progress("Downloading street network...")
        network_filter = osm.osmium_network_filter("walk+bike+primary")
        osm.geofabrik_to_osm(
            paths["osm_xml"],
            input_file=RESULTS_PATH,
            aoi=aoi_download,
            osmium_filter_args=network_filter,
            overwrite=False,
        )
        _progress("Building street graph...")
        G = ox.graph_from_xml(paths["osm_xml"])
        G = ox.project_graph(G, to_crs=aoi.estimate_utm_crs())
        _progress("Simplifying graph...")
        G = graph_processing.simplify_graph(
            G,
            min_edge_length=MIN_EDGE_LENGTH,
            min_edge_separation=MIN_EDGE_LENGTH * 2,
            undirected=True,
        )
        ox.save_graphml(G, paths["graph"])

    street_edges = ox.graph_to_gdfs(G, nodes=False).to_crs(aoi.crs)

    # 3. POIs (parks as entry points)
    if os.path.exists(paths["poi"]):
        _progress("Loading cached park entry points...")
        poi = gpd.read_file(paths["poi"]).to_crs(aoi.crs)
    else:
        _progress("Fetching parks from OSM...")
        parks_gdf = osm.green_areas(aoi_download)
        if parks_gdf.empty:
            raise ValueError("No parks found in this area.")
        parks_gdf = parks_gdf.to_crs(aoi.crs)
        _progress("Computing park entry points...")
        poi = poi_utils.polygons_to_points(parks_gdf, street_edges)
        poi = poi[poi.geometry.intersects(aoi_download.union_all())]
        if poi.empty:
            raise ValueError("No park entry points intersect the street network.")
        poi.to_file(paths["poi"])

    poi = poi[poi.geometry.intersects(aoi_download.union_all())]

    # 4. Add POIs to graph
    _progress("Adding park entry points to graph...")
    G, osmids = graph_processing.add_points_to_graph(
        poi, G, max_dist=100 + MIN_EDGE_LENGTH, min_edge_length=MIN_EDGE_LENGTH
    )
    poi["osmid"] = osmids

    # 5. Isochrones
    _progress("Computing isochrones...")
    accessibility_graph = isochrones.graph(
        G, poi, [distance_walk],
        poi_quality_col=None,
        accessibility_values=ACCESSIBILITY_VALUES,
        min_edge_length=MIN_EDGE_LENGTH,
    )
    _, accessibility_edges = ox.graph_to_gdfs(accessibility_graph)
    accessibility_edges.to_file(paths["los_streets"])

    # 6. H3
    _progress("Converting to H3 hexagons...")
    access_h3_df = h3_utils.from_gdf(
        accessibility_edges,
        resolution=H3_RESOLUTION,
        columns=["accessibility"],
        value_order=ACCESSIBILITY_VALUES,
        contain="overlap",
        method="min",
        buffer=10,
    )

    # 7. Population
    pop_raster_ref = paths["pop_raster_ref"]
    population_file = None
    if os.path.exists(pop_raster_ref):
        with open(pop_raster_ref) as f:
            cached_path = f.read().strip()
        if os.path.exists(cached_path):
            _progress("Using cached population raster...")
            population_file = cached_path

    if population_file is None:
        _progress("Downloading population data...")
        population_file = population.download_worldpop_population(
            aoi_download, 2025, folder=RESULTS_PATH, resolution="100m"
        )
        if ".zip" in population_file:
            extract_dir = os.path.splitext(population_file)[0]
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(population_file, "r") as zip_ref:
                zip_ref.extractall(extract_dir)
            for file_name in os.listdir(extract_dir):
                if file_name.lower().endswith(".tif") and "_T_" in file_name:
                    population_file = os.path.join(extract_dir, file_name)
                    break
        with open(pop_raster_ref, "w") as f:
            f.write(population_file)

    _progress("Processing population grid...")
    pop_h3_df = h3_utils.from_raster(population_file, aoi=aoi_download, resolution=H3_RESOLUTION)
    pop_h3_df = pop_h3_df.rename(columns={"value": "population"})

    # 8. Merge + stats
    _progress("Merging accessibility and population data...")
    results_h3_df = access_h3_df.merge(pop_h3_df, left_index=True, right_index=True, how="outer")
    results_h3_df = h3_utils.to_gdf(results_h3_df).to_crs(aoi.crs)
    results_h3_df = results_h3_df[results_h3_df.intersects(aoi.union_all())]
    results_h3_df.to_file(paths["population"])

    stats_df = results_h3_df.groupby("accessibility", as_index=False)["population"].sum()
    total_population = stats_df["population"].sum()
    stats_df = pd.concat(
        [stats_df, pd.DataFrame([{"accessibility": "total population", "population": total_population}])],
        ignore_index=True,
    )
    stats_df["population_pct"] = (stats_df["population"] * 100 / total_population).round(2)
    stats_df["population"] = stats_df["population"].round(0).astype(int)

    _progress("Building response...")
    return {
        "aoi": gdf_to_geojson(aoi.to_crs("EPSG:4326")),
        "pois": gdf_to_geojson(poi.to_crs("EPSG:4326")),
        "hexagons": gdf_to_geojson(results_h3_df.to_crs("EPSG:4326")),
        "edges": gdf_to_geojson(accessibility_edges.to_crs("EPSG:4326")),
        "stats": stats_df.to_dict(orient="records"),
    }
```

- [ ] **Step 2: Verify import works**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
uv run python -c "from backend.analysis_parks import run_parks_analysis; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
git add backend/analysis_parks.py
git commit -m "feat: add parks analysis pipeline"
```

---

## Task 5: GTFS Analysis Module (pyGTFSHandler-guarded)

**Files:**
- Create: `backend/analysis_gtfs.py`

This module guards all `pyGTFSHandler` imports. When the library is added, the stubs become live code.
`MOBILITY_DB_TOKEN` must be set as an environment variable.

- [ ] **Step 1: Write backend/analysis_gtfs.py**

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/backend/analysis_gtfs.py`:

```python
"""
GTFS Transit LOS pipeline.

Requires:
  - pyGTFSHandler (local package, add to pyproject.toml when available)
  - MOBILITY_DB_TOKEN environment variable (Mobility Database refresh token)

When pyGTFSHandler is not installed, all public functions raise RuntimeError.
"""
import os
import zipfile
from datetime import date, datetime, time, timedelta
from typing import Optional

import geopandas as gpd
import osmnx as ox
import pandas as pd

import UrbanAccessAnalyzer.h3_utils as h3_utils
import UrbanAccessAnalyzer.isochrones as isochrones
import UrbanAccessAnalyzer.population as population
import UrbanAccessAnalyzer.utils as uaa_utils

from backend.utils import geocode, gdf_to_geojson, sanitize_filename

try:
    from pyGTFSHandler.feed import Feed
    from pyGTFSHandler.downloaders.mobility_database import MobilityDatabaseClient
    from pyGTFSHandler.downloaders.mobility_database import (
        get_geographic_suggestions_from_string,
    )
    import pyGTFSHandler.processing_helper as processing_helper

    PYGTFS_AVAILABLE = True
except ImportError:
    PYGTFS_AVAILABLE = False

RESULTS_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "output"))
GTFS_PATH = os.path.join(RESULTS_PATH, "gtfs_files")
H3_RESOLUTION = 10

# LOS grades used in the analysis (A1 is best, F is worst)
LOS_GRADES = ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3", "D", "E", "F"]


def _require_pygtfs():
    if not PYGTFS_AVAILABLE:
        raise RuntimeError(
            "pyGTFSHandler is not installed. "
            "Add it as a local dependency in pyproject.toml."
        )


def _get_token() -> str:
    token = os.environ.get("MOBILITY_DB_TOKEN", "")
    if not token:
        raise RuntimeError(
            "MOBILITY_DB_TOKEN environment variable is not set. "
            "Get a refresh token from https://mobilitydatabase.org/"
        )
    return token


def get_gtfs_feeds(aoi_gdf: gpd.GeoDataFrame) -> list[dict]:
    """
    Search Mobility Database for GTFS feeds covering the given AOI.

    Returns a list of dicts: [{id, provider, name}, ...]
    """
    _require_pygtfs()
    api = MobilityDatabaseClient(_get_token())
    feeds = api.search_gtfs_feeds(aoi=aoi_gdf.to_crs("EPSG:4326"), is_official=None)
    return [
        {
            "id": f.get("id", str(i)),
            "provider": f.get("provider", "Unknown"),
            "name": f.get("name") or f.get("provider", "Unknown"),
        }
        for i, f in enumerate(feeds)
    ]


def run_gtfs_analysis(
    city_name: Optional[str] = None,
    address: Optional[str] = None,
    buffer_m: float = 0,
    feed_ids: list[str] = None,
    start_hour: int = 8,
    end_hour: int = 20,
    analysis_date: Optional[str] = None,
    distance_walk: int = 500,
    progress_callback=None,
) -> dict:
    """
    Run GTFS Transit LOS pipeline.

    Steps:
      1. AOI
      2. Download selected GTFS feeds
      3. Parse Feed, compute service quality per stop
      4. isochrones.buffers to create LOS buffer polygons per grade
      5. H3 hexagons + population overlay
    """
    _require_pygtfs()

    def _progress(msg: str):
        if progress_callback:
            progress_callback(msg)

    if not city_name and not address:
        raise ValueError("Provide either city_name or address")

    if feed_ids is None or len(feed_ids) == 0:
        raise ValueError("At least one feed_id must be provided")

    aoi_key = city_name if city_name else f"{address} r={int(round(buffer_m))}m"
    city_filename = sanitize_filename(aoi_key)
    city_results_path = os.path.join(RESULTS_PATH, city_filename + "_gtfs")
    os.makedirs(city_results_path, exist_ok=True)
    os.makedirs(RESULTS_PATH, exist_ok=True)
    os.makedirs(GTFS_PATH, exist_ok=True)

    # 1. AOI
    if city_name:
        _progress("Fetching city geometry...")
        aoi_raw = uaa_utils.get_city_geometry(city_name)
        aoi = gpd.GeoDataFrame(geometry=[aoi_raw.union_all()], crs=aoi_raw.crs)
        aoi = aoi.to_crs(aoi.estimate_utm_crs())
    else:
        _progress("Geocoding address...")
        gdf = geocode(address, results=1, buffer=buffer_m)
        if gdf is None or gdf.empty:
            raise ValueError(f"Could not geocode: {address}")
        aoi = gpd.GeoDataFrame(geometry=[gdf.union_all()], crs=gdf.crs)
        aoi = aoi.to_crs(aoi.estimate_utm_crs())

    aoi_download = aoi.buffer(0)

    # 2. Download GTFS feeds
    _progress("Downloading GTFS feeds...")
    api = MobilityDatabaseClient(_get_token())
    # Search all feeds, then filter by selected IDs
    all_feeds = api.search_gtfs_feeds(
        aoi=aoi_download.to_crs("EPSG:4326"), is_official=None
    )
    selected_feeds = [f for f in all_feeds if str(f.get("id", "")) in feed_ids]
    if not selected_feeds:
        raise ValueError(f"None of the requested feed IDs {feed_ids} were found.")

    files = api.download_feeds(
        selected_feeds, download_folder=GTFS_PATH, overwrite=False
    )

    # 3. Parse GTFS and compute service quality
    _progress("Parsing GTFS feeds...")
    if analysis_date:
        chosen_date = date.fromisoformat(analysis_date)
    else:
        chosen_date = date.today() + timedelta(days=1)

    start_dt = datetime.combine(chosen_date, time())
    end_dt = datetime.combine(chosen_date + timedelta(days=30), time())

    gtfs = Feed(
        files,
        aoi=aoi_download,
        stop_group_distance=100,
        start_date=start_dt,
        end_date=end_dt,
    )

    _progress("Computing stop service quality...")
    service_quality_path = processing_helper.get_service_quality(
        city_results_path,
        gtfs,
        dates=datetime.combine(chosen_date, time()),
        times=[start_hour, end_hour],
    )
    service_quality_gdf = gpd.read_file(service_quality_path).to_crs(aoi.crs)

    service_quality_col = f"service_quality_{start_hour}h_{end_hour}h"
    if service_quality_col not in service_quality_gdf.columns:
        raise ValueError(
            f"Expected column '{service_quality_col}' not found in service quality output. "
            f"Available: {list(service_quality_gdf.columns)}"
        )

    # 4. LOS buffer polygons per grade
    _progress("Generating LOS buffers...")
    level_of_service_gdf = isochrones.buffers(
        service_quality_gdf,
        distance_matrix=processing_helper.DISTANCE_MATRIX,
        accessibility_values=LOS_GRADES,
        poi_quality_col=service_quality_col,
    )
    level_of_service_gdf = level_of_service_gdf.to_crs(aoi.crs)

    # 5. H3 hexagons from LOS buffers
    _progress("Converting LOS buffers to H3 hexagons...")
    access_h3_df = h3_utils.from_gdf(
        level_of_service_gdf,
        resolution=H3_RESOLUTION,
        columns=["accessibility"],
        value_order=LOS_GRADES,
        contain="overlap",
        method="min",
        buffer=10,
    )

    # 6. Population
    pop_raster_ref = os.path.join(city_results_path, ".population_raster_path")
    population_file = None
    if os.path.exists(pop_raster_ref):
        with open(pop_raster_ref) as f:
            cached_path = f.read().strip()
        if os.path.exists(cached_path):
            _progress("Using cached population raster...")
            population_file = cached_path

    if population_file is None:
        _progress("Downloading population data...")
        population_file = population.download_worldpop_population(
            aoi_download, 2025, folder=RESULTS_PATH, resolution="100m"
        )
        if ".zip" in population_file:
            extract_dir = os.path.splitext(population_file)[0]
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(population_file, "r") as zip_ref:
                zip_ref.extractall(extract_dir)
            for file_name in os.listdir(extract_dir):
                if file_name.lower().endswith(".tif") and "_T_" in file_name:
                    population_file = os.path.join(extract_dir, file_name)
                    break
        with open(pop_raster_ref, "w") as f:
            f.write(population_file)

    _progress("Processing population grid...")
    pop_h3_df = h3_utils.from_raster(
        population_file, aoi=aoi_download, resolution=H3_RESOLUTION
    )
    pop_h3_df = pop_h3_df.rename(columns={"value": "population"})

    # 7. Merge + stats
    _progress("Merging data...")
    results_h3_df = access_h3_df.merge(
        pop_h3_df, left_index=True, right_index=True, how="outer"
    )
    results_h3_df = h3_utils.to_gdf(results_h3_df).to_crs(aoi.crs)
    results_h3_df = results_h3_df[results_h3_df.intersects(aoi.union_all())]

    stats_df = results_h3_df.groupby("accessibility", as_index=False)["population"].sum()
    total_population = stats_df["population"].sum()
    stats_df = pd.concat(
        [stats_df, pd.DataFrame([{"accessibility": "total population", "population": total_population}])],
        ignore_index=True,
    )
    stats_df["population_pct"] = (stats_df["population"] * 100 / total_population).round(2)
    stats_df["population"] = stats_df["population"].round(0).astype(int)

    # Stops as POIs
    stops_gdf = service_quality_gdf[["geometry"]].copy().to_crs("EPSG:4326")
    if "stop_name" in service_quality_gdf.columns:
        stops_gdf["name"] = service_quality_gdf["stop_name"]

    _progress("Building response...")
    return {
        "aoi": gdf_to_geojson(aoi.to_crs("EPSG:4326")),
        "pois": gdf_to_geojson(stops_gdf),
        "hexagons": gdf_to_geojson(results_h3_df.to_crs("EPSG:4326")),
        "edges": gdf_to_geojson(level_of_service_gdf.to_crs("EPSG:4326")),
        "stats": stats_df.to_dict(orient="records"),
    }
```

- [ ] **Step 2: Verify import works (pyGTFSHandler not available yet, PYGTFS_AVAILABLE=False is fine)**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
uv run python -c "from backend.analysis_gtfs import run_gtfs_analysis, get_gtfs_feeds, PYGTFS_AVAILABLE; print('PYGTFS_AVAILABLE:', PYGTFS_AVAILABLE)"
```

Expected: `PYGTFS_AVAILABLE: False`

- [ ] **Step 3: Commit**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
git add backend/analysis_gtfs.py
git commit -m "feat: add GTFS analysis pipeline stub (pyGTFSHandler-guarded)"
```

---

## Task 6: FastAPI Backend

**Files:**
- Create: `backend/main.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Write the failing API tests**

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/tests/test_api.py`:

```python
"""FastAPI integration tests using TestClient."""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health():
    """The app starts and responds to a basic request."""
    res = client.get("/api/job/nonexistent")
    assert res.status_code == 404


def test_suggestions_returns_list():
    mock_results = [{"display_name": "Berlin, Germany", "lat": "52.5", "lon": "13.4"}]
    with patch("backend.main.requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: mock_results,
            raise_for_status=lambda: None,
        )
        res = client.get("/api/suggestions?q=Berlin")
    assert res.status_code == 200
    data = res.json()
    assert "suggestions" in data
    assert isinstance(data["suggestions"], list)


def test_analyze_schools_creates_job():
    with patch("backend.main.asyncio.create_task"):
        res = client.post(
            "/api/analyze",
            json={
                "analysis_type": "schools",
                "city_name": "Bilbao, Spain",
                "distance_walk": 1000,
                "distance_bike": 2500,
                "distance_car": 10000,
                "kids_only": False,
            },
        )
    assert res.status_code == 200
    data = res.json()
    assert "job_id" in data
    assert isinstance(data["job_id"], str)


def test_analyze_parks_creates_job():
    with patch("backend.main.asyncio.create_task"):
        res = client.post(
            "/api/analyze",
            json={
                "analysis_type": "parks",
                "city_name": "Bilbao, Spain",
                "distance_walk": 500,
            },
        )
    assert res.status_code == 200
    assert "job_id" in res.json()


def test_analyze_gtfs_creates_job():
    with patch("backend.main.asyncio.create_task"):
        res = client.post(
            "/api/analyze",
            json={
                "analysis_type": "gtfs",
                "city_name": "Bilbao, Spain",
                "feed_ids": ["feed-123"],
                "start_hour": 8,
                "end_hour": 20,
            },
        )
    assert res.status_code == 200
    assert "job_id" in res.json()


def test_analyze_missing_type_returns_422():
    res = client.post(
        "/api/analyze",
        json={"city_name": "Bilbao, Spain"},
    )
    assert res.status_code == 422


def test_analyze_neither_city_nor_address_returns_422():
    res = client.post(
        "/api/analyze",
        json={"analysis_type": "schools", "distance_walk": 1000},
    )
    assert res.status_code == 422


def test_job_status_not_found():
    res = client.get("/api/job/does-not-exist")
    assert res.status_code == 404


def test_job_status_running():
    from backend.main import jobs
    jobs["test-job-123"] = {
        "status": "running",
        "progress": "Processing...",
        "result": None,
        "error": None,
    }
    res = client.get("/api/job/test-job-123")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "running"
    assert data["progress"] == "Processing..."
    jobs.pop("test-job-123")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
uv run pytest tests/test_api.py -v
```

Expected: `ImportError: cannot import name 'app' from 'backend.main'`

- [ ] **Step 3: Write backend/main.py**

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/backend/main.py`:

```python
"""FastAPI backend for UrbanAccessApp: Transit, Schools, Parks accessibility analysis."""
import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import Literal, Optional

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, model_validator

from backend.analysis_schools import run_schools_analysis
from backend.analysis_parks import run_parks_analysis
from backend.analysis_gtfs import get_gtfs_feeds as _get_gtfs_feeds, run_gtfs_analysis
from backend.utils import geocode

import geopandas as gpd
from shapely.geometry import box
import osmnx as ox

jobs: dict[str, dict] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    jobs.clear()


app = FastAPI(title="Urban Access Analyzer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ──────────────────────────────────────


class CityRequest(BaseModel):
    city_name: str


class GeocodeRequest(BaseModel):
    address: str
    buffer_m: float


class AnalysisRequest(BaseModel):
    analysis_type: Literal["schools", "parks", "gtfs"]
    city_name: Optional[str] = None
    address: Optional[str] = None
    buffer_m: float = 5000
    # Schools / Parks
    distance_walk: int = 1000
    distance_bike: int = 2500
    distance_car: int = 10000
    kids_only: bool = False
    # GTFS
    feed_ids: Optional[list[str]] = None
    start_hour: int = 8
    end_hour: int = 20
    analysis_date: Optional[str] = None

    @model_validator(mode="after")
    def check_aoi(self):
        if not self.city_name and not self.address:
            raise ValueError("Provide either city_name or address")
        if self.city_name and self.address:
            raise ValueError("Provide only one of city_name or address")
        return self


# ── Endpoints ──────────────────────────────────────────────────────


@app.get("/api/suggestions")
async def suggestions(q: str):
    """Nominatim autocomplete."""
    try:
        resp = await asyncio.to_thread(
            lambda: requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": q, "format": "json", "limit": 8, "addressdetails": 1},
                headers={"User-Agent": "urban-access-app/1.0"},
                timeout=10,
            )
        )
        resp.raise_for_status()
        return {
            "suggestions": [
                {"display_name": item["display_name"], "lat": item["lat"], "lon": item["lon"]}
                for item in resp.json()
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/city-geometry")
async def city_geometry(req: CityRequest):
    """Return city boundary as GeoJSON (EPSG:4326)."""
    try:
        def _fetch():
            import UrbanAccessAnalyzer.utils as uaa_utils
            from shapely.geometry import mapping
            aoi = uaa_utils.get_city_geometry(req.city_name)
            aoi = gpd.GeoDataFrame(geometry=[aoi.union_all()], crs=aoi.crs).to_crs("EPSG:4326")
            return {
                "type": "FeatureCollection",
                "features": [{"type": "Feature", "geometry": mapping(aoi.geometry.iloc[0]), "properties": {}}],
            }
        return await asyncio.to_thread(_fetch)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/geocode-geometry")
async def geocode_geometry(req: GeocodeRequest):
    """Geocode address + buffer, return as GeoJSON (EPSG:4326)."""
    try:
        def _fetch():
            from shapely.geometry import mapping
            gdf = geocode(req.address, results=1, buffer=req.buffer_m)
            if gdf is None or gdf.empty:
                raise ValueError(f"Could not geocode: {req.address}")
            aoi = gdf.to_crs("EPSG:4326")
            return {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": mapping(aoi.geometry.iloc[0]),
                        "properties": {"display_name": aoi.iloc[0].get("display_name", req.address)},
                    }
                ],
            }
        return await asyncio.to_thread(_fetch)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gtfs-feeds")
async def gtfs_feeds(bbox: str):
    """
    Search Mobility Database for GTFS feeds covering the given bounding box.
    bbox format: "minx,miny,maxx,maxy" in EPSG:4326.
    """
    try:
        def _fetch():
            minx, miny, maxx, maxy = map(float, bbox.split(","))
            aoi_gdf = gpd.GeoDataFrame(
                geometry=[box(minx, miny, maxx, maxy)], crs="EPSG:4326"
            )
            return _get_gtfs_feeds(aoi_gdf)
        return await asyncio.to_thread(_fetch)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze")
async def start_analysis(req: AnalysisRequest):
    """Start a long-running analysis job. Returns job_id for polling."""
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "running", "progress": "Starting...", "result": None, "error": None}

    async def _run():
        loop = asyncio.get_event_loop()
        try:
            def progress_cb(msg: str):
                jobs[job_id]["progress"] = msg

            if req.analysis_type == "schools":
                result = await loop.run_in_executor(
                    None,
                    lambda: run_schools_analysis(
                        city_name=req.city_name,
                        address=req.address,
                        buffer_m=req.buffer_m,
                        distance_steps=[req.distance_walk, req.distance_bike, req.distance_car],
                        accessibility_values=["walk", "bike", "bus/car"],
                        kids_only=req.kids_only,
                        progress_callback=progress_cb,
                    ),
                )
            elif req.analysis_type == "parks":
                result = await loop.run_in_executor(
                    None,
                    lambda: run_parks_analysis(
                        city_name=req.city_name,
                        address=req.address,
                        buffer_m=req.buffer_m,
                        distance_walk=req.distance_walk,
                        progress_callback=progress_cb,
                    ),
                )
            else:  # gtfs
                result = await loop.run_in_executor(
                    None,
                    lambda: run_gtfs_analysis(
                        city_name=req.city_name,
                        address=req.address,
                        buffer_m=req.buffer_m,
                        feed_ids=req.feed_ids or [],
                        start_hour=req.start_hour,
                        end_hour=req.end_hour,
                        analysis_date=req.analysis_date,
                        distance_walk=req.distance_walk,
                        progress_callback=progress_cb,
                    ),
                )

            jobs[job_id]["status"] = "completed"
            jobs[job_id]["result"] = result
        except Exception as e:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)

    asyncio.create_task(_run())
    return {"job_id": job_id}


@app.get("/api/job/{job_id}")
async def job_status(job_id: str):
    """Poll for analysis job status and result."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    job = jobs[job_id]
    response = {"status": job["status"], "progress": job["progress"]}
    if job["status"] == "completed":
        response["result"] = job["result"]
    elif job["status"] == "failed":
        response["error"] = job["error"]
    return response
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
uv run pytest tests/test_api.py tests/test_utils.py -v
```

Expected: `13 passed`

- [ ] **Step 5: Commit**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
git add backend/main.py tests/test_api.py
git commit -m "feat: add FastAPI backend with job queue and all endpoints"
```

---

## Task 7: Frontend Scaffold

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.app.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/index.html`

- [ ] **Step 1: Write frontend/package.json**

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/frontend/package.json`:

```json
{
  "name": "urban-access-app-frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@types/leaflet": "^1.9.21",
    "leaflet": "^1.9.4",
    "react": "^19.2.0",
    "react-dom": "^19.2.0",
    "react-leaflet": "^5.0.0"
  },
  "devDependencies": {
    "@eslint/js": "^9.39.1",
    "@tailwindcss/vite": "^4.2.0",
    "@types/node": "^24.0.0",
    "@types/react": "^19.2.7",
    "@types/react-dom": "^19.2.3",
    "@vitejs/plugin-react": "^5.1.1",
    "eslint": "^9.39.1",
    "globals": "^16.5.0",
    "tailwindcss": "^4.2.0",
    "typescript": "~5.9.3",
    "typescript-eslint": "^8.48.0",
    "vite": "^7.3.1"
  }
}
```

- [ ] **Step 2: Write frontend/vite.config.ts**

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/frontend/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:7000',
    },
  },
})
```

- [ ] **Step 3: Write tsconfig files**

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/frontend/tsconfig.json`:

```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}
```

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/frontend/tsconfig.app.json`:

```json
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo",
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true
  },
  "include": ["src"]
}
```

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/frontend/tsconfig.node.json`:

```json
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.node.tsbuildinfo",
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 4: Write frontend/index.html**

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/frontend/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link
      rel="stylesheet"
      href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
    />
    <title>Urban Access Analyzer</title>
  </head>
  <body>
    <div id="root" class="h-screen w-screen"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Create src directory and install npm dependencies**

```bash
mkdir -p /home/xabi9/Documents/Sources/UrbanAccessApp/frontend/src/components
cd /home/xabi9/Documents/Sources/UrbanAccessApp/frontend
npm install
```

Expected: `node_modules/` created, no errors.

- [ ] **Step 6: Commit**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
git add frontend/package.json frontend/vite.config.ts frontend/tsconfig*.json frontend/index.html
git commit -m "chore: frontend scaffold (Vite + React + TypeScript + Tailwind)"
```

---

## Task 8: Frontend Types + API Client

**Files:**
- Create: `frontend/src/types.ts`
- Create: `frontend/src/api.ts`

- [ ] **Step 1: Write frontend/src/types.ts**

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/frontend/src/types.ts`:

```typescript
export type AnalysisMode = "gtfs" | "schools" | "parks";

export interface Suggestion {
  display_name: string;
  lat: string;
  lon: string;
}

export type CityAOI = {
  kind: "city";
  city_name: string;
};

export type AddressAOI = {
  kind: "address";
  address: string;
  buffer_m: number;
};

export type AoiSelection = CityAOI | AddressAOI;

export interface GtfsFeed {
  id: string;
  provider: string;
  name: string;
}

export interface AnalysisRequest {
  analysis_type: AnalysisMode;
  city_name?: string;
  address?: string;
  buffer_m?: number;
  // Schools / Parks
  distance_walk?: number;
  distance_bike?: number;
  distance_car?: number;
  kids_only?: boolean;
  // GTFS
  feed_ids?: string[];
  start_hour?: number;
  end_hour?: number;
  analysis_date?: string;
}

export interface StatsRow {
  accessibility: string;
  population: number;
  population_pct: number;
}

export interface AnalysisResult {
  aoi: GeoJSON.FeatureCollection;
  pois: GeoJSON.FeatureCollection;
  hexagons: GeoJSON.FeatureCollection;
  edges: GeoJSON.FeatureCollection;
  stats: StatsRow[];
}

export interface JobStatus {
  status: "running" | "completed" | "failed";
  progress: string;
  result?: AnalysisResult;
  error?: string;
}
```

- [ ] **Step 2: Write frontend/src/api.ts**

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/frontend/src/api.ts`:

```typescript
import type { AnalysisRequest, GtfsFeed, JobStatus, Suggestion } from "./types";

const BASE = "/api";

export async function fetchSuggestions(query: string): Promise<Suggestion[]> {
  const res = await fetch(`${BASE}/suggestions?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error("Failed to fetch suggestions");
  return (await res.json()).suggestions;
}

export async function fetchCityGeometry(
  cityName: string
): Promise<GeoJSON.FeatureCollection> {
  const res = await fetch(`${BASE}/city-geometry`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ city_name: cityName }),
  });
  if (!res.ok) throw new Error("Failed to fetch city geometry");
  return res.json();
}

export async function fetchGeocodeGeometry(
  address: string,
  bufferM: number
): Promise<GeoJSON.FeatureCollection> {
  const res = await fetch(`${BASE}/geocode-geometry`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ address, buffer_m: bufferM }),
  });
  if (!res.ok) throw new Error("Failed to geocode address");
  return res.json();
}

export async function fetchGtfsFeeds(bbox: string): Promise<GtfsFeed[]> {
  const res = await fetch(`${BASE}/gtfs-feeds?bbox=${encodeURIComponent(bbox)}`);
  if (!res.ok) throw new Error("Failed to fetch GTFS feeds");
  return res.json();
}

export async function startAnalysis(params: AnalysisRequest): Promise<string> {
  const res = await fetch(`${BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to start analysis");
  }
  return (await res.json()).job_id;
}

export async function pollJob(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${BASE}/job/${jobId}`);
  if (!res.ok) throw new Error("Failed to poll job");
  return res.json();
}
```

- [ ] **Step 3: Commit**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
git add frontend/src/types.ts frontend/src/api.ts
git commit -m "feat: frontend types and API client"
```

---

## Task 9: Shared Frontend Components (ErrorBoundary + StatsPanel)

**Files:**
- Create: `frontend/src/components/ErrorBoundary.tsx`
- Create: `frontend/src/components/StatsPanel.tsx`

- [ ] **Step 1: Write ErrorBoundary.tsx** (direct port)

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/frontend/src/components/ErrorBoundary.tsx`:

```typescript
import { Component, type ReactNode } from "react";

interface Props { children: ReactNode; }
interface State { error: Error | null; }

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex h-full items-center justify-center bg-gray-950 p-8 text-white">
          <div className="max-w-md space-y-4 text-center">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-red-500/20">
              <svg className="h-7 w-7 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold">Something went wrong</h2>
            <p className="text-sm text-gray-400">{this.state.error.message}</p>
            <button
              onClick={() => this.setState({ error: null })}
              className="rounded-xl bg-white/10 px-4 py-2 text-sm font-medium text-gray-200 transition hover:bg-white/20"
            >
              Try again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
```

- [ ] **Step 2: Write StatsPanel.tsx** (extended with GTFS LOS grade colors)

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/frontend/src/components/StatsPanel.tsx`:

```typescript
import type { StatsRow } from "../types";

// Colors for schools/parks modes
const ROW_COLORS: Record<string, string> = {
  walk: "text-emerald-400",
  bike: "text-blue-400",
  "bus/car": "text-amber-400",
  "total population": "text-white",
};

const BAR_COLORS: Record<string, string> = {
  walk: "bg-emerald-500",
  bike: "bg-blue-500",
  "bus/car": "bg-amber-500",
};

// GTFS LOS grade colors (A=green, B=yellow, C=orange, D=red, E=purple, F=blue)
const LOS_GRADE_BG: Record<string, string> = {
  A1: "bg-[#68b684]", A2: "bg-[#40916c]", A3: "bg-[#1b4332]",
  B1: "bg-[#f1c40f]", B2: "bg-[#d4ac0d]", B3: "bg-[#b7950b]",
  C1: "bg-[#ffa75a]", C2: "bg-[#fa8246]", C3: "bg-[#cf5600]",
  D: "bg-[#b30202]",
  E: "bg-[#9b59b6]",
  F: "bg-[#0051ff]",
};

function getBarClass(acc: string): string {
  return BAR_COLORS[acc] ?? LOS_GRADE_BG[acc] ?? "bg-gray-500";
}

function getTextClass(acc: string): string {
  return ROW_COLORS[acc] ?? "text-gray-300";
}

interface Props {
  stats: StatsRow[];
}

export default function StatsPanel({ stats }: Props) {
  const dataRows = stats.filter((r) => r.accessibility !== "total population");
  const totalRow = stats.find((r) => r.accessibility === "total population");

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-400">
        Population Coverage
      </h3>

      {dataRows.map((row) => (
        <div key={row.accessibility} className="space-y-1">
          <div className="flex items-center justify-between text-sm">
            <span className={`font-medium capitalize ${getTextClass(row.accessibility)}`}>
              {row.accessibility}
            </span>
            <span className="tabular-nums text-gray-300">
              {row.population.toLocaleString()} ({row.population_pct}%)
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-white/5">
            <div
              className={`h-full rounded-full transition-all duration-500 ${getBarClass(row.accessibility)}`}
              style={{ width: `${Math.min(row.population_pct, 100)}%` }}
            />
          </div>
        </div>
      ))}

      {totalRow && (
        <div className="mt-4 flex items-center justify-between border-t border-white/10 pt-3 text-sm font-semibold text-white">
          <span>Total Population</span>
          <span className="tabular-nums">{totalRow.population.toLocaleString()}</span>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
git add frontend/src/components/ErrorBoundary.tsx frontend/src/components/StatsPanel.tsx
git commit -m "feat: add ErrorBoundary and StatsPanel with GTFS LOS grade support"
```

---

## Task 10: CityMap Component

**Files:**
- Create: `frontend/src/components/CityMap.tsx`

- [ ] **Step 1: Write CityMap.tsx** (extended with GTFS LOS grade colors)

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/frontend/src/components/CityMap.tsx`:

```typescript
import { useEffect, useRef } from "react";
import { GeoJSON, MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import type { AnalysisResult } from "../types";

const poiIcon = L.divIcon({
  className: "",
  iconSize: [28, 36],
  iconAnchor: [14, 36],
  popupAnchor: [0, -34],
  html: `<svg xmlns="http://www.w3.org/2000/svg" width="28" height="36" viewBox="0 0 28 36">
    <filter id="ds" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="1" stdDeviation="1.5" flood-color="#000" flood-opacity="0.5"/>
    </filter>
    <path filter="url(#ds)" d="M14 0C6.268 0 0 6.268 0 14c0 10.5 14 22 14 22s14-11.5 14-22C28 6.268 21.732 0 14 0z" fill="#ef4444" stroke="#fff" stroke-width="2"/>
    <circle cx="14" cy="13" r="5.5" fill="#fff"/>
  </svg>`,
});

// Schools / Parks mode colors
const ACCESSIBILITY_COLORS: Record<string, string> = {
  walk: "#22c55e",
  bike: "#3b82f6",
  "bus/car": "#f59e0b",
};

// GTFS LOS grade colors
const LOS_GRADE_COLORS: Record<string, string> = {
  A1: "#68b684", A2: "#40916c", A3: "#1b4332",
  B1: "#f1c40f", B2: "#d4ac0d", B3: "#b7950b",
  C1: "#ffa75a", C2: "#fa8246", C3: "#cf5600",
  D:  "#b30202",
  E:  "#9b59b6",
  F:  "#0051ff",
};

function getFeatureColor(accessibility: string): string {
  return (
    ACCESSIBILITY_COLORS[accessibility] ??
    LOS_GRADE_COLORS[accessibility] ??
    "#6b7280"
  );
}

type FeatureProps = {
  accessibility?: string;
  population?: number | string;
  name?: string;
};
type MapFeature = GeoJSON.Feature<GeoJSON.Geometry, FeatureProps>;

function FitBounds({ geojson }: { geojson: GeoJSON.FeatureCollection }) {
  const map = useMap();
  const fitted = useRef(false);
  useEffect(() => {
    if (!fitted.current && geojson.features.length > 0) {
      const layer = L.geoJSON(geojson as GeoJSON.GeoJsonObject);
      const bounds = layer.getBounds();
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [40, 40] });
        fitted.current = true;
      }
    }
  }, [geojson, map]);
  return null;
}

function ResetFit({ geojson }: { geojson: GeoJSON.FeatureCollection }) {
  const map = useMap();
  useEffect(() => {
    if (geojson.features.length > 0) {
      const layer = L.geoJSON(geojson as GeoJSON.GeoJsonObject);
      const bounds = layer.getBounds();
      if (bounds.isValid()) map.fitBounds(bounds, { padding: [40, 40] });
    }
  }, [geojson, map]);
  return null;
}

interface Props {
  aoiGeojson: GeoJSON.FeatureCollection | null;
  result: AnalysisResult | null;
}

export default function CityMap({ aoiGeojson, result }: Props) {
  const hexagonStyle = (feature?: MapFeature) => {
    const color = getFeatureColor(feature?.properties?.accessibility ?? "");
    return { fillColor: color, fillOpacity: 0.45, color, weight: 0.5, opacity: 0.7 };
  };

  const edgeStyle = (feature?: MapFeature) => {
    const color = getFeatureColor(feature?.properties?.accessibility ?? "");
    return { color, weight: 2, opacity: 0.8 };
  };

  const aoiStyle = {
    fillColor: "transparent",
    fillOpacity: 0,
    color: "#e5e7eb",
    weight: 2.5,
    dashArray: "6 4",
  };

  const displayAoi = result?.aoi ?? aoiGeojson;

  return (
    <MapContainer
      center={[40, -3]}
      zoom={3}
      className="h-full w-full rounded-xl"
      scrollWheelZoom
    >
      <TileLayer
        attribution='&copy; <a href="https://carto.com/">CARTO</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />

      {displayAoi && (
        <>
          <FitBounds geojson={displayAoi} />
          <GeoJSON data={displayAoi} style={() => aoiStyle} />
        </>
      )}

      {result && (
        <>
          <ResetFit geojson={result.aoi} />
          <GeoJSON
            data={result.hexagons}
            style={hexagonStyle}
            onEachFeature={(feature: GeoJSON.Feature, layer) => {
              const p = (feature as MapFeature).properties;
              if (p) {
                const pop = p.population;
                const popText =
                  pop == null || String(pop) === "nan"
                    ? "N/A"
                    : Math.round(Number(pop)).toString();
                layer.bindPopup(
                  `<b>Accessibility:</b> ${p.accessibility ?? "N/A"}<br/><b>Population:</b> ${popText}`
                );
              }
            }}
          />
          <GeoJSON data={result.edges} style={edgeStyle} />
          {result.pois?.features?.map((f, i) => {
            const coords = (f.geometry as GeoJSON.Point).coordinates;
            if (!coords) return null;
            return (
              <Marker key={i} position={[coords[1], coords[0]]} icon={poiIcon}>
                <Popup>
                  <span className="font-medium">{f.properties?.name ?? "POI"}</span>
                </Popup>
              </Marker>
            );
          })}
        </>
      )}
    </MapContainer>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
git add frontend/src/components/CityMap.tsx
git commit -m "feat: add CityMap with GTFS LOS grade color support"
```

---

## Task 11: Mode-Specific Control Panels

**Files:**
- Create: `frontend/src/components/SchoolsControls.tsx`
- Create: `frontend/src/components/ParksControls.tsx`
- Create: `frontend/src/components/GtfsControls.tsx`

- [ ] **Step 1: Write SchoolsControls.tsx**

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/frontend/src/components/SchoolsControls.tsx`:

```typescript
interface Props {
  distanceWalk: number;
  distanceBike: number;
  distanceCar: number;
  kidsOnly: boolean;
  onChangeWalk: (v: number) => void;
  onChangeBike: (v: number) => void;
  onChangeCar: (v: number) => void;
  onChangeKidsOnly: (v: boolean) => void;
}

const MODES = [
  { label: "Walking",  color: "emerald", min: 200,  max: 3000,  step: 100, key: 0 },
  { label: "Biking",   color: "blue",    min: 500,  max: 8000,  step: 250, key: 1 },
  { label: "Bus/Car",  color: "amber",   min: 1000, max: 20000, step: 500, key: 2 },
] as const;

const C = {
  emerald: { bg: "bg-emerald-500/10", text: "text-emerald-400", accent: "accent-emerald-500", badge: "bg-emerald-500/20 text-emerald-300" },
  blue:    { bg: "bg-blue-500/10",    text: "text-blue-400",    accent: "accent-blue-500",    badge: "bg-blue-500/20 text-blue-300"    },
  amber:   { bg: "bg-amber-500/10",   text: "text-amber-400",   accent: "accent-amber-500",   badge: "bg-amber-500/20 text-amber-300"  },
};

export default function SchoolsControls(props: Props) {
  const values = [props.distanceWalk, props.distanceBike, props.distanceCar];
  const handlers = [props.onChangeWalk, props.onChangeBike, props.onChangeCar];

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-400">
        Distance Thresholds
      </h3>
      {MODES.map((mode, i) => {
        const c = C[mode.color];
        return (
          <div key={mode.label} className={`rounded-xl ${c.bg} p-4`}>
            <div className="mb-2 flex items-center justify-between">
              <span className={`text-sm font-medium ${c.text}`}>{mode.label}</span>
              <span className={`rounded-lg px-2 py-0.5 text-xs font-semibold ${c.badge}`}>
                {(values[i] / 1000).toFixed(1)} km
              </span>
            </div>
            <input
              type="range"
              min={mode.min} max={mode.max} step={mode.step}
              value={values[i]}
              onChange={(e) => handlers[i](Number(e.target.value))}
              className={`w-full ${c.accent} h-1.5 cursor-pointer appearance-none rounded-full bg-white/10`}
            />
            <div className="mt-1 flex justify-between text-[10px] text-gray-500">
              <span>{(mode.min / 1000).toFixed(1)} km</span>
              <span>{(mode.max / 1000).toFixed(1)} km</span>
            </div>
          </div>
        );
      })}
      <label className="flex cursor-pointer items-center gap-3 rounded-xl bg-white/5 p-3">
        <input
          type="checkbox"
          checked={props.kidsOnly}
          onChange={(e) => props.onChangeKidsOnly(e.target.checked)}
          className="h-4 w-4 accent-emerald-500"
        />
        <span className="text-sm text-gray-300">Children under 18 only (population)</span>
      </label>
    </div>
  );
}
```

- [ ] **Step 2: Write ParksControls.tsx**

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/frontend/src/components/ParksControls.tsx`:

```typescript
interface Props {
  distanceWalk: number;
  onChangeWalk: (v: number) => void;
}

export default function ParksControls({ distanceWalk, onChangeWalk }: Props) {
  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-400">
        Walking Distance
      </h3>
      <div className="rounded-xl bg-emerald-500/10 p-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm font-medium text-emerald-400">Walking</span>
          <span className="rounded-lg bg-emerald-500/20 px-2 py-0.5 text-xs font-semibold text-emerald-300">
            {(distanceWalk / 1000).toFixed(2)} km
          </span>
        </div>
        <input
          type="range"
          min={100} max={2000} step={50}
          value={distanceWalk}
          onChange={(e) => onChangeWalk(Number(e.target.value))}
          className="w-full accent-emerald-500 h-1.5 cursor-pointer appearance-none rounded-full bg-white/10"
        />
        <div className="mt-1 flex justify-between text-[10px] text-gray-500">
          <span>0.1 km</span>
          <span>2.0 km</span>
        </div>
      </div>
      <p className="text-xs text-gray-500">
        Area reachable on foot from any park entrance.
      </p>
    </div>
  );
}
```

- [ ] **Step 3: Write GtfsControls.tsx**

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/frontend/src/components/GtfsControls.tsx`:

```typescript
import { useCallback, useEffect, useState } from "react";
import { fetchGtfsFeeds } from "../api";
import type { GtfsFeed } from "../types";

interface Props {
  aoiBbox: string | null;        // "minx,miny,maxx,maxy" — set once AOI is loaded
  startHour: number;
  endHour: number;
  selectedFeedIds: string[];
  onChangeStartHour: (v: number) => void;
  onChangeEndHour: (v: number) => void;
  onChangeFeedIds: (ids: string[]) => void;
}

export default function GtfsControls({
  aoiBbox,
  startHour,
  endHour,
  selectedFeedIds,
  onChangeStartHour,
  onChangeEndHour,
  onChangeFeedIds,
}: Props) {
  const [feeds, setFeeds] = useState<GtfsFeed[]>([]);
  const [loadingFeeds, setLoadingFeeds] = useState(false);
  const [feedError, setFeedError] = useState<string | null>(null);

  const loadFeeds = useCallback(async (bbox: string) => {
    setLoadingFeeds(true);
    setFeedError(null);
    try {
      const results = await fetchGtfsFeeds(bbox);
      setFeeds(results);
    } catch (e: unknown) {
      setFeedError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingFeeds(false);
    }
  }, []);

  useEffect(() => {
    if (aoiBbox) loadFeeds(aoiBbox);
  }, [aoiBbox, loadFeeds]);

  function toggleFeed(id: string) {
    if (selectedFeedIds.includes(id)) {
      onChangeFeedIds(selectedFeedIds.filter((f) => f !== id));
    } else {
      onChangeFeedIds([...selectedFeedIds, id]);
    }
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-400">
        Service Hours
      </h3>
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl bg-white/5 p-3">
          <p className="mb-1 text-xs text-gray-400">Start hour</p>
          <input
            type="number" min={0} max={23} step={1}
            value={startHour}
            onChange={(e) => onChangeStartHour(Number(e.target.value))}
            className="w-full bg-transparent text-lg font-semibold text-white outline-none"
          />
        </div>
        <div className="rounded-xl bg-white/5 p-3">
          <p className="mb-1 text-xs text-gray-400">End hour</p>
          <input
            type="number" min={0} max={23} step={1}
            value={endHour}
            onChange={(e) => onChangeEndHour(Number(e.target.value))}
            className="w-full bg-transparent text-lg font-semibold text-white outline-none"
          />
        </div>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-gray-400">
          GTFS Feeds
        </h3>

        {!aoiBbox && (
          <p className="text-xs text-gray-500">Loading AOI to search feeds...</p>
        )}

        {aoiBbox && loadingFeeds && (
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <div className="h-3 w-3 animate-spin rounded-full border border-gray-500 border-t-purple-400" />
            Searching Mobility Database...
          </div>
        )}

        {feedError && (
          <p className="text-xs text-red-400">{feedError}</p>
        )}

        {!loadingFeeds && feeds.length === 0 && aoiBbox && !feedError && (
          <p className="text-xs text-gray-500">No feeds found for this area.</p>
        )}

        {feeds.length > 0 && (
          <div className="max-h-48 space-y-1 overflow-y-auto">
            {feeds.map((feed) => (
              <label
                key={feed.id}
                className="flex cursor-pointer items-start gap-2 rounded-lg bg-white/5 px-3 py-2 text-sm transition hover:bg-white/10"
              >
                <input
                  type="checkbox"
                  checked={selectedFeedIds.includes(feed.id)}
                  onChange={() => toggleFeed(feed.id)}
                  className="mt-0.5 h-4 w-4 shrink-0 accent-purple-500"
                />
                <div>
                  <p className="font-medium text-gray-200">{feed.provider}</p>
                  {feed.name !== feed.provider && (
                    <p className="text-xs text-gray-500">{feed.name}</p>
                  )}
                </div>
              </label>
            ))}
          </div>
        )}

        {feeds.length > 0 && selectedFeedIds.length === 0 && (
          <p className="mt-1 text-xs text-amber-400">Select at least one feed to run analysis.</p>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
git add frontend/src/components/SchoolsControls.tsx frontend/src/components/ParksControls.tsx frontend/src/components/GtfsControls.tsx
git commit -m "feat: add mode-specific control panels (Schools, Parks, GTFS)"
```

---

## Task 12: LandingPage

**Files:**
- Create: `frontend/src/components/LandingPage.tsx`

- [ ] **Step 1: Write LandingPage.tsx**

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/frontend/src/components/LandingPage.tsx`:

```typescript
import { useCallback, useEffect, useRef, useState } from "react";
import { fetchSuggestions } from "../api";
import type { AnalysisMode, AoiSelection, Suggestion } from "../types";

interface Props {
  mode: AnalysisMode;
  onSelectMode: (m: AnalysisMode) => void;
  onSelect: (aoi: AoiSelection) => void;
}

const MODES: { value: AnalysisMode; label: string; description: string }[] = [
  { value: "gtfs",    label: "Transit",  description: "Public transport level of service" },
  { value: "schools", label: "Schools",  description: "Walking, biking, and driving to school" },
  { value: "parks",   label: "Parks",    description: "Green space within walking distance" },
];

const SearchIcon = () => (
  <svg className="h-5 w-5 shrink-0 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
  </svg>
);

const PinIcon = () => (
  <svg className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 0 1 15 0Z" />
  </svg>
);

function SuggestionDropdown({ suggestions, onSelect }: { suggestions: Suggestion[]; onSelect: (s: Suggestion) => void }) {
  return (
    <ul className="absolute top-full z-50 mt-2 max-h-72 w-full overflow-y-auto rounded-xl border border-white/10 bg-gray-900/95 shadow-2xl backdrop-blur-xl">
      {suggestions.map((s, i) => (
        <li key={i}>
          <button
            onClick={() => onSelect(s)}
            className="flex w-full items-start gap-3 px-5 py-3 text-left text-sm text-gray-200 transition hover:bg-white/5"
          >
            <PinIcon />
            <span>{s.display_name}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

function useSearch() {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const search = useCallback(async (q: string) => {
    if (q.length < 3) { setSuggestions([]); return; }
    setLoading(true);
    try {
      const results = await fetchSuggestions(q);
      setSuggestions(results);
      setShowDropdown(true);
    } catch { setSuggestions([]); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => search(query), 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query, search]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node))
        setShowDropdown(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return { query, setQuery, suggestions, showDropdown, setShowDropdown, loading, wrapperRef };
}

function CitySearch({ onSelect }: { onSelect: (aoi: AoiSelection) => void }) {
  const { query, setQuery, suggestions, showDropdown, setShowDropdown, loading, wrapperRef } = useSearch();
  return (
    <div>
      <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-400">
        Search by city boundary
      </p>
      <div ref={wrapperRef} className="relative">
        <div className="flex items-center rounded-2xl border border-white/10 bg-white/10 shadow-2xl backdrop-blur-xl transition focus-within:border-emerald-400/50 focus-within:ring-2 focus-within:ring-emerald-400/20">
          <div className="ml-5"><SearchIcon /></div>
          <input
            type="text" value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter a city name (e.g. Bilbao, Spain)"
            className="w-full bg-transparent px-4 py-4 text-lg text-white placeholder-gray-400 outline-none"
          />
          {loading && <div className="mr-4 h-5 w-5 animate-spin rounded-full border-2 border-gray-500 border-t-emerald-400" />}
        </div>
        {showDropdown && suggestions.length > 0 && (
          <SuggestionDropdown
            suggestions={suggestions}
            onSelect={(s) => { setShowDropdown(false); onSelect({ kind: "city", city_name: s.display_name }); }}
          />
        )}
      </div>
    </div>
  );
}

function AddressSearch({ onSelect }: { onSelect: (aoi: AoiSelection) => void }) {
  const { query, setQuery, suggestions, showDropdown, setShowDropdown, loading, wrapperRef } = useSearch();
  const [selectedAddr, setSelectedAddr] = useState<Suggestion | null>(null);
  const [bufferM, setBufferM] = useState(5000);
  const skipNextRef = useRef(false);

  function handleAddrPick(s: Suggestion) {
    setShowDropdown(false);
    skipNextRef.current = true;
    setQuery(s.display_name);
    setSelectedAddr(s);
  }

  return (
    <div>
      <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-400">
        Search by address + radius
      </p>
      <div className="flex gap-3">
        <div ref={wrapperRef} className="relative flex-1">
          <div className="flex items-center rounded-2xl border border-white/10 bg-white/10 shadow-2xl backdrop-blur-xl transition focus-within:border-blue-400/50 focus-within:ring-2 focus-within:ring-blue-400/20">
            <div className="ml-5"><PinIcon /></div>
            <input
              type="text" value={query}
              onChange={(e) => { setQuery(e.target.value); if (selectedAddr) setSelectedAddr(null); }}
              placeholder="Enter an address or place name"
              className="w-full bg-transparent px-4 py-4 text-base text-white placeholder-gray-400 outline-none"
            />
            {loading && <div className="mr-4 h-5 w-5 animate-spin rounded-full border-2 border-gray-500 border-t-blue-400" />}
          </div>
          {showDropdown && suggestions.length > 0 && (
            <SuggestionDropdown suggestions={suggestions} onSelect={handleAddrPick} />
          )}
        </div>
        <div className="flex w-[140px] shrink-0 flex-col items-center justify-center rounded-2xl border border-white/10 bg-white/10 px-3 backdrop-blur-xl">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-400">Buffer</span>
          <div className="flex items-baseline gap-1">
            <input
              type="number" min={100} max={100000} step={500} value={bufferM}
              onChange={(e) => setBufferM(Number(e.target.value))}
              className="w-[70px] bg-transparent text-center text-lg font-semibold text-white outline-none"
            />
            <span className="text-xs text-gray-400">m</span>
          </div>
        </div>
        <button
          onClick={() => selectedAddr && onSelect({ kind: "address", address: selectedAddr.display_name, buffer_m: bufferM })}
          disabled={!selectedAddr}
          className="flex w-[56px] shrink-0 items-center justify-center rounded-2xl bg-emerald-600 text-white shadow-lg transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
          </svg>
        </button>
      </div>
      {selectedAddr && (
        <p className="mt-2 text-xs text-gray-400">
          Selected: <span className="text-gray-200">{selectedAddr.display_name}</span>
          {" "}&mdash; {(bufferM / 1000).toFixed(1)} km radius
        </p>
      )}
    </div>
  );
}

export default function LandingPage({ mode, onSelectMode, onSelect }: Props) {
  return (
    <div className="relative h-full w-full overflow-hidden bg-gray-950">
      <video
        className="absolute inset-0 h-full w-full object-cover opacity-50"
        autoPlay loop muted playsInline
        poster="https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?w=1920&q=80"
      >
        <source src="https://cdn.coverr.co/videos/coverr-aerial-view-of-city-buildings-1573/1080p.mp4" type="video/mp4" />
      </video>
      <div className="absolute inset-0 bg-gradient-to-b from-gray-950/70 via-gray-950/40 to-gray-950/80" />

      <div className="relative z-10 flex h-full flex-col items-center justify-center px-4">
        <h1 className="mb-2 text-4xl font-bold tracking-tight text-white md:text-5xl">
          Urban Access Analyzer
        </h1>
        <p className="mb-8 max-w-xl text-center text-lg text-gray-300">
          Analyze urban accessibility for transit, schools, and parks.
        </p>

        {/* Mode selector */}
        <div className="mb-8 flex gap-2 rounded-2xl border border-white/10 bg-white/5 p-1.5 backdrop-blur-xl">
          {MODES.map((m) => (
            <button
              key={m.value}
              onClick={() => onSelectMode(m.value)}
              className={`rounded-xl px-5 py-2.5 text-sm font-semibold transition ${
                mode === m.value
                  ? "bg-white/15 text-white shadow"
                  : "text-gray-400 hover:text-gray-200"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
        <p className="mb-6 text-sm text-gray-400">
          {MODES.find((m) => m.value === mode)?.description}
        </p>

        <div className="w-full max-w-3xl space-y-6">
          <CitySearch onSelect={onSelect} />
          <div className="flex items-center gap-4">
            <div className="h-px flex-1 bg-white/10" />
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">or</span>
            <div className="h-px flex-1 bg-white/10" />
          </div>
          <AddressSearch onSelect={onSelect} />
        </div>

        <p className="mt-8 text-sm text-gray-500">
          Powered by OpenStreetMap &middot; WorldPop &middot; H3 &middot; Mobility Database
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
git add frontend/src/components/LandingPage.tsx
git commit -m "feat: add LandingPage with mode selector (Transit default)"
```

---

## Task 13: AnalysisPage

**Files:**
- Create: `frontend/src/components/AnalysisPage.tsx`

- [ ] **Step 1: Write AnalysisPage.tsx**

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/frontend/src/components/AnalysisPage.tsx`:

```typescript
import { useCallback, useEffect, useRef, useState } from "react";
import { fetchCityGeometry, fetchGeocodeGeometry, pollJob, startAnalysis } from "../api";
import type { AnalysisMode, AnalysisResult, AoiSelection } from "../types";
import CityMap from "./CityMap";
import SchoolsControls from "./SchoolsControls";
import ParksControls from "./ParksControls";
import GtfsControls from "./GtfsControls";
import StatsPanel from "./StatsPanel";
import L from "leaflet";

interface Props {
  mode: AnalysisMode;
  aoi: AoiSelection;
  onBack: () => void;
}

// LOS grade legend items
const LOS_LEGEND = [
  { label: "A (best)", color: "bg-[#40916c]" },
  { label: "B",        color: "bg-[#d4ac0d]" },
  { label: "C",        color: "bg-[#fa8246]" },
  { label: "D",        color: "bg-[#b30202]" },
  { label: "E",        color: "bg-[#9b59b6]" },
  { label: "F (worst)", color: "bg-[#0051ff]" },
];

const SCHOOLS_LEGEND = [
  { label: "Walk",     color: "bg-emerald-500" },
  { label: "Bike",     color: "bg-blue-500"    },
  { label: "Bus/Car",  color: "bg-amber-500"   },
];

const PARKS_LEGEND = [
  { label: "Walk", color: "bg-emerald-500" },
];

function geojsonToBbox(geojson: GeoJSON.FeatureCollection): string | null {
  try {
    const layer = L.geoJSON(geojson as GeoJSON.GeoJsonObject);
    const bounds = layer.getBounds();
    if (!bounds.isValid()) return null;
    const sw = bounds.getSouthWest();
    const ne = bounds.getNorthEast();
    return `${sw.lng},${sw.lat},${ne.lng},${ne.lat}`;
  } catch {
    return null;
  }
}

export default function AnalysisPage({ mode, aoi, onBack }: Props) {
  const [aoiGeojson, setAoiGeojson] = useState<GeoJSON.FeatureCollection | null>(null);
  const [aoiBbox, setAoiBbox] = useState<string | null>(null);
  const [loadingAoi, setLoadingAoi] = useState(true);

  // Schools params
  const [distanceWalk, setDistanceWalk] = useState(1000);
  const [distanceBike, setDistanceBike] = useState(2500);
  const [distanceCar, setDistanceCar] = useState(10000);
  const [kidsOnly, setKidsOnly] = useState(false);

  // Parks params
  const [parksWalk, setParksWalk] = useState(500);

  // GTFS params
  const [startHour, setStartHour] = useState(8);
  const [endHour, setEndHour] = useState(20);
  const [selectedFeedIds, setSelectedFeedIds] = useState<string[]>([]);

  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoadingAoi(true);
    setError(null);
    setAoiBbox(null);

    const fetchAoi = async () => {
      try {
        const geojson =
          aoi.kind === "city"
            ? await fetchCityGeometry(aoi.city_name)
            : await fetchGeocodeGeometry(aoi.address, aoi.buffer_m);
        if (!cancelled) {
          setAoiGeojson(geojson);
          setAoiBbox(geojsonToBbox(geojson));
        }
      } catch (e: unknown) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoadingAoi(false);
      }
    };
    fetchAoi();
    return () => { cancelled = true; };
  }, [aoi]);

  const handleRun = useCallback(async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    setProgress("Starting analysis...");

    const aoiParams =
      aoi.kind === "city"
        ? { city_name: aoi.city_name }
        : { address: aoi.address, buffer_m: aoi.buffer_m };

    let modeParams = {};
    if (mode === "schools") {
      modeParams = { distance_walk: distanceWalk, distance_bike: distanceBike, distance_car: distanceCar, kids_only: kidsOnly };
    } else if (mode === "parks") {
      modeParams = { distance_walk: parksWalk };
    } else {
      modeParams = { feed_ids: selectedFeedIds, start_hour: startHour, end_hour: endHour };
    }

    try {
      const jobId = await startAnalysis({ analysis_type: mode, ...aoiParams, ...modeParams });
      pollRef.current = setInterval(async () => {
        try {
          const status = await pollJob(jobId);
          setProgress(status.progress);
          if (status.status === "completed") {
            clearInterval(pollRef.current!);
            setResult(status.result!);
            setRunning(false);
          } else if (status.status === "failed") {
            clearInterval(pollRef.current!);
            setError(status.error ?? "Unknown error");
            setRunning(false);
          }
        } catch {
          clearInterval(pollRef.current!);
          setError("Lost connection to server");
          setRunning(false);
        }
      }, 2000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      setRunning(false);
    }
  }, [aoi, mode, distanceWalk, distanceBike, distanceCar, kidsOnly, parksWalk, startHour, endHour, selectedFeedIds]);

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  const canRun = !running && !loadingAoi && (mode !== "gtfs" || selectedFeedIds.length > 0);
  const legend = mode === "gtfs" ? LOS_LEGEND : mode === "schools" ? SCHOOLS_LEGEND : PARKS_LEGEND;
  const title = aoi.kind === "city" ? aoi.city_name : aoi.address;

  return (
    <div className="flex h-full bg-gray-950 text-white">
      <aside className="flex w-[360px] shrink-0 flex-col gap-5 overflow-y-auto border-r border-white/5 bg-gray-900/60 p-6 backdrop-blur-sm">
        <div>
          <button onClick={onBack} className="mb-3 flex items-center gap-1.5 text-sm text-gray-400 transition hover:text-white">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
            </svg>
            Back
          </button>
          <h2 className="text-lg font-semibold leading-tight">{title}</h2>
          <p className="mt-0.5 text-xs font-semibold uppercase tracking-wider text-gray-500">
            {mode === "gtfs" ? "Transit LOS" : mode === "schools" ? "Schools" : "Parks"}
          </p>
          {loadingAoi && <p className="mt-1 text-sm text-gray-500">Loading geometry...</p>}
        </div>

        {mode === "schools" && (
          <SchoolsControls
            distanceWalk={distanceWalk} distanceBike={distanceBike} distanceCar={distanceCar} kidsOnly={kidsOnly}
            onChangeWalk={setDistanceWalk} onChangeBike={setDistanceBike} onChangeCar={setDistanceCar} onChangeKidsOnly={setKidsOnly}
          />
        )}
        {mode === "parks" && (
          <ParksControls distanceWalk={parksWalk} onChangeWalk={setParksWalk} />
        )}
        {mode === "gtfs" && (
          <GtfsControls
            aoiBbox={aoiBbox}
            startHour={startHour} endHour={endHour}
            selectedFeedIds={selectedFeedIds}
            onChangeStartHour={setStartHour} onChangeEndHour={setEndHour}
            onChangeFeedIds={setSelectedFeedIds}
          />
        )}

        <button
          onClick={handleRun}
          disabled={!canRun}
          className="flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-emerald-900/30 transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {running ? (
            <><div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" /> Running...</>
          ) : (
            <><svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z" /></svg> Run Analysis</>
          )}
        </button>

        {running && (
          <div className="rounded-xl bg-blue-500/10 px-4 py-3 text-sm text-blue-300">
            <div className="mb-1 flex items-center gap-2">
              <div className="h-2 w-2 animate-pulse rounded-full bg-blue-400" />
              <span className="font-medium">Processing</span>
            </div>
            <p className="text-blue-300/80">{progress}</p>
          </div>
        )}

        {error && (
          <div className="rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-300">
            <p className="font-medium">Error</p>
            <p className="mt-1 text-red-300/80">{error}</p>
          </div>
        )}

        {result && <StatsPanel stats={result.stats} />}

        <div className="mt-auto space-y-2 border-t border-white/5 pt-4">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500">Legend</h4>
          {legend.map((item) => (
            <div key={item.label} className="flex items-center gap-2 text-sm text-gray-400">
              <span className={`inline-block h-3 w-3 rounded-sm ${item.color}`} />
              {item.label}
            </div>
          ))}
        </div>
      </aside>

      <main className="relative flex-1 p-3">
        <CityMap aoiGeojson={aoiGeojson} result={result} />
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
git add frontend/src/components/AnalysisPage.tsx
git commit -m "feat: add mode-aware AnalysisPage"
```

---

## Task 14: Wire App.tsx + CSS + main.tsx

**Files:**
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/App.css`
- Create: `frontend/src/index.css`
- Create: `frontend/src/main.tsx`

- [ ] **Step 1: Write App.tsx**

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/frontend/src/App.tsx`:

```typescript
import { useState } from "react";
import LandingPage from "./components/LandingPage";
import AnalysisPage from "./components/AnalysisPage";
import ErrorBoundary from "./components/ErrorBoundary";
import type { AnalysisMode, AoiSelection } from "./types";

export default function App() {
  const [mode, setMode] = useState<AnalysisMode>("gtfs");
  const [aoi, setAoi] = useState<AoiSelection | null>(null);

  if (!aoi) {
    return (
      <LandingPage
        mode={mode}
        onSelectMode={setMode}
        onSelect={setAoi}
      />
    );
  }

  return (
    <ErrorBoundary>
      <AnalysisPage
        mode={mode}
        aoi={aoi}
        onBack={() => setAoi(null)}
      />
    </ErrorBoundary>
  );
}
```

- [ ] **Step 2: Write index.css**

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/frontend/src/index.css`:

```css
@import "tailwindcss";

*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body, #root {
  height: 100%;
  width: 100%;
}
```

- [ ] **Step 3: Write App.css**

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/frontend/src/App.css`:

```css
/* No global App styles needed; Tailwind handles everything. */
```

- [ ] **Step 4: Write main.tsx**

Save to `/home/xabi9/Documents/Sources/UrbanAccessApp/frontend/src/main.tsx`:

```typescript
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

- [ ] **Step 5: Commit**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
git add frontend/src/App.tsx frontend/src/App.css frontend/src/index.css frontend/src/main.tsx
git commit -m "feat: wire App.tsx, main.tsx, and CSS"
```

---

## Task 15: Smoke Test

Verify the app starts and responds end-to-end.

- [ ] **Step 1: Run backend tests**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
uv run pytest tests/ -v
```

Expected: all tests pass (13 tests: 5 utils + 8 api).

- [ ] **Step 2: Start the backend**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
uv run uvicorn backend.main:app --reload --port 7000
```

Expected: `Uvicorn running on http://127.0.0.1:7000`

- [ ] **Step 3: Start the frontend (new terminal)**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp/frontend
npm run dev
```

Expected: `VITE v7.x.x  ready in ... ms` and `Local: http://localhost:5173/`

- [ ] **Step 4: Open the app**

Navigate to `http://localhost:5173/` in a browser.

Expected:
- Landing page loads with city video background
- Transit / Schools / Parks mode toggle visible with **Transit** selected
- City search and address+buffer search are functional (autocomplete works)
- Selecting a city navigates to the AnalysisPage
- In Transit mode, GtfsControls appears with hour inputs and "Loading AOI..." then feed search
- In Schools mode, SchoolsControls shows three sliders + kids toggle
- In Parks mode, ParksControls shows a single walking distance slider

- [ ] **Step 5: Final commit**

```bash
cd /home/xabi9/Documents/Sources/UrbanAccessApp
git add .
git commit -m "chore: verify smoke test passes"
```

---

## Notes

**To activate GTFS analysis** (when `pyGTFSHandler` is added):
1. Add `pyGTFSHandler = { path = "/path/to/pyGTFSHandler" }` under `[tool.uv.sources]` in `pyproject.toml`
2. Add `"pyGTFSHandler"` to `dependencies` in `pyproject.toml`
3. Run `uv sync`
4. Set `MOBILITY_DB_TOKEN=<your_token>` environment variable before starting the backend
5. `PYGTFS_AVAILABLE` in `backend/analysis_gtfs.py` will become `True` automatically

**Output caching:** Results are saved to `output/<city_name>/` to avoid re-downloading on subsequent runs. Delete the folder to force a refresh.

**Backend port:** The backend runs on port `7000`. The frontend Vite dev server proxies `/api` to `http://localhost:7000`. Change `vite.config.ts` if needed.
