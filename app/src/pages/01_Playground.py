import logging
logger = logging.getLogger(__name__)

import streamlit as st
import requests
from modules.nav import SideBarLinks


# Page setup
st.set_page_config(layout='wide')

# Sidebar
SideBarLinks()

# Placeholder graph
st.image("assets/posts/placeholderGraph.gif", caption="GINI vs Population (example)")

# Columns for presets + controls
col1, col2, col3 = st.columns([0.75, 0.05, 0.2])

with col1:
    st.markdown("### Presets:")
    preset = st.selectbox("", ["USA (2022)", "France (2022)", "Germany (2022)"])

    st.markdown("")

    # Feature buttons — 4x3 grid
    feature_cols = st.columns(3)

    with feature_cols[0]:
        st.number_input("Population:")
        st.number_input("GDP per capita")
        st.number_input("Trade union density")
        st.number_input("Unemployment rate")

    with feature_cols[1]:
        st.number_input("Govt. spending")
        st.number_input("Education")
        st.number_input("Healthcare")
        st.number_input("Community spending")

    with feature_cols[2]:
        st.number_input("Productivity")
        st.number_input("Real interest rates")
        st.number_input("Corporate Tax Rate")
        st.number_input("Personal/property tax")

with col3:
    st.markdown("### Currently Comparing:")
    compare_feature = st.selectbox("Feature", [
        "Population", "GDP per capita", "Trade union density", 
        "Unemployment rate", "Govt. spending", "Education", 
        "Healthcare", "Community spending", "Productivity", 
        "Real interest rates", "Corporate Tax Rate", "Personal/property tax"
    ])

    st.text_input("Min:")
    st.text_input("Max:")
    st.text_input("Step:")