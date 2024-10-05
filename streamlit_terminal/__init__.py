import os
import logging

import streamlit.components.v1 as components

ASCII_ART= r"""
         __                            ___ __        __                      _             __
   _____/ /_________  ____ _____ ___  / (_) /_      / /____  _________ ___  (_)___  ____ _/ /
  / ___/ __/ ___/ _ \/ __ `/ __ `__ \/ / / __/_____/ __/ _ \/ ___/ __ `__ \/ / __ \/ __ `/ / 
 (__  ) /_/ /  /  __/ /_/ / / / / / / / / /_/_____/ /_/  __/ /  / / / / / / / / / / /_/ / /  
/____/\__/_/   \___/\__,_/_/ /_/ /_/_/_/\__/      \__/\___/_/  /_/ /_/ /_/_/_/ /_/\__,_/_/   

"""[1:]

# Create a _RELEASE constant. We'll set this to False while we're developing
# the component, and True when we're ready to package and distribute it.
# (This is, of course, optional - there are innumerable ways to manage your
# release process.)
_RELEASE = False

# Declare a Streamlit component. `declare_component` returns a function
# that is used to create instances of the component. We're naming this
# function "_component_func", with an underscore prefix, because we don't want
# to expose it directly to users. Instead, we will create a custom wrapper
# function, below, that will serve as our component's public API.

# It's worth noting that this call to `declare_component` is the
# *only thing* you need to do to create the binding between Streamlit and
# your component frontend. Everything else we do in this file is simply a
# best practice.

if not _RELEASE:
    logging.basicConfig(level=logging.DEBUG)
    _component_func = components.declare_component(
        # We give the component a simple, descriptive name ("my_component"
        # does not fit this bill, so please choose something better for your
        # own component :)
        "st_terminal",
        # Pass `url` here to tell Streamlit that the component will be served
        # by the local dev server that you run via `npm run start`.
        # (This is useful while your component is in development.)
        url="http://localhost:5173",
    )
else:
    # When we're distributing a production version of the component, we'll
    # replace the `url` param with `path`, and point it to the component's
    # build directory:
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(parent_dir, "frontend/dist")
    _component_func = components.declare_component(
        "st_terminal",
        path=build_dir
    )


# Create a wrapper function for the component. This is an optional
# best practice - we could simply expose the component function returned by
# `declare_component` and call it done. The wrapper allows us to customize
# our component's API: we can pre-process its input args, post-process its
# output value, and add a docstring for users.
def st_terminal(name, key=None):
    """Create a new instance of "my_component".

    Parameters
    ----------
    name: str
        The name of the thing we're saying hello to. The component will display
        the text "Hello, {name}!"
    key: str or None
        An optional key that uniquely identifies this component. If this is
        None, and the component's arguments are changed, the component will
        be re-mounted in the Streamlit frontend and lose its current state.

    Returns
    -------
    int
        The number of times the component's "Click Me" button has been clicked.
        (This is the value passed to `Streamlit.setComponentValue` on the
        frontend.)

    """

    terminal_instance = get_terminal_instance(key+"_instance")
    logging.debug(f"Terminal instance: {terminal_instance}")

    history = [
        { "type": "stdout", "value": "asdasd world" },
        { "type": "stdout", "value": "Hello world" },
        { "type": "stdout", "value": "Hello world" },
        { "type": "stdout", "value": "\x1b[0m \x1b[90m 5 |\x1b[39m \x1b[36mfunction\x1b[39m draw() {\x1b[0m" },
        { "type": "stdout", "value": "\x1b[0m \x1b[90m 6 |\x1b[39m   \x1b[36mbackground\x1b[39m(220);\x1b[0m" },
    ]

    updated = terminal_instance.getUpdatedOutputs()
    logging.debug(f"Updated: {updated}")
    # logging.debug(f"Outputs: {terminal_instance.outputs}")
        

    # Call through to our private component function. Arguments we pass here
    # will be sent to the frontend, where they'll be available in an "args"
    # dictionary.
    #
    # "default" is a special argument that specifies the initial return
    # value of the component before the user has interacted with it.
    msg = _component_func(name=name,
                          is_running=terminal_instance.is_running,
                          welcome_message=ASCII_ART,
                        #   history=history,
                          history=terminal_instance.outputs,
                          key=key,
                          default={
                              "command": "initialized",
                              "args": [],
                              "kwargs": {}})
    logging.debug(f"Received value from component: {msg}")




    try:
        command = msg["command"]
        args = msg["args"]
        kwargs = msg["kwargs"]
    except:
        logging.error("Invalid message received")
        return msg

    is_new_msg = terminal_instance.addCommandHash(msg)
    if not is_new_msg:
        logging.debug(f"Command already run: {msg}")
        return {}
    
    if command == "initialized":
        pass
    elif command == "run_command":
        logging.debug(f"Running command: {args[0]}")
        terminal_instance.run(args[0])
    elif command == "terminate_process":
        if terminal_instance and terminal_instance.process:
            logging.debug(f"Terminating process {terminal_instance.process}")
            terminal_instance.process.terminate()
    elif command == "add_not_run_command":
        terminal_instance.add_not_run_command(args[0])
        ...
    else:
        logging.error(f"Invalid command: {command}")

    # We could modify the value returned from the component if we wanted.
    # There's no need to do this in our simple example - but it's an option.
    return msg



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

def st_terminal_(key, *args, **kwargs) -> None:   
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
        self.__command_hashs = set()

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

    def _read_stdbuffer(self, which_buf, q, process):
        if which_buf == "stdout":
            stdbuf = process.stdout
        elif which_buf == "stderr":
            stdbuf = process.stderr
        else:
            raise ValueError("Invalid buffer")
        
        logging.debug(f"Start _read_stdbuffer for {which_buf} {process}, {q}")
        while process.poll() is None:
            
            logging.debug(f"Polling {which_buf} for process {process}")
            logging.debug(f"Current qsize for process {process} is {q.qsize()}, {q}")
            stdbuf.flush()
            out = stdbuf.readline()
            if out:
                logging.debug(f"{process}: {which_buf.upper()}: {out}")
                q.put({"type": f"{which_buf}", "value": out})
                self.streamlit_loop.call_soon_threadsafe(self.notify)
        
        # Read remaining
        out = stdbuf.read()
        if out:
            logging.debug(f"{process}: {which_buf.upper()}(remaining): {out}")
            for o in out.splitlines():
                q.put({"type": f"{which_buf}", "value": o})
        logging.debug(f"Finished thread _read_stdbuffer for {which_buf} finished {process}")
        
        self.streamlit_loop.call_soon_threadsafe(self.notify)

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
            threading.Thread(target=self._read_stdbuffer,
                             args=("stdout",
                                   self.__queue,
                                   self.__process,))
        )
        
        # Start reading stderr
        self.__threads.append(
             threading.Thread(target=self._read_stdbuffer,
                             args=("stderr",
                                   self.__queue,
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

        if type(cmd) == list:
            " ".join(cmd)

        self.__outputs.append({
            "type": "command",
            "value": cmd,
        })

        # Start new process
        try:
            if sys.platform == 'win32':
                self.__process = subprocess.Popen(shlex.split(cmd),
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True,
                                    bufsize=1)
            else:
                self.__process = subprocess.Popen(shlex.split(["exec"]+cmd),
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True,
                                    bufsize=1,
                                    preexec_fn=os.setsid)
        except Exception as e:
            logging.error(f"Error starting process: {e}")
            self.__outputs.append({
                "type": "stderr",
                "value": str(e)
            })
            self.streamlit_loop.call_soon_threadsafe(self.notify)
            return
            
        # self.__outputs = []

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

    def getUpdatedOutputs(self):
        outs = []
        if self.__queue is not None:
            logging.debug(f"Getting updated outputs for process {self.__process}, queue: {self.__queue}, size: {self.__queue.qsize()}")
            while self.__queue is not None and not self.__queue.empty():
                out = self.__queue.get_nowait()
                logging.debug(f"Getting updated outputs: {out}")
                outs += [out]
        self.__outputs += outs
        return outs

    def add_not_run_command(self, cmd):
        logging.debug(f"Adding not run command: {cmd}")
        self.__outputs.append({
            "type": "command",
            "not_run": True,
            "value": cmd
        })
        self.streamlit_loop.call_soon_threadsafe(self.notify)

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
    
    @property
    def is_running(self):
        return self.__process is not None and self.__process.poll() is None
    
    @property
    def outputs(self):
        return self.__outputs



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


    def _generateHashFromMsg(self, msg):
        keys = list(msg.keys())
        keys.sort()
        h = ""
        for k in keys:
            h += str(f"{k}:{msg[k]}")               
        return hash(h)

    def checkIfCommandAlreadyRun(self, msg):
        msg_hash = self._generateHashFromMsg(msg)
        return msg_hash in self.__command_hashs

    def requestRunCommand(self, msg):
        msg_hash = self._generateHashFromMsg(msg)
        if msg_hash not in self.__command_hashs:
            self.__command_hashs.add(msg_hash)
            cmd = msg["args"][0].split(" ")
            self.run(cmd)
            return True
        return False
    
    def addCommandHash(self, msg):
        msg_hash = self._generateHashFromMsg(msg)
        is_new_msg = msg_hash not in self.__command_hashs
        self.__command_hashs.add(msg_hash)
        return is_new_msg



def get_terminal_instance(key) -> Terminal:
    if key in st.session_state:
        return st.session_state[key]
    else:
        st.session_state[key] = Terminal(key)
        return st.session_state[key]