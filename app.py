import streamlit as st
import folium
import pandas as pd
from streamlit_folium import st_folium
from load_data import load_shapefile_with_crs, load_well_data
from process_data import create_buffers, filter_wells, convert_coordinates
import os

st.title("Well Location Analysis with Buffer Zones")

st.markdown("""
This application filters new well locations by excluding those within buffer zones of protected areas and displays the results on an interactive map.
""")

# Set up file paths
BASE_DIR = os.getcwd()
wells_dir = os.path.join(BASE_DIR, "wells")
shapefiles_dir = os.path.join(BASE_DIR, "shapefiles")

# Define paths for well data
realwells_path = os.path.join(wells_dir, "realwells.txt")
newlywells_path = os.path.join(wells_dir, "newlywells.txt")

# Define paths for buffer shapefiles
forest_shp_path = os.path.join(shapefiles_dir, "Forest_LandCover_Nyerseg_2019", "Forest_LandCover_Nyerseg_2019.shp")
waterbody_shp_path = os.path.join(shapefiles_dir, "WaterBody_LandCover_Nyerseg_2019", "WaterBody_LandCover_Nyerseg_2019.shp")
wetland_shp_path = os.path.join(shapefiles_dir, "Wetland_LandCover_Nyerseg_2019", "Wetland_LandCover_Nyerseg_2019.shp")
torma_shp_path = os.path.join(shapefiles_dir, "nov_kulturak", "torma.shp")
kukorica_shp_path = os.path.join(shapefiles_dir, "nov_kulturak", "kukorica.shp")
dohany1_shp_path = os.path.join(shapefiles_dir, "nov_kulturak", "dohany1.shp")
dohany2_shp_path = os.path.join(shapefiles_dir, "nov_kulturak", "dohany2.shp")

# Sidebar buffer input
buffer_distance = st.sidebar.number_input("Buffer Distance (meters)", min_value=0, value=50, step=10)

if st.sidebar.button("Run Analysis") or 'filtered_data' not in st.session_state:
    # Load shapefiles
    forest_gdf = load_shapefile_with_crs(forest_shp_path)
    waterbody_gdf = load_shapefile_with_crs(waterbody_shp_path)
    wetland_gdf = load_shapefile_with_crs(wetland_shp_path)
    torma_gdf = load_shapefile_with_crs(torma_shp_path)
    kukorica_gdf = load_shapefile_with_crs(kukorica_shp_path)
    dohany1_gdf = load_shapefile_with_crs(dohany1_shp_path)
    dohany2_gdf = load_shapefile_with_crs(dohany2_shp_path)
    
    # Create buffers
    combined_buffer = create_buffers([
        forest_gdf, waterbody_gdf, wetland_gdf, torma_gdf, kukorica_gdf, dohany1_gdf, dohany2_gdf
    ], buffer_distance)
    
    # Load and prepare well data
    realwells_gdf, newlywells_gdf = load_well_data(realwells_path, newlywells_path)
    
    # Filter newly wells within buffers
    filtered_newlywells_gdf = filter_wells(newlywells_gdf, combined_buffer)
    
    if filtered_newlywells_gdf.empty:
        st.warning("No wells remain after filtering. Adjust the buffer distance or check your data.")
        st.stop()

    # Convert coordinates to WGS84 for visualization
    realwells_gdf, filtered_newlywells_gdf = convert_coordinates(realwells_gdf, filtered_newlywells_gdf)

    # Create a Folium map centered around an average location
    center_lat = (realwells_gdf['Latitude'].mean() + filtered_newlywells_gdf['Latitude'].mean()) / 2
    center_lon = (realwells_gdf['Longitude'].mean() + filtered_newlywells_gdf['Longitude'].mean()) / 2
    wells_map = folium.Map(location=[center_lat, center_lon], zoom_start=10)

    # Add real wells and filtered new wells to the map
    for index, row in realwells_gdf.iterrows():
        folium.CircleMarker(
            location=(row['Latitude'], row['Longitude']),
            radius=2,
            color='red',
            fill=True,
            fill_opacity=0.6
        ).add_to(wells_map)

    for index, row in filtered_newlywells_gdf.iterrows():
        folium.CircleMarker(
            location=(row['Latitude'], row['Longitude']),
            radius=2,
            color='blue',
            fill=True,
            fill_opacity=0.6
        ).add_to(wells_map)

    # Save filtered data and map in session state
    st.session_state['filtered_data'] = filtered_newlywells_gdf[['EOV_X', 'EOV_Y', 'Latitude', 'Longitude']]
    st.session_state['map'] = wells_map

# Display the map if it exists in session state
if 'map' in st.session_state:
    st.subheader("Filtered Wells Map")
    st_folium(st.session_state['map'], width=700, height=500)

# Download button for CSV data
if 'filtered_data' in st.session_state:
    csv = st.session_state['filtered_data'].to_csv(index=False)
    st.subheader("Download Filtered Wells Data")
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name='filtered_newlywells.csv',
        mime='text/csv'
    )
