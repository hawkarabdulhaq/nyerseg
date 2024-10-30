import geopandas as gpd
import pandas as pd

def process_buffers(shapefiles, buffer_distance):
    # Create buffers for each shapefile
    buffers = [gdf.buffer(buffer_distance) for gdf in shapefiles]

    # Combine all buffers into one GeoSeries
    combined_buffer = gpd.GeoSeries(pd.concat(buffers, ignore_index=True))

    # Set the CRS for combined_buffer
    combined_buffer.crs = "EPSG:23700"

    return combined_buffer

def filter_wells(combined_buffer, newlywells_gdf):
    # Ensure CRS matches
    if combined_buffer.crs != newlywells_gdf.crs:
        combined_buffer = combined_buffer.set_crs(newlywells_gdf.crs, allow_override=True)

    # Check if wells are within the buffer areas
    def is_within_buffers(point):
        return combined_buffer.intersects(point).any()

    # Filter out wells that are within the buffers and create a copy
    filtered_newlywells_gdf = newlywells_gdf[~newlywells_gdf.geometry.apply(is_within_buffers)].copy()

    return filtered_newlywells_gdf
