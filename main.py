import geopandas as gpd
import pandas as pd
import plotly.express as px

# ============================================================
# 1. LOAD ZIP POLYGONS
# ============================================================
zip_geo = gpd.read_file("plz-5stellig.geojson")
zip_geo["plz"] = zip_geo["plz"].astype(str)

# Keep Bavaria only
zip_geo = zip_geo[zip_geo["plz"].str.match(r"^(8[0-9]|9[0-7])")].copy()

# ============================================================
# 2. LOAD CLEAN DATA
# ============================================================
score_df = pd.read_csv("bavaria_zip_summary_clean.csv")
score_df["plz"] = score_df["plz"].astype(str)

# ============================================================
# 3. FINAL SCORE (SIMPLE + IMPROVED WEIGHTS)
# ============================================================

# Normalize components
score_df["avg_roof_component"] = score_df["avg_roof_m2"] / score_df["avg_roof_m2"].max()
score_df["density_component"] = score_df["buildings_per_km2"] / score_df["buildings_per_km2"].max()
score_df["total_roof_component"] = score_df["total_roof_m2"] / score_df["total_roof_m2"].max()

# Scale component
score_df["scale_component"] = score_df["building_count"] / score_df["building_count"].max()
score_df["scale_component"] = score_df["scale_component"] ** 0.5

# Final weighted score (your simplified version)
score_df["final_score"] = (
    0.40 * score_df["avg_roof_component"] +
    0.35 * (1 - score_df["density_component"]) +
    0.10 * score_df["total_roof_component"] +
    0.15 * score_df["scale_component"]
)

# Sort and save
score_df = score_df.sort_values("final_score", ascending=False)
score_df.to_csv("bavaria_zip_summary_with_final_score.csv", index=False)

# ============================================================
# 4. MERGE WITH GEOMETRY
# ============================================================
map_df = zip_geo.merge(score_df, on="plz", how="left")

print("ZIP polygons loaded:", len(zip_geo))
print("Mapped rows:", len(map_df))
print("ZIPs with score:", map_df["final_score"].notna().sum())

# Convert CRS for mapbox
map_df = map_df.to_crs(epsg=4326)
geojson = map_df.__geo_interface__

# ============================================================
# 5. CHOROPLETH MAP (RED → YELLOW → GREEN)
# ============================================================
fig = px.choropleth_mapbox(
    map_df,
    geojson=geojson,
    locations="plz",
    featureidkey="properties.plz",
    color="final_score",
    color_continuous_scale="RdYlGn",
    range_color=(0.5, 0.85),
    hover_name="plz",
    hover_data={
        "building_count": ":,",
        "total_roof_m2": ":,.0f",
        "avg_roof_m2": ":.1f",
        "buildings_per_km2": ":.1f",
        "final_score": ":.3f",
        "plz": False
    },
    mapbox_style="carto-positron",
    zoom=6.3,
    center={"lat": 48.9, "lon": 11.5},
    opacity=0.78,
    title="Bavaria Residential Solar Opportunity Map"
)

fig.update_layout(
    width=1250,
    height=850,
    margin={"r": 0, "t": 60, "l": 0, "b": 0}
)

fig.show()

fig.write_html("bavaria_zip_final_score_map_updated.html")

print("Saved: bavaria_zip_final_score_map_updated.html")
print("Saved: bavaria_zip_summary_with_final_score.csv")