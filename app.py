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

# Directory structure
data_dir = "data/"
wells_dir = os.path.join(data_dir, "wells/")
shapefiles_dir = os.path.join(data_dir, "shapefiles/")

# File paths for wells data
realwells_path = os.path.join(wells_dir, "realwells.txt")
newlywells_path = os.path.join(wells_dir, "newlywells.txt")

# File paths for shapefiles
forest_shp_path = os.path.join(shapefiles_dir, "Forest_LandCover_Nyerseg_2019/Forest_LandCover_Nyerseg_2019.shp")
waterbody_shp_path = os.path.join(shapefiles_dir, "WaterBody_LandCover_Nyerseg_2019/WaterBody_LandCover_Nyerseg_2019.shp")
wetland_shp_path = os.path.join(shapefiles_dir, "Wetland_LandCover_Nyerseg_2019/Wetland_LandCover_Nyerseg_2019.shp")

# Paths for additional shapefiles
torma_shp_path = os.path.join(shapefiles_dir, "nov_kulturak/torma.shp")
kukorica_shp_path = os.path.join(shapefiles_dir, "nov_kulturak/kukorica.shp")
dohany1_shp_path = os.path.join(shapefiles_dir, "nov_kulturak/dohany1.shp")
dohany2_shp_path = os.path.join(shapefiles_dir, "nov_kulturak/dohany2.shp")

# Sidebar input for buffer distance
buffer_distance = st.sidebar.number_input("Buffer Distance (meters)", min_value=0, value=100, step=10)

if st.sidebar.button("Run Analysis"):
    # Check if required files exist
    required_files = [
        realwells_path, newlywells_path, forest_shp_path, waterbody_shp_path, wetland_shp_path
    ]
    missing_files = [f for f in required_files if not os.path.isfile(f)]
    
    if missing_files:
        st.error(f"The following required files are missing: {', '.join(missing_files)}")
    else:
        # Load shapefiles and apply CRS transformation
        forest_gdf = gpd.read_file(forest_shp_path).to_crs(epsg=23700)
        waterbody_gdf = gpd.read_file(waterbody_shp_path).to_crs(epsg=23700)
        wetland_gdf = gpd.read_file(wetland_shp_path).to_crs(epsg=23700)
        
        # Create buffers for each shapefile
        forest_buffer = forest_gdf.buffer(buffer_distance)
        waterbody_buffer = waterbody_gdf.buffer(buffer_distance)
        wetland_buffer = wetland_gdf.buffer(buffer_distance)
        
        # Load additional shapefiles if they exist and create buffers
        buffers = [forest_buffer, waterbody_buffer, wetland_buffer]
        additional_shapefiles = {
            'torma': torma_shp_path,
            'kukorica': kukorica_shp_path,
            'dohany1': dohany1_shp_path,
            'dohany2': dohany2_shp_path
        }
        
        for name, shp_path in additional_shapefiles.items():
            if os.path.isfile(shp_path):
                shp_gdf = gpd.read_file(shp_path).to_crs(epsg=23700)
                shp_buffer = shp_gdf.buffer(buffer_distance)
                buffers.append(shp_buffer)
        
        # Combine all buffers into one GeoSeries
        combined_buffer = gpd.GeoSeries(pd.concat(buffers, ignore_index=True))
        
        # Load the well data
        realwells_df = pd.read_csv(realwells_path, delimiter='\t', header=None, names=['EOV_X', 'EOV_Y'])
        newlywells_df = pd.read_csv(newlywells_path, delimiter='\t', header=None, names=['EOV_X', 'EOV_Y'])
        
        # Initialize the EOV to WGS84 transformer
        transformer = Transformer.from_crs("EPSG:23700", "EPSG:4326", always_xy=True)
        
        # Convert coordinates to GeoDataFrames
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
            lambda row: transformer.transform(row.geometry.x, row.geometry.y), axis=1, result_type='expand'
        )
        
        realwells_df[['Latitude', 'Longitude']] = realwells_gdf.apply(
            lambda row: transformer.transform(row.geometry.x, row.geometry.y), axis=1, result_type='expand'
        )
        
        # Create a Folium map centered on the average location
        center_lat = (realwells_df['Latitude'].mean() + filtered_newlywells_gdf['Latitude'].mean()) / 2
        center_lon = (realwells_df['Longitude'].mean() + filtered_newlywells_gdf['Longitude'].mean()) / 2
        wells_map = folium.Map(location=[center_lat, center_lon], zoom_start=10)
        
        # Add real wells to the map
        for _, row in realwells_df.iterrows():
            folium.CircleMarker(
                location=(row['Latitude'], row['Longitude']),
                radius=2,
                color='red',
                fill=True,
                fill_color='red',
                fill_opacity=0.6
            ).add_to(wells_map)
        
        # Add filtered new wells to the map
        for _, row in filtered_newlywells_gdf.iterrows():
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
        st_folium(wells_map, width=700, height=500)
        
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
