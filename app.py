import streamlit as st
from streamlit_terminal import st_terminal

# set wide mode
st.set_page_config(layout="wide")


st.markdown("# Streamlit Terminal")

st.markdown("## Example 1: Basic Usage")

st_terminal(key="terminal1", show_welcome_message=True)


st.markdown("## Example 2: Custom Terminal")

st.markdown("### Auto height")
st.write("This terminal has a command `python -u test/clock.py` and height < 0 (auto height)")
st_terminal(key="terminal2", command="python -u test/clock.py", height=-1)

st.markdown("### Fixed height")
st.write("This terminal has a command `echo 'Hello World'` and height 200px")
st_terminal(key="terminal3", command="echo 'Hello World'", height=200)

st.markdown("### Set command from input")
st.write("This terminal has an external command input")
cmd = st.text_input("Command", "python -u test/clock.py")
st_terminal(key="terminal4", command=cmd, height=-1, disable_input=True)


st.markdown("## Example 3: Get Output from Terminal")

full_outputs, updated_outputs = st_terminal(key="terminal5",  command="python -u test/clock.py", height=-1)

st.markdown("### Updated outputs")
st.write(updated_outputs)

st.markdown("### Full outputs")
st.write(full_outputs)
