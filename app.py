import streamlit as st
import folium
from streamlit_folium import st_folium
import os

from data_loader import load_shapefiles, load_well_data
from processors import process_buffers, filter_wells
from visualizer import create_wells_map

# Define the access key
ACCESS_KEY = "Asd456"

# Define authentication state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Display login screen if not authenticated
if not st.session_state.authenticated:
    st.title("Well Location Analysis with Buffer Zones - Login")
    
    st.write("Please enter the access key to proceed.")
    input_key = st.text_input("Access Key", type="password")

    # Check if input key matches
    if st.button("Login"):
        if input_key == ACCESS_KEY:
            st.session_state.authenticated = True
            st.success("Access granted! You can now use the app.")
            st.experimental_set_query_params(auth="true")  # Set query param to refresh
        else:
            st.error("Invalid access key. Please try again.")
    st.stop()  # Stop the app here if not authenticated

# If authenticated, display the main app content
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
kukorica_shp_path = os.path.join(nov_kulturak_dir, "kukorica.shp")
dohany1_shp_path = os.path.join(nov_kulturak_dir, "dohany1.shp")
dohany2_shp_path = os.path.join(nov_kulturak_dir, "dohany2.shp")

# List of shapefile paths
shapefile_paths = [
    forest_shp_path,
    waterbody_shp_path,
    wetland_shp_path,
    torma_shp_path,
    kukorica_shp_path,
    dohany1_shp_path,
    dohany2_shp_path
]

# Sidebar buffer input
buffer_distance = st.sidebar.number_input("Buffer Distance (meters)", min_value=0, value=50, step=10)

if st.sidebar.button("Run Analysis") or 'filtered_data' not in st.session_state:
    # Load shapefiles
    shapefiles = load_shapefiles(shapefile_paths)

    # Create buffers and combined buffer
    combined_buffer = process_buffers(shapefiles, buffer_distance)

    # Load well data
    realwells_gdf, newlywells_gdf = load_well_data(realwells_path, newlywells_path)

    # Filter wells
    filtered_newlywells_gdf = filter_wells(combined_buffer, newlywells_gdf)

    if filtered_newlywells_gdf.empty:
        st.warning("No wells remain after filtering. Adjust the buffer distance or check your data.")
        st.stop()

    # Create map and prepare filtered data
    wells_map, filtered_data = create_wells_map(realwells_gdf, filtered_newlywells_gdf)

    # Save filtered data and map in session state
    st.session_state['filtered_data'] = filtered_data
    st.session_state['map'] = wells_map

# Display the map if it exists in session state
if 'map' in st.session_state:
    st.subheader("Filtered Wells Map")
    st_folium(st.session_state['map'], width=700, height=500)

# Prepare and display the download button if data is available
if 'filtered_data' in st.session_state:
    csv = st.session_state['filtered_data'].to_csv(index=False)
    st.subheader("Download Filtered Wells Data")
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name='filtered_newlywells.csv',
        mime='text/csv'
    )
