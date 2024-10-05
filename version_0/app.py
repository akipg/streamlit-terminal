import streamlit as st
import subprocess
import threading
import time

from notifier import notify

from queue import Queue

def run_subprocess(q, process):
    while process.poll() is None:
        line = process.stdout.readline()
        if line:
            print(line)
            q.put(line)
            notify()

if st.button("Start Process") and "process" not in st.session_state:
    print("Starting process")
    st.session_state.process = subprocess.Popen(["python", "-u", "clock.py"],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               text=True,
                               bufsize=1)
    
    st.session_state.queue = Queue()
    st.session_state.stdout = []

    thread = threading.Thread(target=run_subprocess,
                              args=(st.session_state.queue,
                                    st.session_state.process,))
    thread.start()

if "queue" in st.session_state:
    if st.session_state.queue.qsize() > 0:
        st.session_state.stdout.append(st.session_state.queue.get_nowait())
        st.write(st.session_state.stdout)
    

if st.button("Terminate"):
    st.session_state.process.terminate()
    del st.session_state.process

