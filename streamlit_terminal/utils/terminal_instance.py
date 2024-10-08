import streamlit as st
from ..terminal import Terminal

def get_terminal_instance(key) -> Terminal:
    if key in st.session_state:
        return st.session_state[key]
    else:
        st.session_state[key] = Terminal(key)
        return st.session_state[key]
