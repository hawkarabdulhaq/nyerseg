import streamlit as st
import folium
import pandas as pd
import geopandas as gpd
from pyproj import Transformer
from streamlit_folium import st_folium
import os
import io
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

st.title("Well Location Analysis with Buffer Zones")

st.markdown("""
This application filters new well locations by excluding those within buffer zones of protected areas and displays the results on an interactive map.
""")

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
dohany1_shp_path = os.path.join(nov_kulturak_dir, "dohany1.shp")
dohany2_shp_path = os.path.join(nov_kulturak_dir, "dohany2.shp")

# Google Drive file IDs for the kukorica shapefile components
kukorica_file_ids = {
    'shp': '1nWPuABDefjUQPnlFWdvKdh7LbKMpew12',
    'shx': '1UwgSv0ybs-h3glpV20T0o3auwnhTnzbi',
    'dbf': '1YYD6fXSNTdELqzUE3Qa-pWx2tlqq2vls',
    'prj': '1twtD8xlmkhX8koJgarkI8kjfbFU6awOC',
    'cpg': '1KsDzeR1_6HxvsIeDPsyz8VgkRm0ZVWnR',
    'sbn': '1ENeEp6N-Vxv30baf_Wo32Xs_ojx8OC9p',
    'sbx': '1l2vzPlPW7pq2fNlJ4h45QLHvpsfdi0mc'
}

# Authenticate and build the Google Drive service
def authenticate_gdrive():
    try:
        # Access JSON credentials directly from Streamlit secrets
        service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/drive']
        )
    except json.JSONDecodeError as e:
        st.error(f"Error parsing JSON from Streamlit secrets: {e}")
        st.stop()

    service = build('drive', 'v3', credentials=credentials)
    return service

# Download files from Google Drive
def download_kukorica_files(service, file_ids, download_dir):
    os.makedirs(download_dir, exist_ok=True)
    for ext, file_id in file_ids.items():
        request = service.files().get_media(fileId=file_id)
        fh = io.FileIO(os.path.join(download_dir, f'kukorica.{ext}'), 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            st.write(f"Downloading kukorica.{ext}: {int(status.progress() * 100)}%")
        fh.close()

kukorica_shp_dir = os.path.join(BASE_DIR, "kukorica_shp")
kukorica_shp_path = os.path.join(kukorica_shp_dir, "kukorica.shp")

# Sidebar buffer input
buffer_distance = st.sidebar.number_input("Buffer Distance (meters)", min_value=0, value=50, step=10)

if st.sidebar.button("Run Analysis") or 'filtered_data' not in st.session_state:
    # Authenticate and download kukorica files
    st.write("Authenticating with Google Drive API...")
    service = authenticate_gdrive()
    st.write("Downloading kukorica shapefile components...")
    download_kukorica_files(service, kukorica_file_ids, kukorica_shp_dir)

    # Load shapefiles and continue with your processing logic...
    # Load buffer shapefiles and set CRS
    forest_gdf = gpd.read_file(forest_shp_path).to_crs(epsg=23700)
    waterbody_gdf = gpd.read_file(waterbody_shp_path).to_crs(epsg=23700)
    wetland_gdf = gpd.read_file(wetland_shp_path).to_crs(epsg=23700)
    torma_gdf = gpd.read_file(torma_shp_path).to_crs(epsg=23700)
    dohany1_gdf = gpd.read_file(dohany1_shp_path).to_crs(epsg=23700)
    dohany2_gdf = gpd.read_file(dohany2_shp_path).to_crs(epsg=23700)
    kukorica_gdf = gpd.read_file(kukorica_shp_path).to_crs(epsg=23700)

    # Create buffers
    forest_buffer = forest_gdf.buffer(buffer_distance)
    waterbody_buffer = waterbody_gdf.buffer(buffer_distance)
    wetland_buffer = wetland_gdf.buffer(buffer_distance)
    torma_buffer = torma_gdf.buffer(buffer_distance)
    dohany1_buffer = dohany1_gdf.buffer(buffer_distance)
    dohany2_buffer = dohany2_gdf.buffer(buffer_distance)
    kukorica_buffer = kukorica_gdf.buffer(buffer_distance)

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

    # Set CRS for combined_buffer
    combined_buffer.crs = "EPSG:23700"

    # Read the well data
    realwells_df = pd.read_csv(realwells_path, delimiter='\t', header=None, names=['EOV_X', 'EOV_Y'])
    newlywells_df = pd.read_csv(newlywells_path, delimiter='\t', header=None, names=['EOV_X', 'EOV_Y'])

    # Initialize the EOV to WGS84 transformer
    transformer = Transformer.from_crs("EPSG:23700", "EPSG:4326")

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

    # Ensure CRS matches
    if combined_buffer.crs != newlywells_gdf.crs:
        combined_buffer = combined_buffer.set_crs(newlywells_gdf.crs, allow_override=True)

    # Filter out wells within buffer
    def is_within_buffers(point):
        return combined_buffer.intersects(point).any()

    filtered_newlywells_gdf = newlywells_gdf[~newlywells_gdf.geometry.apply(is_within_buffers)].copy()

    if filtered_newlywells_gdf.empty:
        st.warning("No wells remain after filtering. Adjust the buffer distance or check your data.")
        st.stop()

    # Convert EOV to Lat/Lon
    def eov_to_latlon(eov_x, eov_y):
        lat, lon = transformer.transform(eov_x, eov_y)
        return pd.Series({'Latitude': lat, 'Longitude': lon})

    filtered_newlywells_gdf[['Latitude', 'Longitude']] = filtered_newlywells_gdf.apply(
        lambda row: eov_to_latlon(row.geometry.x, row.geometry.y), axis=1
    )

    realwells_gdf[['Latitude', 'Longitude']] = realwells_gdf.apply(
        lambda row: eov_to_latlon(row.geometry.x, row.geometry.y), axis=1
    )

    # Create a Folium map centered around an average location
    center_lat = (realwells_gdf['Latitude'].mean() + filtered_newlywells_gdf['Latitude'].mean()) / 2
    center_lon = (realwells_gdf['Longitude'].mean() + filtered_newlywells_gdf['Longitude'].mean()) / 2

    wells_map = folium.Map(location=[center_lat, center_lon], zoom_start=10)

    # Add real wells to the map
    for index, row in realwells_gdf.iterrows():
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

    st.session_state['filtered_data'] = filtered_newlywells_gdf[['EOV_X', 'EOV_Y', 'Latitude', 'Longitude']]
    st.session_state['map'] = wells_map

if 'map' in st.session_state:
    st.subheader("Filtered Wells Map")
    st_folium(st.session_state['map'], width=700, height=500)

if 'filtered_data' in st.session_state:
    csv = st.session_state['filtered_data'].to_csv(index=False)
    st.subheader("Download Filtered Wells Data")
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name='filtered_newlywells.csv',
        mime='text/csv'
    )
