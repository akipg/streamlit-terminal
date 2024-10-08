import streamlit as st
from streamlit_terminal import st_terminal

# Set wide mode
st.set_page_config(layout="wide")

# Set debug mode
if st.query_params.get("debug"):
    import logging
    logging.basicConfig(level=logging.DEBUG)

st.markdown("🚧 **Work in Progress** 🚧")

st.markdown("# Streamlit Terminal")

# Example 1: Basic Usage
st.markdown("## Example 1: Basic Usage")
st.write("Use this terminal to execute commands.")
st.write("For example, type `ls` after the `>` prompt and press `Enter` to run the command.")
st_terminal(key="terminal1", show_welcome_message=True)

st.markdown("""
            ```python
            # Source code of the above example
            from streamlit_terminal import st_terminal
            st_terminal(key="terminal1", show_welcome_message=True)
            ```""")

# Example 2: Custom Terminal
st.markdown("## Example 2: Custom Terminal")

st.markdown("### Set a Command from Input")
st.write("In this terminal, you can't type commands directly, but you can set a custom command using the `command` parameter.")
st.write("Click the |> button at the top-right of the terminal to run the command.")
cmd = st.text_input("Command", "python -u test/clock.py")
st_terminal(key="terminal4", command=cmd, height=-1, max_height=250, disable_input=True)

# Example 3: Get Output from Terminal
st.markdown("## Example 3: Get Output from Terminal")

full_outputs, updated_outputs = st_terminal(key="terminal5", command="python -u test/clock.py", height=200)

with st.container(height=500):
    cols = st.columns(2)
    with cols[0]:
        st.markdown("### Full Outputs")
        st.write(full_outputs)

    with cols[1]:
        st.markdown("### Updated Outputs")
        st.write(updated_outputs)


# Example 4: Colorful Output
st.markdown("## Example 4: Colorful Output")
st.write("This terminal displays colorful output.")
colorful_command = st.text_input("Colorful command", r'''echo -e "\x1b[31mError: Something went wrong\x1b[0m" && 
echo -e "\x1b[33mWarning: Check your configuration\x1b[0m" && 
echo -e "\x1b[32mSuccess: Operation completed successfully\x1b[0m"''')
st_terminal(key="terminal2", command=colorful_command, height=-1)
