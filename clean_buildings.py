import geopandas as gpd
import pandas as pd

# ============================================================
# 1. LOAD ZIP POLYGONS
# ============================================================
zip_geo = gpd.read_file("plz-5stellig.geojson")
zip_geo["plz"] = zip_geo["plz"].astype(str)

# Keep Bavaria only
zip_geo = zip_geo[zip_geo["plz"].str.match(r"^(8[0-9]|9[0-7])")].copy()

# ============================================================
# 2. LOAD ALL BAVARIA BUILDING SHAPEFILES
# ============================================================
folders = [
    "mittelfranken-260304-free.shp",
    "niederbayern-260304-free.shp",
    "oberbayern-260304-free.shp",
    "oberfranken-260304-free.shp",
    "oberpfalz-260304-free.shp",
    "schwaben-260304-free.shp",
    "unterfranken-260304-free.shp"
]

gdfs = []

for folder in folders:
    path = f"{folder}/gis_osm_buildings_a_free_1.shp"
    print(f"Loading: {path}")
    gdf = gpd.read_file(path)
    gdf["source_region"] = folder
    gdfs.append(gdf)

buildings = pd.concat(gdfs, ignore_index=True)

print("Total raw buildings:", len(buildings))
print("Columns:", buildings.columns.tolist())

# ============================================================
# 3. CLEAN GEOMETRY
# ============================================================
buildings = buildings[buildings.geometry.notna()].copy()
buildings = buildings[~buildings.geometry.is_empty].copy()
buildings = buildings[buildings.is_valid].copy()

print("After geometry cleaning:", len(buildings))

# ============================================================
# 4. REMOVE DUPLICATES
# ============================================================
buildings["geom_wkt"] = buildings.geometry.to_wkt()
buildings = buildings.drop_duplicates(subset="geom_wkt").copy()
buildings = buildings.drop(columns="geom_wkt")

print("After duplicate removal:", len(buildings))

# ============================================================
# 5. CALCULATE FOOTPRINT AREA
# ============================================================
buildings = buildings.to_crs(epsg=3857)
buildings["roof_m2"] = buildings.geometry.area

print("\nRaw roof area stats:")
print(buildings["roof_m2"].describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]))

# ============================================================
# 6. FILTER TO REALISTIC RESIDENTIAL-LIKE BUILDINGS
# ============================================================
buildings = buildings[
    (buildings["roof_m2"] >= 50) &
    (buildings["roof_m2"] <= 300)
].copy()

print("After residential-like area filter:", len(buildings))
print(buildings["roof_m2"].describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]))

# ============================================================
# 7. PREP ZIP POLYGONS
# ============================================================
zip_geo = zip_geo.to_crs(epsg=3857)
zip_geo["area_km2"] = zip_geo.geometry.area / 1e6

# ============================================================
# 8. SPATIAL JOIN BUILDINGS TO ZIPS
# ============================================================
joined = gpd.sjoin(
    buildings,
    zip_geo[["plz", "geometry", "area_km2"]],
    how="inner",
    predicate="intersects"
)

print("Joined rows:", len(joined))

# ============================================================
# 9. AGGREGATE BY ZIP
# ============================================================
summary = joined.groupby("plz").agg(
    building_count=("roof_m2", "count"),
    total_roof_m2=("roof_m2", "sum"),
    avg_roof_m2=("roof_m2", "mean"),
    area_km2=("area_km2", "first")
).reset_index()

summary["buildings_per_km2"] = summary["building_count"] / summary["area_km2"]

# ============================================================
# 10. SAVE CLEAN CSV
# ============================================================
summary.to_csv("bavaria_zip_summary_clean.csv", index=False)

print("\nSaved: bavaria_zip_summary_clean.csv")
print(summary.head())

# ============================================================
# 11. OPTIONAL CHECK FOR SPECIFIC ZIP
# ============================================================
check_plz = "97833"
check_row = summary[summary["plz"] == check_plz]

if not check_row.empty:
    print(f"\nCheck PLZ {check_plz}:")
    print(check_row.to_string(index=False))
else:
    print(f"\nPLZ {check_plz} not found in summary.")