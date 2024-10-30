import streamlit as st
import folium
import pandas as pd
import geopandas as gpd
from pyproj import Transformer
from shapely.geometry import Point
from streamlit_folium import st_folium
import os

# Set up file paths
BASE_DIR = os.getcwd()  # Assuming current working directory is root of project
wells_dir = os.path.join(BASE_DIR, "wells")
shapefiles_dir = os.path.join(BASE_DIR, "shapefiles")

# Define paths for well data
realwells_path = os.path.join(wells_dir, "realwells.txt")
newlywells_path = os.path.join(wells_dir, "newlywells.txt")

# Define paths for buffer shapefiles
forest_shp_path = os.path.join(shapefiles_dir, "Forest_LandCover_Nyerseg_2019", "Forest_LandCover_Nyerseg_2019.shp")
waterbody_shp_path = os.path.join(shapefiles_dir, "WaterBody_LandCover_Nyerseg_2019", "WaterBody_LandCover_Nyerseg_2019.shp")
wetland_shp_path = os.path.join(shapefiles_dir, "Wetland_LandCover_Nyerseg_2019", "Wetland_LandCover_Nyerseg_2019.shp")

# Define paths for additional shapefiles in nov_kulturak
nov_kulturak_dir = os.path.join(shapefiles_dir, "nov_kulturak")
torma_shp_path = os.path.join(nov_kulturak_dir, "torma.shp")
kukorica_shp_path = os.path.join(nov_kulturak_dir, "kukorica.shp")
dohany1_shp_path = os.path.join(nov_kulturak_dir, "dohany1.shp")
dohany2_shp_path = os.path.join(nov_kulturak_dir, "dohany2.shp")

st.title("Well Location Analysis with Buffer Zones")

st.markdown("""
This application filters new well locations by excluding those within buffer zones of protected areas and displays the results on an interactive map.
""")

# Sidebar buffer input
buffer_distance = st.sidebar.number_input("Buffer Distance (meters)", min_value=0, value=100, step=10)

if st.sidebar.button("Run Analysis"):
    # Load shapefiles
    forest_gdf = gpd.read_file(forest_shp_path).to_crs(epsg=23700)
    waterbody_gdf = gpd.read_file(waterbody_shp_path).to_crs(epsg=23700)
    wetland_gdf = gpd.read_file(wetland_shp_path).to_crs(epsg=23700)
    
    # Create buffers
    forest_buffer = forest_gdf.buffer(buffer_distance)
    waterbody_buffer = waterbody_gdf.buffer(buffer_distance)
    wetland_buffer = wetland_gdf.buffer(buffer_distance)
    
    # Load additional shapefiles and create buffers
    torma_gdf = gpd.read_file(torma_shp_path).to_crs(epsg=23700)
    kukorica_gdf = gpd.read_file(kukorica_shp_path).to_crs(epsg=23700)
    dohany1_gdf = gpd.read_file(dohany1_shp_path).to_crs(epsg=23700)
    dohany2_gdf = gpd.read_file(dohany2_shp_path).to_crs(epsg=23700)
    
    torma_buffer = torma_gdf.buffer(buffer_distance)
    kukorica_buffer = kukorica_gdf.buffer(buffer_distance)
    dohany1_buffer = dohany1_gdf.buffer(buffer_distance)
    dohany2_buffer = dohany2_gdf.buffer(buffer_distance)
    
    # Combine all buffers into one GeoSeries
    combined_buffer = gpd.GeoSeries(pd.concat([
        forest_buffer,
        waterbody_buffer,
        wetland_buffer,
        torma_buffer,
        kukorica_buffer,
        dohany1_buffer,
        dohany2_buffer
    ], ignore_index=True))
    
    # Read the well data
    realwells_df = pd.read_csv(realwells_path, delimiter='\t', header=None, names=['EOV_X', 'EOV_Y'])
    newlywells_df = pd.read_csv(newlywells_path, delimiter='\t', header=None, names=['EOV_X', 'EOV_Y'])
    
    # Initialize the EOV to WGS84 transformer
    transformer = Transformer.from_crs("EPSG:23700", "EPSG:4326", always_xy=True)  # EOV to WGS84
    
    # Function to convert EOV to Lat/Lon
    def eov_to_latlon(eov_x, eov_y):
        lon, lat = transformer.transform(eov_x, eov_y)
        return lat, lon
    
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
    
    # Check if wells are within the buffer areas
    def is_within_buffers(point):
        return combined_buffer.contains(point).any()
    
    # Filter out wells that are within the buffers
    filtered_newlywells_gdf = newlywells_gdf[~newlywells_gdf.geometry.apply(is_within_buffers)]
    
    # Convert filtered coordinates to WGS84
    filtered_newlywells_gdf[['Latitude', 'Longitude']] = filtered_newlywells_gdf.apply(
        lambda row: eov_to_latlon(row.geometry.x, row.geometry.y), axis=1, result_type='expand'
    )
    
    realwells_df[['Latitude', 'Longitude']] = realwells_gdf.apply(
        lambda row: eov_to_latlon(row.geometry.x, row.geometry.y), axis=1, result_type='expand'
    )
    
    # Create a Folium map centered around an average location
    center_lat = (realwells_df['Latitude'].mean() + filtered_newlywells_gdf['Latitude'].mean()) / 2
    center_lon = (realwells_df['Longitude'].mean() + filtered_newlywells_gdf['Longitude'].mean()) / 2
    wells_map = folium.Map(location=[center_lat, center_lon], zoom_start=10)
    
    # Add real wells to the map
    for index, row in realwells_df.iterrows():
        folium.CircleMarker(
            location=(row['Latitude'], row['Longitude']),
            radius=2,
            color='red',
            fill=True,
            fill_color='red',
            fill_opacity=0.6
        ).add_to(wells_map)
    
    # Add filtered new wells to the map
    for index, row in filtered_newlywells_gdf.iterrows():
        folium.CircleMarker(
            location=(row['Latitude'], row['Longitude']),
            radius=2,
            color='blue',
            fill=True,
            fill_color='blue',
            fill_opacity=0.6
        ).add_to(wells_map)
    
    # Display the map in Streamlit
    st.subheader("Filtered Wells Map")
    st_data = st_folium(wells_map, width=700, height=500)
    
    # Prepare the filtered data for download
    filtered_newlywells_df = pd.DataFrame({
        'EOV_X': filtered_newlywells_gdf.geometry.x,
        'EOV_Y': filtered_newlywells_gdf.geometry.y,
        'Latitude': filtered_newlywells_gdf['Latitude'],
        'Longitude': filtered_newlywells_gdf['Longitude']
    })
    
    # Provide download link for the CSV
    csv = filtered_newlywells_df.to_csv(index=False)
    st.subheader("Download Filtered Wells Data")
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name='filtered_newlywells.csv',
        mime='text/csv'
    )
