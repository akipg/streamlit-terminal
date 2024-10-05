import streamlit as st
from streamlit_terminal import st_terminal

# set wide mode
st.set_page_config(layout="wide")


st.markdown("# Streamlit Terminal")

st.markdown("## Example 1: Basic Usage")

st_terminal("World", key="terminal1")


st.markdown("## Example 2: Custom Terminal")

# st_terminal("Hello", key="terminal2", terminal="iterm")
st_terminal("Hello", key="terminal2")

