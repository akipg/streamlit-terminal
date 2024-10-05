import streamlit as st
from streamlit_terminal import st_terminal

import logging

logging.basicConfig(level=logging.DEBUG)

import psutil

from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx
ctx = get_script_run_ctx()
st.write(ctx.session_id)


with st.sidebar:
    current_process = psutil.Process()
    children = current_process.children(recursive=True)
    if st.button("Terminate all child processes"):
        for child in children:
            child.terminate()
            
    for child in children:
        logging.debug('Child pid is {}'.format(child.pid))
        st.write(f'Child pid {child.pid}  \n  {child.exe()} {child.cmdline()}')
        

    st.write(st.session_state)


st_terminal(key="terminal1", value="python -u test/clock.py")

st_terminal(key="terminal2", value="ls -la")

st_terminal(key="terminal3", value=r"C:\cygwin64\bin\stdbuf.exe -o0 cmd.exe /c test\c.bat ")

