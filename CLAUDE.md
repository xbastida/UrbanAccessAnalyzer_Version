# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**UrbanAccessAnalyzer** is a Python library for computing geospatial accessibility isochrones. Given an Area of Interest (AOI) and a set of Points of Interest (POIs), it builds a street network graph, computes shortest-path distances from POIs outward, assigns accessibility scores to each street edge/node, and aggregates results into H3 hexagons or rasters with optional population overlays.

The library is consumed by external web applications (e.g. `Accessibility_tool_rural`) — it is not a standalone app. The primary interfaces are Python functions imported directly; there is no CLI.

## Installation

```bash
# Install with all common extras
pip install -e ".[osm,h3,plot,census,dev]"

# System dependency needed for OSM network downloads
# osmium-tool must be installed separately (e.g. apt install osmium-tool)
```

## Linting & Formatting

```bash
ruff check .          # lint
ruff format .         # format
pre-commit run --all-files   # run all pre-commit hooks (ruff only)
```

No test suite currently exists (`pytest` is listed as a dev dependency but there are no test files).

## Architecture

### Core Pipeline

The typical analysis flow is:

1. **AOI & POIs** — caller provides a GeoDataFrame AOI; POIs are fetched from OSM Overpass API (`osm.overpass_api_query`) or loaded from file
2. **Street network** — `osm.geofabrik_to_osm()` clips a Geofabrik PBF download to the AOI, then `ox.graph_from_xml()` builds a NetworkX/OSMnx graph; `graph_processing.simplify_graph()` cleans short edges
3. **POIs injected into graph** — `graph_processing.add_points_to_graph()` snaps POI centroids onto the nearest edge
4. **Isochrones** — `isochrones.graph()` runs Dijkstra from each POI node and annotates every reachable edge with an accessibility value (distance band or quality score); returns an augmented NetworkX graph
5. **H3 aggregation** — `h3_utils.from_gdf()` rasterizes accessibility edges into Uber H3 hexagons at a chosen resolution (typically 10)
6. **Population overlay** — `population.download_worldpop_population()` fetches a WorldPop 100m GeoTIFF; `h3_utils.from_raster()` converts it to H3; merged with accessibility H3 for coverage statistics

### Module Responsibilities

| Module | Role |
|--------|------|
| `osm.py` | Overpass queries, Geofabrik PBF download/clip via osmium, `green_areas()` for parks |
| `graph_processing.py` | OSMnx graph construction, simplification, POI snapping (`add_points_to_graph`) |
| `isochrones.py` | Core Dijkstra-based accessibility computation; `isochrones.graph()` is the main entry point |
| `h3_utils.py` | Rasterize GeoDataFrames and rasters into H3 cells; `from_gdf()`, `from_raster()`, `to_gdf()` |
| `poi_utils.py` | Quality scoring — `quality_by_area()` (parks), `quality_by_values()`, `polygons_to_points()` |
| `population.py` | WorldPop download, US Census helpers, level-of-service difference calculations |
| `quality.py` | Elasticity-based quality functions and calibration |
| `raster_utils.py` | COG creation, raster clipping/merging, CRS validation |
| `geometry_utils.py` | Geodesic area, UTM zone checks, bulk intersection helpers |
| `utils.py` | `get_city_geometry()` (Nominatim), `geocode()`, fuzzy matching |
| `configs.py` | Global path constants (`PBF_OSM_PATH`, `WORLDPOP_PATH`, etc.) — set these before use |
| `scripts/workflow_functions.py` | `process_with_quality_matrix()` — higher-level pipeline that wraps graph + isochrone + H3 steps |

### Key Design Decisions

- **CRS discipline**: AOI and graph are always projected to UTM (via `estimate_utm_crs()`) for metric distance calculations; results are re-projected to EPSG:4326 only for output/display.
- **Distance matrix vs quality matrix**: `isochrones.graph()` accepts either a flat list of distance thresholds (simple bands) or a 2D quality×distance matrix for elasticity-based scoring. `isochrones.default_distance_matrix()` builds a diagonal matrix from POI quality values and distance steps.
- **Caching pattern**: Downstream apps are responsible for caching (saving/loading `.graphml`, `.gpkg`, `.tif` files). The library itself is stateless.
- **H3 resolution 10** ≈ 65m edge length — the standard resolution used in examples and the schools webapp.
- **`configs.py` globals**: `PBF_OSM_PATH` and `WORLDPOP_PATH` can point to a shared local cache of downloaded files to avoid re-downloading across runs.

### External Data Sources

- **OpenStreetMap** via Geofabrik (PBF) and Overpass API
- **WorldPop** (100m population rasters, downloaded on demand)
- **Nominatim** for geocoding / city boundary queries
- **US Census** via `pygris` (LODES RAC/WAC, ACS, Decennial) — in `census/us_census.py`
