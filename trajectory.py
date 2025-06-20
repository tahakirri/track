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

with st.form("location_form"):
    start_location = st.text_input("Start Location (address or lat,lon)")
    locations_text = st.text_area("Other Locations (one per line, address or lat,lon)")
    submitted = st.form_submit_button("Find Optimal Trajectory")

if submitted:
    geolocator = Nominatim(user_agent="streamlit-optimal-trajectory")
    
    def parse_location(loc):
        loc = loc.strip()
        if "," in loc:
            try:
                lat, lon = map(float, loc.split(","))
                return (lat, lon)
            except:
                pass
        # Try to geocode address
        try:
            location = geolocator.geocode(loc)
            if location:
                return (location.latitude, location.longitude)
        except:
            pass
        return None
    
    # Parse start location
    start_coords = parse_location(start_location)
    if not start_coords:
        st.error("Could not parse start location.")
        st.stop()
    
    # Parse other locations
    locations = []
    for line in locations_text.strip().split("\n"):
        if line.strip():
            coords = parse_location(line)
            if coords:
                locations.append((line.strip(), coords))
            else:
                st.warning(f"Could not parse location: {line}")
    if not locations:
        st.error("No valid locations provided.")
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
    df = pd.DataFrame({
        "Order": list(range(1, len(route)+1)),
        "Location": [x[0] for x in route],
        "Latitude": [x[1][0] for x in route],
        "Longitude": [x[1][1] for x in route]
    })
    st.dataframe(df)
    
    # Map Plot with pydeck: show markers and the trajectory path
    import pydeck as pdk
    df_map = df.dropna(subset=["Latitude", "Longitude"])
    if not df_map.empty:
        # Scatterplot layer for locations
        scatter_layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_map,
            get_position='[Longitude, Latitude]',
            get_color='[200, 30, 0, 160]',
            get_radius=100,
            pickable=True,
        )
        # Line layer for trajectory path
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
        midpoint = (np.average(df_map["Latitude"]), np.average(df_map["Longitude"]))
        st.pydeck_chart(pdk.Deck(
            map_style="mapbox://styles/mapbox/streets-v12",
            initial_view_state=pdk.ViewState(
                latitude=midpoint[0],
                longitude=midpoint[1],
                zoom=10,
                pitch=0,
            ),
            layers=[scatter_layer, line_layer],
            tooltip={"text": "{Location}"}
        ))
    else:
        st.warning("No valid coordinates to display on the map.")

    st.success("Optimal trajectory computed!")
