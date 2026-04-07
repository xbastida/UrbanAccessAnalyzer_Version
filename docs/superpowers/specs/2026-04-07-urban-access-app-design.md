# UrbanAccessApp — Design Spec

**Date:** 2026-04-07
**Status:** Approved

## Overview

A new standalone web app (`UrbanAccessApp`) that exposes three accessibility analysis modes — Transit (GTFS), Schools, and Parks — over a shared React + FastAPI interface. It is separate from `Accessibility_tool_rural` but reuses its proven patterns and the `UrbanAccessAnalyzer` library.

Transit is the default mode on load.

---

## Architecture

Single repo with a FastAPI backend and a React/Vite/TypeScript frontend.

```
UrbanAccessApp/
├── backend/
│   ├── main.py              # FastAPI app, job queue, all endpoints
│   ├── analysis_schools.py  # Schools pipeline (ported from Accessibility_tool_rural)
│   ├── analysis_parks.py    # Parks pipeline
│   ├── analysis_gtfs.py     # GTFS transit LOS pipeline
│   └── utils.py             # geocode, gdf_to_geojson, sanitize_filename
├── frontend/
│   └── src/
│       ├── App.tsx
│       ├── types.ts
│       ├── api.ts
│       └── components/
│           ├── LandingPage.tsx       # Mode selector (default: Transit) + AOI input
│           ├── AnalysisPage.tsx      # Shared shell: polling, map, stats
│           ├── CityMap.tsx           # Shared map component
│           ├── StatsPanel.tsx        # Shared stats panel
│           ├── SchoolsControls.tsx   # Walk/bike/car sliders + kids toggle
│           ├── ParksControls.tsx     # Walking distance slider
│           └── GtfsControls.tsx      # Hour range + GTFS feed picker
└── pyproject.toml
```

---

## Data Flow

1. User selects mode (default: Transit) and AOI (city name or address + buffer radius) on LandingPage
2. AnalysisPage loads and previews the AOI boundary on the map
3. User sets mode-specific parameters in the side panel
4. For GTFS: AOI confirmation triggers `/api/gtfs-feeds` fetch — available feeds shown as a checkbox list before running
5. User hits Run → POST `/api/analyze` → job created, runs in background thread
6. Frontend polls `/api/job/{job_id}` every 2s → shows progress message
7. On completion: H3 hexagons, POI dots, AOI outline rendered on map; stats panel populated

---

## Backend Pipelines

All three functions share the contract:
```python
run_*_analysis(aoi_params, mode_params, progress_callback) -> dict
# Returns: {aoi, pois, hexagons, edges, stats} as GeoJSON dicts
```

### Schools
Direct port of `Accessibility_tool_rural/backend/analysis.py`.
- POIs: OSM Overpass query for `amenity=school`
- Pipeline: street graph → Dijkstra isochrones → H3 (res 10) → WorldPop population overlay
- Parameters: `distance_walk`, `distance_bike`, `distance_car`, `kids_only`
- Output colors: walk < bike < car accessibility bands

### Parks
Same pipeline structure as Schools.
- POIs: `osm.green_areas()` returns park polygons → `poi_utils.polygons_to_points()` converts to entry points
- Parameters: `distance_walk` only (parks are a walking amenity)
- Single accessibility band: reachable within walking distance or not
- Population overlay same as Schools

### GTFS Transit
Different pipeline using `pyGTFSHandler` (added as dependency when available).
1. `/api/gtfs-feeds` endpoint: `MobilityDatabaseClient` searches feeds by AOI bounding box; returns list of available feeds
2. `run_gtfs_analysis`: loads selected feed(s) via `Feed`, runs `processing_helper` to compute service intensity per stop for the given hour range and date
3. Stops become POIs; `isochrones.graph()` computes walking catchment from each stop
4. LOS grade (A1–F) assigned per H3 hex using the density×frequency matrix from `streamlit_app.py`
5. Population overlay same as other modes
- Parameters: `feed_ids` (list), `start_hour`, `end_hour`, `distance_walk`, `analysis_date` (ISO date string, defaults to today)

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/suggestions?q=` | Nominatim autocomplete |
| POST | `/api/city-geometry` | AOI boundary for a city name |
| POST | `/api/geocode-geometry` | AOI boundary for address + buffer |
| GET | `/api/gtfs-feeds?bbox=` | Available GTFS feeds for AOI (Mobility Database) |
| POST | `/api/analyze` | Start analysis job, returns `job_id` |
| GET | `/api/job/{job_id}` | Poll job status/result |

`/api/analyze` request body:
```json
{
  "analysis_type": "gtfs" | "schools" | "parks",
  "city_name": "...",       // or address + buffer_m
  "address": "...",
  "buffer_m": 5000,
  // Schools/Parks:
  "distance_walk": 1000,
  "distance_bike": 2500,
  "distance_car": 10000,
  "kids_only": false,
  // GTFS:
  "feed_ids": ["..."],
  "start_hour": 8,
  "end_hour": 20,
  "analysis_date": "2026-04-07"   // defaults to today
}
```

---

## Frontend Components

### LandingPage
- Mode toggle at the top: **Transit** (default) | Schools | Parks
- AOI input below (unchanged from Accessibility_tool_rural): city name autocomplete or address + buffer slider

### AnalysisPage
Shared shell identical in structure to Accessibility_tool_rural's AnalysisPage:
- AOI boundary preview on map while parameters are set
- Side panel with mode-specific controls
- Run button, progress message, error display
- On completion: map + stats

### Mode Control Panels
- **SchoolsControls**: walk/bike/car distance sliders + kids-only toggle (ported as-is)
- **ParksControls**: single walking distance slider
- **GtfsControls**: hour range pickers (start/end); after AOI loads, fetches available feeds and shows a checkbox list; user selects feed(s) before running

### CityMap
Reused unchanged. H3 hexagons colored by:
- Schools/Parks: accessibility band (walk → bike → car, green to red)
- GTFS: LOS grade A1–F using the GRADE_COLOR_MAP from `streamlit_app.py` (green A → yellow B → orange C → red D → purple E → blue F)

### StatsPanel
Reused unchanged. Shows population count + percentage per accessibility band or LOS grade.

---

## Key Types (TypeScript)

```typescript
type AnalysisMode = "gtfs" | "schools" | "parks";

interface AnalysisRequest {
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
}

// AnalysisResult shape is unchanged from Accessibility_tool_rural
interface AnalysisResult {
  aoi: GeoJSON.FeatureCollection;
  pois: GeoJSON.FeatureCollection;
  hexagons: GeoJSON.FeatureCollection;
  edges: GeoJSON.FeatureCollection;
  stats: StatsRow[];
}
```

---

## Dependencies

**Backend:**
- `UrbanAccessAnalyzer` (local, editable install)
- `pyGTFSHandler` (local, to be added)
- `fastapi`, `uvicorn`, `pydantic`
- Same geo stack as Accessibility_tool_rural

**Frontend:**
- React + Vite + TypeScript
- Same map/UI libraries as Accessibility_tool_rural

---

## Out of Scope

- User authentication
- Persistent job storage (in-memory dict, same as Accessibility_tool_rural)
- Raster output / COG export
- US Census integration
