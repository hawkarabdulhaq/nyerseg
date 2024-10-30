import geopandas as gpd
import pandas as pd

def load_shapefile_with_crs(filepath, target_crs="EPSG:23700"):
    gdf = gpd.read_file(filepath)
    if gdf.crs is None:
        # Set the initial CRS if it's missing
        gdf.set_crs(epsg=23700, inplace=True)
    gdf = gdf.to_crs(target_crs)
    return gdf

def load_shapefiles(shapefile_paths):
    shapefiles = [load_shapefile_with_crs(path) for path in shapefile_paths]
    return shapefiles

def load_well_data(realwells_path, newlywells_path):
    # Read the well data
    realwells_df = pd.read_csv(realwells_path, delimiter='\t', header=None, names=['EOV_X', 'EOV_Y'])
    newlywells_df = pd.read_csv(newlywells_path, delimiter='\t', header=None, names=['EOV_X', 'EOV_Y'])

    # Convert coordinates and create GeoDataFrames
    realwells_gdf = gpd.GeoDataFrame(
        realwells_df,
        geometry=gpd.points_from_xy(realwells_df.EOV_X, realwells_df.EOV_Y),
        crs="EPSG:23700"
    )

    newlywells_gdf = gpd.GeoDataFrame(
        newlywells_df,
        geometry=gpd.points_from_xy(newlywells_df.EOV_X, newlywells_df.EOV_Y),
        crs="EPSG:23700"
    )

    return realwells_gdf, newlywells_gdf
