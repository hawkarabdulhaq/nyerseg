import geopandas as gpd
import pandas as pd
from pyproj import Transformer

def create_buffers(gdf_list, buffer_distance):
    buffers = [gdf.buffer(buffer_distance) for gdf in gdf_list]
    combined_buffer = gpd.GeoSeries(pd.concat(buffers, ignore_index=True))
    combined_buffer.crs = "EPSG:23700"
    return combined_buffer

def filter_wells(wells_gdf, combined_buffer):
    def is_within_buffers(point):
        return combined_buffer.intersects(point).any()
    return wells_gdf[~wells_gdf.geometry.apply(is_within_buffers)].copy()

def convert_coordinates(realwells_gdf, newlywells_gdf):
    transformer = Transformer.from_crs("EPSG:23700", "EPSG:4326", always_xy=True)

    def eov_to_latlon(eov_x, eov_y):
        lat, lon = transformer.transform(eov_x, eov_y)
        return pd.Series({'Latitude': lat, 'Longitude': lon})

    realwells_gdf[['Latitude', 'Longitude']] = realwells_gdf.apply(
        lambda row: eov_to_latlon(row.geometry.x, row.geometry.y), axis=1
    )
    
    newlywells_gdf[['Latitude', 'Longitude']] = newlywells_gdf.apply(
        lambda row: eov_to_latlon(row.geometry.x, row.geometry.y), axis=1
    )
    
    return realwells_gdf, newlywells_gdf
