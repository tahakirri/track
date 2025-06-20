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
    
    # Map Plot
    st.map(df[["Latitude", "Longitude"]])
    
    st.success("Optimal trajectory computed!")
