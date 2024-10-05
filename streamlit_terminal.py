import streamlit as st
import subprocess
import threading
import psutil
import time
import shlex
import sys

from queue import Queue

import logging

import gc
import asyncio
from streamlit.runtime.app_session import AppSession
from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx, add_script_run_ctx
from streamlit.runtime.runtime import Runtime

def get_terminal_instance(key):
    if key in st.session_state:
        return st.session_state[key]
    else:
        st.session_state[key] = Terminal(key)
        return st.session_state[key]

def st_terminal(key, *args, **kwargs) -> None:   
    get_terminal_instance(key).component(*args, **kwargs)



class Terminal:
    static_instance_id = 0

    def __init__(self, key) -> None:
        logging.debug("IIIIIIIIIIIIIIII Initializing Terminal instance")
        self.__key = key
        self.__process = None
        self.__queue = None
        self.__outputs = []
        self.__threads = []
        self.cmd = ""

        Terminal.static_instance_id += 1
        self.__id = Terminal.static_instance_id

        # https://github.com/streamlit/streamlit/issues/2838#issuecomment-1738983577
        # This is it!
        # get_browser_session_id needs to be run on the relevant script thread,
        # then you can call the rest of this on other threads.
        self.streamlit_loop = self.find_streamlit_main_loop()
        self.streamlit_session = self.get_streamlit_session(self.get_browser_session_id())

        # This can be called on any thread you want.
        # self.streamlit_loop.call_soon_threadsafe(notify)

    def __del__(self):
        logging.debug("DDDDDDDDDDDDDDD Deleting Terminal instance")
        for _th in self.__threads:
            _th.join()

    def _read_stdout(self, q, process):
        logging.debug(f"Start _read_stdout for {process}, {q}")
        while process.poll() is None:
            
            logging.debug(f"Polling stdout for process {process}")
            logging.debug(f"Current qsize for process {process} is {q.qsize()}, {q}")
            out = process.stdout.readline()
            logging.debug(f"{process}: STDOUT: {out}")
            q.put(out)
            self.streamlit_loop.call_soon_threadsafe(self.notify)
        
        # Read remaining
        out = process.stdout.read()
        logging.debug(f"{process}: STDOUT(remaining): {out}")
        q.put(out)

        logging.debug(f"Thread _read_stdout finished {process}")

    def _read_stderr(self, q, process):
        logging.debug(f"Start _read_stderr for {process}, {q}")
        while process.poll() is None:
            
            logging.debug(f"Polling stderr for process {process}")
            logging.debug(f"Current qsize for process {process} is {q.qsize()}, {q}")
            out = process.stderr.readline()
            logging.debug(f"{process}: STDERR: {out}")
            q.put(out)
            self.streamlit_loop.call_soon_threadsafe(self.notify)

        # Read remaining
        out = process.stdout.read()
        logging.debug(f"{process}: STDOUT(remaining): {out}")
        q.put(out)
        
        logging.debug(f"Thread _read_stderr finished {process}")


    def _watch_queue(self):
        logging.debug(f"Start watching queue for process {self.__process}, Queue: {self.__queue}")
        while self.__process.poll() is None:
            if self.__queue.qsize() > 0:
                logging.debug(f"Notify Queue: size: {self.__queue.qsize()}")
                # self.__outputs.append(self.__queue.get_nowait())
                self.streamlit_loop.call_soon_threadsafe(self.notify)
        logging.debug(f"Thread _watch_queue finished {self.__process}")
    

    def _start_watch_stdout_stderr(self):
        self.__queue = Queue()

        # Start reading stdout
        logging.debug(f"Starting reading stdout for process {self.__process}, Queue: {self.__queue}")
        self.__threads = []
        self.__threads.append(
            threading.Thread(target=self._read_stdout,
                             args=(self.__queue,
                                   self.__process,))
        )
        
        # Start reading stderr
        self.__threads.append(
             threading.Thread(target=self._read_stderr,
                              args=(self.__queue,
                                    self.__process,))
        )

        
        # Watch queue
        # self.__threads.append(
        #     threading.Thread(target=self._watch_queue)
        # )

        for _th in self.__threads:
            _th.start()


    def run(self, cmd):
        logging.debug(f"Running subprocess: {cmd}")

        # Check if process is running
        if self.__process is not None:
            logging.debug(f"Terminating existing process {self.__process}")
            if self.__process.poll() is None:
                logging.debug("Process is running")
        else:
            logging.debug("No existing process")

        # Start new process
        if sys.platform == 'win32':
            self.__process = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                bufsize=1)
        else:
            self.__process = subprocess.Popen(shlex.split("exec "+cmd),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                bufsize=1,
                                preexec_fn=os.setsid)
        
        self.__outputs = []

        self._start_watch_stdout_stderr()

    def attach(self, pid):
        logging.debug(f"Attaching to process {pid}")
        self.__process = psutil.Process(pid)
        logging.debug(f"Attached to process {self.__process}")
        self._start_watch_stdout_stderr()

    

    @st.fragment
    def component(self, value, key=None):
        if key is None:
            key = self.__key

        is_running = self.__process is not None and self.__process.poll() is None

        logging.debug(f"Rendering component for Terminal instance {self.__process}, Queue: {self.__queue}")
        st.write(self.__queue)

        self.cmd = st.text_input("Command", value=value, key=key+"_text_input_cmd")

        # Run button
        if st.button("Run" if not is_running else "Running...", key=key+"_button_run", disabled=is_running) and self.cmd is not None:
            logging.debug(f"Running command: {self.cmd}")
            self.run(self.cmd.split(" "))
            # st.rerun(scope="fragment")

        with st.expander("Attach to existing process (experimental)"):
            pid = st.number_input("PID", key=key+"_number_input_pid", value=0)
            if st.button("Attach", key=key+"_button_attach", disabled=is_running):
                self.attach(pid)
                # st.rerun(scope="fragment")

        # Terminate button
        if st.button("Terminate", key=key+"_button_terminate", disabled=not is_running) and self.__process:
            if self.__process is not None and self.__process.poll() is None:
                logging.debug(f"Terminating process {self.__process}")
                self.__process.terminate()
                st.rerun(scope="fragment")

        # Get stdout/stderr
        if self.__queue is not None and self.__queue.qsize() > 0:
            while not self.__queue.empty():
                out = self.__queue.get_nowait()
                self.__outputs += out.splitlines()
        
        # Output
        st.write("  \n  ".join(self.__outputs))

    @property
    def process(self):
        return self.__process
    
    @property
    def queue(self):
        return self.__queue
    
    @property
    def outputs(self):
        return self.__outputs
    
    @property
    def id(self):
        return str(self.__id)



    def get_browser_session_id(self) -> str:
        # Get the session_id for the current running script 
        try:
            ctx = get_script_run_ctx()
            return ctx.session_id
        except Exception as e:
            raise Exception("Could not get browser session id") from e
            
    def find_streamlit_main_loop(self) -> asyncio.BaseEventLoop:
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
        
    def get_streamlit_session(self, session_id: str) -> AppSession:
        runtime: Runtime = Runtime.instance()
        session = next((
            s.session
            for s in runtime._session_mgr.list_sessions()
            if s.session.id == session_id
        ), None)
        if session is None:
            raise Exception(f"Streamlit session not found for {session_id}")
        return session

    def notify(self) -> None:
        # this didn't work when I passed it in directly, I didn't really think too much about why not
        self.streamlit_session._handle_rerun_script_request()
        # self.streamlit_session._handle_rerun_script_request(self.streamlit_session._client_state)

