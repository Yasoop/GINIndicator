import logging
logger = logging.getLogger(__name__)

import streamlit as st
import requests
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from modules.nav import SideBarLinks
from modules.presets import get_presets

# API Configuration
API_BASE_URL = "http://web-api:4000"  

# Page setup
st.set_page_config(layout='wide')
st.title("Data Playground")
st.markdown("*Explore how different economic factors affect income inequality.*")

# Sidebar
SideBarLinks()

# Feature variable mapping to match backend expectations
FEATURE_MAPPING = {
    "Population": "Population",
    "GDP per capita": "GDP_per_capita", 
    "Trade union density": "Trade_union_density",
    "Unemployment rate": "Unemployment_rate",
    "Health": "Health",
    "Education": "Education", 
    "Housing": "Housing",
    "Community development": "Community_development",
    "Productivity": "Productivity",
    "Inflation": "Inflation",
    "IRLT": "IRLT"
}

# API Functions
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_available_features():
    """Fetch available feature variables from backend"""
    try:
        response = requests.get(f"{API_BASE_URL}/playground/features", timeout=10)
        if response.status_code == 200:
            return response.json().get("features", [])
        else:
            st.error(f"Failed to fetch features: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to backend: {str(e)}")
        return None

def save_graph_to_backend(user_id, graph_name, x_axis, x_min, x_max, x_steps, feature_values):
    """Save graph configuration to backend"""
    try:
        data = {
            "user_id": user_id,
            "name": graph_name,
            "x_axis": x_axis,
            "x_min": x_min,
            "x_max": x_max,
            "x_steps": x_steps,
            **feature_values  # Spread all feature values
        }
        
        response = requests.post(f"{API_BASE_URL}/playground/save", json=data, timeout=10)
        return response.status_code == 201, response.json()
    except requests.exceptions.RequestException as e:
        return False, {"error": str(e)}

@st.cache_data(ttl=60)  # Cache for 1 minute
def fetch_saved_graphs(user_id):
    """Fetch saved graphs for a user"""
    try:
        response = requests.get(f"{API_BASE_URL}/playground/saved/{user_id}", timeout=10)
        if response.status_code == 200:
            return response.json().get("saved_graphs", [])
        else:
            return []
    except requests.exceptions.RequestException:
        return []

def load_graph_from_backend(graph_id):
    """Load a specific graph configuration"""
    try:
        response = requests.get(f"{API_BASE_URL}/playground/graph/{graph_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.exceptions.RequestException:
        return None
    
def fetch_preset_options():
    """Load presets for playground dropdown"""
    try:
        response = requests.get(f"{API_BASE_URL}/playground/presets", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.exceptions.RequestException:
        return None

def generate_real_predictions(feature_values, x_axis, x_min, x_max, steps):
    """Generate real GINI predictions using the actual model in the backend API"""
    try:
        # Prepare the request data with the correct structure for models endpoint
        data = {
            "XAxis": x_axis,
            "XMin": x_min,
            "XMax": x_max,
            "XStep": steps,  # Send number of steps directly
            **feature_values  # Include all feature values
        }

        # Make the API call to the models endpoint
        response = requests.post(f"{API_BASE_URL}/models/playground/predict", json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            x_values = result.get("x_values", [])
            y_values = result.get("predictions", [])
            
            return x_values, y_values
        else:
            st.error(f"Failed to generate predictions: {response.status_code}")
            return None, None
            
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to backend: {str(e)}")
        return None, None

# maps regions of selectbox into region variables that can be input into graph data
# not sure if this is the most efficient way but it works
def map_regions(region):
    regions = {"East Asia and Pacific": 0,
               "Europe and Central Asia": 0,
               "Latin America and Caribbean": 0,
               "Middle East and North Africa": 0}
    regions[region] = 1
    return (regions["East Asia and Pacific"], 
            regions["Europe and Central Asia"], 
            regions["Latin America and Caribbean"], 
            regions["Middle East and North Africa"])

def get_region_from_features(features):
    if features["Region_East_Asia_and_Pacific"] == 1:
        return 0
    if features["Region_Europe_and_Central_Asia"] == 1:
        return 1
    if features["Region_Latin_America_and_Caribbean"] == 1:
        return 2
    if features["Region_Middle_East_and_North_Africa"] == 1:
        return 3


# Initialize session state
if 'graph_data' not in st.session_state:
    st.session_state.graph_data = None
if 'available_features' not in st.session_state:
    st.session_state.available_features = None

# Check authentication and get user ID
if not st.session_state.get('authenticated', False):
    st.error("Please log in first!!")
    st.info("Use sidebar to navigate to home page and log in.")
    if st.button("🏠 Go to Home Page", type="primary"):
        st.switch_page('Home.py')
    st.stop()

graph_id = st.session_state.get('loaded_graph_id')
if graph_id:
    graph_data = requests.get(API_BASE_URL + f"/playground/graph/{graph_id}").json()
    st.session_state['loaded_graph'] = graph_data
st.write(str(graph_id))

# Get user ID from session state (set during login)
user_id = st.session_state.get('UserID')
if not user_id:
    st.error("User ID not found in session state. Please log in again from the home page.")
    if st.button("🏠 Go to Home Page", type="primary"):
        st.switch_page('Home.py')
    st.stop()


# Fetch available features from backend
if st.session_state.available_features is None:
    with st.spinner("Loading available features..."):
        backend_features = fetch_available_features()
        if backend_features:
            # Convert backend feature names to frontend display names
            display_features = []
            backend_to_display = {v: k for k, v in FEATURE_MAPPING.items()}
            
            for backend_feature in backend_features:
                display_name = backend_to_display.get(backend_feature, backend_feature)
                display_features.append(display_name)
            
            st.session_state.available_features = display_features
        else:
            # Fallback to hardcoded features if backend is unavailable
            st.session_state.available_features = list(FEATURE_MAPPING.keys())
            st.warning("⚠️ Backend unavailable - using default features")


# Show current user info in sidebar
with st.sidebar:
    st.markdown("### 👤 Current User")
    user_name = st.session_state.get('Name', 'Unknown User')
    user_roles = st.session_state.get('Roles', [])
    
    st.info(f"**{user_name}**")
    if user_roles:
        st.caption(f"Roles: {', '.join(user_roles)}")
    
    # Logout button
    if st.button("🚪 Logout", use_container_width=True):
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("Logged out successfully!")
        st.switch_page('Home.py')
    
    st.markdown("---")
    
    # Load saved graphs
    st.markdown("### 📁 Load Saved Graphs")
    saved_graphs = fetch_saved_graphs(user_id)
    
    if saved_graphs:
        graph_names = [f"{graph['name']} ({graph['date_saved'][:10] if graph['date_saved'] else 'Unknown'})" 
                      for graph in saved_graphs]
        
        selected_graph = st.selectbox("Load saved graph:", ["None"] + graph_names, key="load_graph_select")
        
        if selected_graph != "None" and st.button("🔄 Load Graph", use_container_width=True):
            graph_index = graph_names.index(selected_graph)
            selected_graph_data = saved_graphs[graph_index]
            
            # Load graph configuration into session state
            st.session_state.loaded_graph = selected_graph_data
            # Clear any selected preset when loading a graph
            if 'selected_preset' in st.session_state:
                del st.session_state.selected_preset
            st.success(f"Loaded graph: {selected_graph_data['name']}")
            st.rerun()
    else:
        st.info("No saved graphs found")

# Main content area
if st.session_state.graph_data is not None:
    # Show the generated graph
    st.markdown("### Generated GINI Coefficient Prediction")
    
    # Create plotly figure
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=st.session_state.graph_data['x_values'],
        y=st.session_state.graph_data['y_values'],
        mode='lines+markers',
        name='GINI Prediction',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=6)
    ))
    
    fig.update_layout(
        title=f"GINI Coefficient vs {st.session_state.graph_data['feature_name']}",
        xaxis_title=st.session_state.graph_data['feature_name'],
        yaxis_title='GINI Coefficient',
        template='plotly_white',
        height=500,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)
else:
    # Show placeholder image when no graph is generated
    st.image("assets/posts/placeholderGraph.gif", caption="GINI vs Population (example)")

# Columns for presets + controls
col1, col2, col3 = st.columns([0.75, 0.05, 0.4])

with col1:
    
    json_of_presets = fetch_preset_options() # NOTE : working here rn
    
    # Error handling for API response
    if json_of_presets and "data" in json_of_presets:
        # Unpacking json response, grabbing just the data
        preset_data = json_of_presets["data"]
        # Making the strings for preset dropdown
        country_options = [f"{entry['Reference_area']} ({entry['Time_period']})" for entry in preset_data]
    else:
        # make the dropdown empty if the api call fails
        preset_data = []
        country_options = ["No presets available"]  # Fallback option
        st.error("Failed to load presets from API.")
    
    st.markdown("### Presets:")
    # Stores the index of the selected preset
    selected_index = st.selectbox("", country_options, key="preset_select", index=0)
    
    # Apply preset button
    if selected_index != "No presets available" and st.button("📋 Apply Preset", use_container_width=True):
        # If the api call was successful then we can grab the data from the selected preset
        if 'loaded_graph_id' in st.session_state:
            del st.session_state['loaded_graph_id']
        if 'loaded_graph' in st.session_state:
            del st.session_state['loaded_graph']
        if preset_data:
            # Get the index for the selected preset, then grab the data from that index
            data_index = country_options.index(selected_index)
            matching_entry = preset_data[data_index]
            
            # Map the region to the expected format
            region_name = matching_entry.get("Region", "Europe and Central Asia")
            east_asia, europe, latin_america, middle_east = map_regions(region_name)
            
            # Create the preset data structure
            preset_values = {
                "Population": int(matching_entry.get("Population", 22000000)),  # Convert to int
                "GDP_per_capita": float(matching_entry.get("GDP_per_capita", 41000.0)),  # Convert to float
                "Trade_union_density": float(matching_entry.get("Trade_union_density", 33.0)),
                "Unemployment_rate": float(matching_entry.get("Unemployment_rate", 8.0)),
                "Health": float(matching_entry.get("Health", 0.064)),
                "Education": float(matching_entry.get("Education", 0.052)),
                "Housing": float(matching_entry.get("Housing", 0.0032)),
                "Community_development": float(matching_entry.get("Community_development", 0.0019)),
                "Corporate_tax_rate": float(matching_entry.get("Corporate_tax_rate", 21.0)),
                "Inflation": float(matching_entry.get("Inflation", 2.1)),
                "IRLT": float(matching_entry.get("IRLT", 7.9)),
                "Region_East_Asia_and_Pacific": east_asia,
                "Region_Europe_and_Central_Asia": europe,
                "Region_Latin_America_and_Caribbean": latin_america,
                "Region_Middle_East_and_North_Africa": middle_east
            }
            
            # Store the selected preset data in session state
            st.session_state.selected_preset = preset_values
            st.success(f"Applied preset: {selected_index}")
            st.rerun()
        else:
            st.error("No preset data available")

    st.markdown("")

    # Feature buttons — 4x4 grid to accommodate all features
    with st.expander("ADVANCED MODE"):
        st.markdown("### Feature Variables:")
        feature_cols = st.columns(3)

        # Determine default values (priority: loaded graph > selected preset > hardcoded defaults)
        loaded_graph = st.session_state.get('loaded_graph', None)
        selected_preset_data = st.session_state.get('selected_preset', None)
        
        def get_default_value(feature_key, fallback_default, as_int=False):
            """Get default value with priority: loaded graph > preset > fallback"""
            value = fallback_default
            if loaded_graph and 'features' in loaded_graph:
                value = loaded_graph['features'].get(feature_key, fallback_default)
            elif selected_preset_data:
                value = selected_preset_data.get(feature_key, fallback_default)
            
            # Convert to int if requested (for fields like Population)
            if as_int:
                return int(value)
            else:
                return float(value)
            
        def get_default_region():
            """Get default value with priority: loaded graph > preset > fallback"""
            if loaded_graph and 'features' in loaded_graph:
                value = get_region_from_features(loaded_graph['features'])
            elif selected_preset_data:
                value = get_region_from_features(selected_preset_data)
            else: 
                value = 0
            return value

        with feature_cols[0]:
            population = st.number_input("Population:", 
                                    value=get_default_value('Population', 22000000, as_int=True), 
                                    key="population", 
                                    min_value=0,
                                    step=1000000,
                                    help="Population of a country.  \n**Min:** 0 **Avg:** 22,000,000")
            gdp_per_capita = st.number_input("GDP per capita:", 
                                        value=get_default_value('GDP_per_capita', 41000.0), 
                                        key="gdp_per_capita",
                                        min_value=0.0,
                                        step=1000.0,
                                        help="GDP divided by population.  \n**Min:** 0 **Avg:** 41,000")
            trade_union = st.number_input("Trade union density:", 
                                        value=get_default_value('Trade_union_density', 33.0), 
                                        key="trade_union",
                                        min_value=0.0,
                                        max_value=100.0,
                                        step=1.0,
                                        format='%.1f',
                                        help="Percent of workers in a trade union.  \n**Min:** 0 **Max:** 100 **Avg:** 33")
            unemployment = st.number_input("Unemployment rate:", 
                                        value=get_default_value('Unemployment_rate', 8.0), 
                                        key="unemployment",
                                        min_value=0.0,
                                        max_value=100.0,
                                        step=1.0,
                                        format='%.1f',
                                        help="Percent of labor force unemployed.  \n**Min:** 0 **Max:** 100 **Avg:** 8")

        with feature_cols[1]:
            health = st.number_input("Health:", 
                                value=get_default_value('Health', .064), 
                                key="health",
                                min_value=0.0,
                                max_value=1.0,
                                step=.01,
                                format='%.4f',
                                help="Share of GDP spent by government on health.  \n**Min:** 0 **Max:** 1 **Avg:** .064")
            education = st.number_input("Education:", 
                                    value=get_default_value('Education', .052), 
                                    key="education",
                                    min_value=0.0,
                                    max_value=1.0,
                                    step=.01,
                                    format='%.4f',
                                    help="Share of GDP spent by government on education.  \n**Min:** 0 **Max:** 1 **Avg:** .052")
            housing = st.number_input("Housing:", 
                                    value=get_default_value('Housing', .0032), 
                                    key="housing",
                                    min_value=0.0,
                                    max_value=1.0,
                                    step=.001,
                                    format='%.4f',
                                    help="Share of GDP spent by government on housing.  \n**Min:** 0 **Max:** 1 **Avg:** .0032")
            community = st.number_input("Community development:", 
                                    value=get_default_value('Community_development', .0019), 
                                    key="community",
                                    min_value=0.0,
                                    max_value=1.0,
                                    step=.001,
                                    format='%.4f',
                                    help="Share of GDP (current US$) spent by government on community development.  \n**Min:** 0 **Max:** 1 **Avg:** .0019")

        with feature_cols[2]:
            corporate_tax = st.number_input("Corporate tax rate:", 
                                        value=get_default_value('Corporate_tax_rate', 21.0), 
                                        key="corporate_tax",
                                        min_value=0.0,
                                        max_value=100.0,
                                        step=1.0,
                                        format='%.1f',
                                        help="Percent of profits that corporations pay in taxes.  \n**Min:** 0 **Max:** 100 **Avg:** 25")
            inflation = st.number_input("Inflation:", 
                                    value=get_default_value('Inflation', 2.1), 
                                    key="inflation",
                                    format='%.1f',
                                    step=1.0,
                                    help="Percent increase in general prices in a given year.  \n**No bounds.** **Avg:** 2.1")
            irlt = st.number_input("IRLT:", 
                                value=get_default_value('IRLT', 7.9), 
                                key="irlt",
                                step=1.0,
                                format='%.1f',
                                help="Percent interest paid on long-term bonds and loans.  \n**Min:** 0 **Max:** 100 **Avg:** 3.5")   
            region = st.selectbox("Region:", options=["East Asia and Pacific", 
                                                      "Europe and Central Asia", 
                                                      "Latin America and Caribbean", 
                                                      "Middle East and North Africa"],
                                    help="Region of the world country is located.",
                                    index = get_default_region())
            east_asia, europe, latin_america, middle_east = map_regions(region)
            # Add some spacing for cleaner ui
            st.markdown("")
            st.markdown("")

    with st.popover(label="What is the Gini index?"):
        st.markdown("""The Gini index is a measure of economic inequality in a country from 0 to 1, 
            where 0 is perfect equality, and 1 is perfect inequality. It is calculated using
            the Lorenz curve, a curve that displays the distribution of income in a country.""")
        image_col, description_col = st.columns([.5,.5])
        
        with image_col:
            st.image("assets/gini_graph.png", width=300)
        
        with description_col:
            st.write(""" **Area A** is the area between the Lorenz curve and the _line of perfect equality_,
                        and **Area B** is the area between the Lorenz curve and the _X axis._
            """)
            st.write("The Gini index is calculated as:")
            st.write("$GINI = \dfrac{ A }{A + B}$")


with col3:
    st.markdown("### Currently Comparing:")
    
    # Use features from backend if available
    available_features = st.session_state.available_features or list(FEATURE_MAPPING.keys())
    available_features = available_features[:-4]
    # Set default compare feature from loaded graph
    default_compare_feature = None
    if loaded_graph:
        backend_feature = loaded_graph.get('x_axis')
        backend_to_display = {v: k for k, v in FEATURE_MAPPING.items()}
        default_compare_feature = backend_to_display.get(backend_feature)
    
    default_index = 0
    if default_compare_feature and default_compare_feature in available_features:
        default_index = available_features.index(default_compare_feature)
    
    compare_feature = st.selectbox("Feature", available_features, 
                                 index=default_index, key="compare_feature")
    feature_values = {
                # Main features
                "Population": population,
                "GDP_per_capita": gdp_per_capita,
                "Trade_union_density": trade_union,
                "Unemployment_rate": unemployment,
                "Health": health,
                "Education": education,
                "Housing": housing,
                "Community_development": community,
                "Corporate_tax_rate": corporate_tax,
                "Inflation": inflation,
                "IRLT": irlt,
                
                # Region features
                "Region_East_Asia_and_Pacific": east_asia,
                "Region_Europe_and_Central_Asia": europe,
                "Region_Latin_America_and_Caribbean": latin_america,
                "Region_Middle_East_and_North_Africa": middle_east
            }
    current_compared_value = feature_values[FEATURE_MAPPING[compare_feature]]

    stds = requests.get(API_BASE_URL + "/models/playground/stds").json()[0]
    current_std = stds[FEATURE_MAPPING[compare_feature]]
    st.write()

    # Set default values from loaded graph
    default_x_min = loaded_graph.get('x_min', 0) if loaded_graph else 0
    default_x_max = loaded_graph.get('x_max', current_compared_value + 3 * current_std) if loaded_graph else current_compared_value + 3 * current_std
    default_steps = loaded_graph.get('x_steps', 20) if loaded_graph else 20

    x_min = st.number_input("Min:", value=float(default_x_min), key="x_min", format='%.4f')
    x_max = st.number_input("Max:", value=float(default_x_max), key="x_max", format='%.4f')
    steps = st.number_input("Steps:", value=int(default_steps), min_value=5, max_value=100, step=1, key="steps")
    
    st.markdown("")
    
    # Generate button
    if st.button("🚀 Generate Graph", type="primary", use_container_width=True):
        if x_min >= x_max:
            st.error("Min value must be less than Max value!")
        elif steps < 5:
            st.error("Steps must be at least 5!")
        else:
            # Collect all feature values
            feature_values = {
                # Main features
                "Population": population,
                "GDP_per_capita": gdp_per_capita,
                "Trade_union_density": trade_union,
                "Unemployment_rate": unemployment,
                "Health": health,
                "Education": education,
                "Housing": housing,
                "Community_development": community,
                "Corporate_tax_rate": corporate_tax,
                "Inflation": inflation,
                "IRLT": irlt,
                
                # Region features
                "Region_East_Asia_and_Pacific": east_asia,
                "Region_Europe_and_Central_Asia": europe,
                "Region_Latin_America_and_Caribbean": latin_america,
                "Region_Middle_East_and_North_Africa": middle_east
            }
            

            
            backend_feature_name = FEATURE_MAPPING.get(compare_feature, compare_feature)
            
            with st.spinner("Generating predictions..."):
                x_values, y_values = generate_real_predictions(
                    feature_values,
                    backend_feature_name,
                    x_min,
                    x_max,
                    int(steps)
                )
                
                if x_values is not None and y_values is not None:
                    # Store in session state
                    st.session_state.graph_data = {
                        'x_values': x_values,
                        'y_values': y_values,
                        'feature_name': compare_feature
                    }
                    
                    st.success("Graph generated successfully!")
                    st.rerun()
                else:
                    st.error("Failed to generate predictions. Please try again.")
    
    # Save button
    if st.session_state.graph_data is not None:
        st.markdown("")
        graph_name = st.text_input("Graph name:", placeholder="My Graph", key="graph_name_input")
        
        if st.button("💾 Save Graph", use_container_width=True) and graph_name:
            # Collect all feature values
            feature_values = {
                # Main features
                "Population": population,
                "GDP_per_capita": gdp_per_capita,
                "Trade_union_density": trade_union,
                "Unemployment_rate": unemployment,
                "Health": health,
                "Education": education,
                "Housing": housing,
                "Community_development": community,
                "Corporate_tax_rate": corporate_tax,
                "Inflation": inflation,
                "IRLT": irlt,
                
                # Region features
                "Region_East_Asia_and_Pacific": east_asia,
                "Region_Europe_and_Central_Asia": europe,
                "Region_Latin_America_and_Caribbean": latin_america,
                "Region_Middle_East_and_North_Africa": middle_east
            }
            
            backend_feature_name = FEATURE_MAPPING.get(compare_feature, compare_feature)
            
            with st.spinner("Saving graph..."):
                success, response = save_graph_to_backend(
                    user_id, 
                    graph_name, 
                    backend_feature_name,
                    x_min, x_max, steps,
                    feature_values
                )
                
                if success:
                    st.success(f"Graph '{graph_name}' saved successfully!")
                    # Clear the cached saved graphs so they refresh
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Failed to save graph: {response.get('error', 'Unknown error')}")
    
    # Clear button
    if st.button("🗑️ Clear Graph", use_container_width=True):
        st.session_state.graph_data = None
        if 'loaded_graph' in st.session_state:
            del st.session_state.loaded_graph
        st.rerun()

