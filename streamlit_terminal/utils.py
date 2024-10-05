import gc
import asyncio
import threading
from streamlit.runtime.app_session import AppSession
from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx
from streamlit.runtime.runtime import Runtime

import streamlit as st
from .terminal import Terminal

def get_terminal_instance(key) -> Terminal:
    if key in st.session_state:
        return st.session_state[key]
    else:
        st.session_state[key] = Terminal(key)
        return st.session_state[key]


### Streamlit utils
def get_browser_session_id() -> str:
    # Get the session_id for the current running script 
    try:
        ctx = get_script_run_ctx()
        return ctx.session_id
    except Exception as e:
        raise Exception("Could not get browser session id") from e
        
def find_streamlit_main_loop() -> asyncio.BaseEventLoop:
    loops = []
    for obj in gc.get_objects():
        try:
            if isinstance(obj, asyncio.BaseEventLoop):
                loops.append(obj)
        except ReferenceError:
            ...
        
    main_thread = next((t for t in threading.enumerate() if t.name == 'MainThread'), None)
    if main_thread is None:
        raise Exception("No main thread")
    main_loop = next((lp for lp in loops if lp._thread_id == main_thread.ident), None) # type: ignore
    if main_loop is None:
        raise Exception("No event loop on 'MainThread'")
    
    return main_loop
    
def get_streamlit_session(session_id: str) -> AppSession:
    runtime: Runtime = Runtime.instance()
    session = next((
        s.session
        for s in runtime._session_mgr.list_sessions()
        if s.session.id == session_id
    ), None)
    if session is None:
        raise Exception(f"Streamlit session not found for {session_id}")
    return session

def notify(streamlit_session) -> None:
    # this didn't work when I passed it in directly, I didn't really think too much about why not
    streamlit_session._handle_rerun_script_request()
