"""Compute walking-distance accessibility to candidate bike-share stations
for San Sebastian.

For each station layout geojson in ``examples/Stations/``, snaps the station
centroids onto the San Sebastian street network, runs Dijkstra isochrones at
100m intervals from 100m to 800m, aggregates the result into H3 r10 hexagons,
and writes one geojson per input to ``examples/Stations/output/``.

The base street graph is built once and cached — each station file only
pays for the POI snap + isochrone + H3 steps.
"""

import os
import glob

import geopandas as gpd
import osmnx as ox

import UrbanAccessAnalyzer.isochrones as isochrones
import UrbanAccessAnalyzer.graph_processing as graph_processing
import UrbanAccessAnalyzer.osm as osm
import UrbanAccessAnalyzer.utils as utils
import UrbanAccessAnalyzer.h3_utils as h3_utils


CITY_NAME = "Donostia, Gipuzkoa, Spain"
STATIONS_DIR = os.path.join(os.path.dirname(__file__), "Stations")
OUTPUT_DIR = os.path.join(STATIONS_DIR, "output")
PBF_CACHE_DIR = os.path.join(os.path.dirname(__file__), "output")

DISTANCE_STEPS = [100, 200, 300, 400, 500, 600, 700, 800]
# Labels are strings with a non-numeric suffix on purpose:
#  - `__exact_isochrones` matches column names via `str in accessibility_values`,
#    which fails if the labels are ints (str "100" != int 100).
#  - A later `astype(float)` cast on the edges column would silently turn
#    numeric-looking strings ("100") into floats ("100.0"), breaking the
#    value_order match inside `h3_utils.aggregate`. "100m" fails that cast
#    (caught by an `except`) and stays as a string end-to-end.
ACCESSIBILITY_VALUES = [f"{d}m" for d in DISTANCE_STEPS]
MIN_EDGE_LENGTH = 30
H3_RESOLUTION = 10
DOWNLOAD_BUFFER = max(DISTANCE_STEPS)  # avoid border effects at the edge of the AOI


def build_aoi():
    aoi = utils.get_city_geometry(CITY_NAME)
    aoi = gpd.GeoDataFrame(geometry=[aoi.union_all()], crs=aoi.crs)
    aoi = aoi.to_crs(aoi.estimate_utm_crs())
    aoi_download = gpd.GeoDataFrame(geometry=aoi.buffer(DOWNLOAD_BUFFER), crs=aoi.crs)
    return aoi, aoi_download


def build_or_load_graph(aoi, aoi_download, graph_path, osm_xml_path):
    if os.path.isfile(graph_path):
        print(f"Loading cached simplified graph from {graph_path}")
        return ox.load_graphml(graph_path)

    print("Building street graph (one-time setup)...")
    network_filter = osm.osmium_network_filter("walk+bike+primary")
    osm.geofabrik_to_osm(
        osm_xml_path,
        input_file=PBF_CACHE_DIR,
        aoi=aoi_download,
        osmium_filter_args=network_filter,
        overwrite=False,
    )

    G = ox.graph_from_xml(osm_xml_path)
    G = ox.project_graph(G, to_crs=aoi.estimate_utm_crs())
    G = graph_processing.simplify_graph(
        G,
        min_edge_length=MIN_EDGE_LENGTH,
        min_edge_separation=MIN_EDGE_LENGTH * 2,
        undirected=True,
    )
    ox.save_graphml(G, graph_path)
    return G


def accessibility_for_stations(station_path, aoi, graph_path):
    stem = os.path.splitext(os.path.basename(station_path))[0]
    output_path = os.path.join(OUTPUT_DIR, f"{stem}_access.geojson")

    poi = gpd.read_file(station_path).to_crs(aoi.crs)
    poi = gpd.GeoDataFrame(poi.drop(columns="geometry"), geometry=poi.geometry.centroid, crs=aoi.crs)
    poi = poi[poi.geometry.intersects(aoi.union_all())]
    if poi.empty:
        print(f"  {stem}: no stations intersect AOI — skipping")
        return

    # Reload the base graph every iteration so add_points_to_graph doesn't
    # accumulate nodes from previous station files.
    G = ox.load_graphml(graph_path)

    G, osmids = graph_processing.add_points_to_graph(
        poi,
        G,
        max_dist=100 + MIN_EDGE_LENGTH,
        min_edge_length=MIN_EDGE_LENGTH,
    )
    poi["osmid"] = osmids

    access_graph = isochrones.graph(
        G,
        poi,
        DISTANCE_STEPS,
        poi_quality_col=None,
        accessibility_values=ACCESSIBILITY_VALUES,
        min_edge_length=MIN_EDGE_LENGTH,
    )
    _, access_edges = ox.graph_to_gdfs(access_graph)

    access_h3 = h3_utils.from_gdf(
        access_edges,
        resolution=H3_RESOLUTION,
        columns=["accessibility"],
        value_order=ACCESSIBILITY_VALUES,
        contain="overlap",
        method="min",
        buffer=10,
    )

    out = h3_utils.to_gdf(access_h3).to_crs(aoi.crs)
    out = out[out.intersects(aoi.union_all())]
    out = out.to_crs("EPSG:4326")
    out.to_file(output_path, driver="GeoJSON")
    print(f"  {stem}: {len(out)} hexagons -> {output_path}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(PBF_CACHE_DIR, exist_ok=True)

    graph_path = os.path.join(OUTPUT_DIR, "streets_simplified.graphml")
    osm_xml_path = os.path.join(OUTPUT_DIR, "streets.osm")

    aoi, aoi_download = build_aoi()
    build_or_load_graph(aoi, aoi_download, graph_path, osm_xml_path)

    station_files = sorted(glob.glob(os.path.join(STATIONS_DIR, "stations_*.geojson")))
    print(f"Found {len(station_files)} station files")

    for i, path in enumerate(station_files, 1):
        print(f"[{i}/{len(station_files)}] {os.path.basename(path)}")
        accessibility_for_stations(path, aoi, graph_path)


if __name__ == "__main__":
    main()
