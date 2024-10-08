import streamlit as st
from ..terminal_lesser import TerminalLesser

def get_terminal_lesser_instance(key) -> TerminalLesser:
    if key in st.session_state:
        return st.session_state[key]
    else:
        st.session_state[key] = TerminalLesser(key)
        return st.session_state[key]
