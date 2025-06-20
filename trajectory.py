import streamlit as st
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import pandas as pd
import numpy as np

st.set_page_config(page_title="Optimal Trajectory Finder", layout="centered")
st.title("Optimal Trajectory Finder")

st.markdown("""
Enter your starting location and a list of locations (addresses or coordinates). The app will compute the most optimal trajectory to visit all locations starting from the start location.
""")

from streamlit_folium import st_folium
import folium

st.markdown("---")
st.subheader("Pick Start and Other Locations on the Map")

# Initialize session state for locations
if 'picked_points' not in st.session_state:
    st.session_state['picked_points'] = []
if 'start_point' not in st.session_state:
    st.session_state['start_point'] = None

def reset_points():
    st.session_state['picked_points'] = []
    st.session_state['start_point'] = None

st.button("Reset Map Selections", on_click=reset_points)

# Create a Folium map
m = folium.Map(location=[30, 0], zoom_start=2)

# Add markers for already picked points
for i, pt in enumerate(st.session_state['picked_points']):
    folium.Marker(pt, icon=folium.Icon(color='blue', icon='info-sign'), tooltip=f"Stop {i+1}").add_to(m)
if st.session_state['start_point']:
    folium.Marker(st.session_state['start_point'], icon=folium.Icon(color='red', icon='star'), tooltip="Start").add_to(m)

# Show map and handle clicks
map_data = st_folium(m, width=700, height=500)

if map_data and map_data['last_clicked']:
    lat = map_data['last_clicked']['lat']
    lon = map_data['last_clicked']['lng']
    if st.button("Set as Start Location", key=f"set_start_{lat}_{lon}"):
        st.session_state['start_point'] = (lat, lon)
    if st.button("Add as Stop Location", key=f"add_stop_{lat}_{lon}"):
        if (lat, lon) not in st.session_state['picked_points']:
            st.session_state['picked_points'].append((lat, lon))

# Optionally, allow manual entry as fallback
with st.expander("Or enter locations manually"):
    start_location = st.text_input("Start Location (address or lat,lon)")
    locations_text = st.text_area("Other Locations (one per line, address or lat,lon)")
    manual_submit = st.button("Add Manual Locations")
    if manual_submit:
        geolocator = Nominatim(user_agent="streamlit-optimal-trajectory")
        def parse_location(loc):
            loc = loc.strip()
            if "," in loc:
                try:
                    lat, lon = map(float, loc.split(","))
                    return (lat, lon)
                except:
                    pass
            try:
                location = geolocator.geocode(loc)
                if location:
                    return (location.latitude, location.longitude)
            except:
                pass
            return None
        # Add start
        coords = parse_location(start_location)
        if coords:
            st.session_state['start_point'] = coords
        # Add stops
        for line in locations_text.strip().split("\n"):
            if line.strip():
                coords = parse_location(line)
                if coords and coords not in st.session_state['picked_points']:
                    st.session_state['picked_points'].append(coords)

# Use picked points for calculation
geolocator = Nominatim(user_agent="streamlit-optimal-trajectory")

# Reverse geocode start and stops
start_coords = st.session_state['start_point']
if start_coords:
    try:
        start_address = geolocator.reverse(start_coords, language='en').address
    except:
        start_address = f"{start_coords[0]}, {start_coords[1]}"
else:
    st.warning("Please select a start location on the map or enter it manually.")
    st.stop()

locations = []
for pt in st.session_state['picked_points']:
    try:
        address = geolocator.reverse(pt, language='en').address
    except:
        address = f"{pt[0]}, {pt[1]}"
    locations.append((address, pt))

if not locations:
    st.warning("Please add at least one stop location on the map or enter it manually.")
    st.stop()
    
    # Nearest Neighbor TSP
    remaining = locations.copy()
    route = [("Start", start_coords)]
    current = start_coords
    while remaining:
        dists = [geodesic(current, loc[1]).km for loc in remaining]
        idx = int(np.argmin(dists))
        route.append(remaining[idx])
        current = remaining[idx][1]
        del remaining[idx]
    
    st.subheader("Optimal Trajectory (Order of Visit)")
    # Calculate estimated time between stops (assuming average speed, e.g., 50 km/h)
    avg_speed_kmh = 50  # You can adjust this value
    times = [0.0]  # First stop is the start
    dists = [0.0]
    total_time = 0.0
    total_dist = 0.0
    for i in range(1, len(route)):
        dist = geodesic(route[i-1][1], route[i][1]).km
        dists.append(dist)
        time = dist / avg_speed_kmh  # in hours
        times.append(time)
        total_time += time
        total_dist += dist
    
    df = pd.DataFrame({
        "Order": list(range(1, len(route)+1)),
        "Location": [x[0] for x in route],
        "Latitude": [x[1][0] for x in route],
        "Longitude": [x[1][1] for x in route],
        "Distance from Prev (km)": [round(d, 2) for d in dists],
        "Est. Time from Prev (min)": [round(t*60, 1) for t in times],
    })
    st.dataframe(df)
    st.info(f"Total estimated distance: {round(total_dist, 2)} km. Total estimated time: {round(total_time*60, 1)} minutes (at {avg_speed_kmh} km/h average speed).")
    
    # Map Plot with pydeck: show markers and the trajectory path
    import pydeck as pdk
    df_map = df.dropna(subset=["Latitude", "Longitude"])
    st.write("Plotted coordinates:", df_map[["Latitude", "Longitude"]])  # Debug info

    if not df_map.empty:
        scatter_layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_map,
            get_position='[Longitude, Latitude]',
            get_color='[200, 30, 0, 160]',
            get_radius=100,
            pickable=True,
        )
        layers = [scatter_layer]
        if len(df_map) > 1:
            line_data = [
                {"source": [df_map.iloc[i]["Longitude"], df_map.iloc[i]["Latitude"]],
                 "target": [df_map.iloc[i+1]["Longitude"], df_map.iloc[i+1]["Latitude"]]}
                for i in range(len(df_map)-1)
            ]
            line_layer = pdk.Layer(
                "LineLayer",
                data=line_data,
                get_source_position='source',
                get_target_position='target',
                get_color=[0, 100, 255, 200],
                width_scale=2,
                width_min_pixels=2,
                get_width=5,
                pickable=True,
            )
            layers.append(line_layer)
        midpoint = (np.average(df_map["Latitude"]), np.average(df_map["Longitude"]))
        st.pydeck_chart(pdk.Deck(
            map_style="mapbox://styles/mapbox/streets-v12",
            initial_view_state=pdk.ViewState(
                latitude=midpoint[0],
                longitude=midpoint[1],
                zoom=11 if len(df_map) > 1 else 3,
                pitch=0,
            ),
            layers=layers,
            tooltip={"text": "{Location}"}
        ))
    else:
        st.warning("No valid coordinates to display on the map.")

    st.success("Optimal trajectory computed!")
