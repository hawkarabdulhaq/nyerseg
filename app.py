import streamlit as st
import folium
import pandas as pd
import geopandas as gpd
from pyproj import Transformer
from shapely.geometry import Point
from streamlit_folium import st_folium
import os

st.title("Well Location Analysis with Buffer Zones")

st.markdown("""
This application filters new well locations by excluding those within buffer zones of protected areas and displays the results on an interactive map.
""")

# Sidebar inputs
st.sidebar.header("Data Files")

# File inputs
realwells_file = st.sidebar.file_uploader("Upload Real Wells File", type=['txt', 'csv'])
newlywells_file = st.sidebar.file_uploader("Upload Newly Wells File", type=['txt', 'csv'])

st.sidebar.header("Shapefiles for Buffer Zones")
forest_shp_file = st.sidebar.file_uploader("Upload Forest Shapefile", type=['shp'])
waterbody_shp_file = st.sidebar.file_uploader("Upload Waterbody Shapefile", type=['shp'])
wetland_shp_file = st.sidebar.file_uploader("Upload Wetland Shapefile", type=['shp'])

st.sidebar.subheader("Additional Shapefiles")
torma_shp_file = st.sidebar.file_uploader("Upload Torma Shapefile", type=['shp'])
kukorica_shp_file = st.sidebar.file_uploader("Upload Kukorica Shapefile", type=['shp'])
dohany2_shp_file = st.sidebar.file_uploader("Upload Dohany2 Shapefile", type=['shp'])
dohany1_shp_file = st.sidebar.file_uploader("Upload Dohany1 Shapefile", type=['shp'])

buffer_distance = st.sidebar.number_input("Buffer Distance (meters)", min_value=0, value=100, step=10)

# Function to read shapefile from uploaded files
def load_shapefile(uploaded_file):
    if uploaded_file:
        # Streamlit uploads files as a BytesIO object, which GeoPandas can read
        shapefile = gpd.read_file(uploaded_file)
        return shapefile
    else:
        return None

if st.sidebar.button("Run Analysis"):
    if not all([realwells_file, newlywells_file, forest_shp_file, waterbody_shp_file, wetland_shp_file]):
        st.error("Please upload all the required files.")
    else:
        # Load shapefiles
        forest_gdf = load_shapefile(forest_shp_file).to_crs(epsg=23700)
        waterbody_gdf = load_shapefile(waterbody_shp_file).to_crs(epsg=23700)
        wetland_gdf = load_shapefile(wetland_shp_file).to_crs(epsg=23700)
        
        # Create buffers
        forest_buffer = forest_gdf.buffer(buffer_distance)
        waterbody_buffer = waterbody_gdf.buffer(buffer_distance)
        wetland_buffer = wetland_gdf.buffer(buffer_distance)
        
        # Load additional shapefiles and create buffers if provided
        buffers = [forest_buffer, waterbody_buffer, wetland_buffer]
        
        additional_shapefiles = {
            'torma': torma_shp_file,
            'kukorica': kukorica_shp_file,
            'dohany2': dohany2_shp_file,
            'dohany1': dohany1_shp_file
        }
        
        for name, shp_file in additional_shapefiles.items():
            if shp_file:
                shp_gdf = load_shapefile(shp_file).to_crs(epsg=23700)
                shp_buffer = shp_gdf.buffer(buffer_distance)
                buffers.append(shp_buffer)
        
        # Combine all buffers into one GeoSeries
        combined_buffer = gpd.GeoSeries(pd.concat(buffers, ignore_index=True))
        
        # Read the well data
        realwells_df = pd.read_csv(realwells_file, delimiter='\t', header=None, names=['EOV_X', 'EOV_Y'])
        newlywells_df = pd.read_csv(newlywells_file, delimiter='\t', header=None, names=['EOV_X', 'EOV_Y'])
        
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
