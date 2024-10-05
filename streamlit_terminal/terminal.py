

import streamlit as st
import subprocess
import threading
import shlex
import sys
import logging
from queue import Queue

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
        self.__run_count = 0

        Terminal.static_instance_id += 1
        self.__id = Terminal.static_instance_id

        # https://github.com/streamlit/streamlit/issues/2838#issuecomment-1738983577
        # This is it!
        # get_browser_session_id needs to be run on the relevant script thread,
        # then you can call the rest of this on other threads.
        from .utils import get_browser_session_id, find_streamlit_main_loop, get_streamlit_session, notify
        self.streamlit_loop = find_streamlit_main_loop()
        self.streamlit_session = get_streamlit_session(get_browser_session_id())

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
                self.notify()
        
        # Read remaining
        out = stdbuf.read()
        if out:
            logging.debug(f"{process}: {which_buf.upper()}(remaining): {out}")
            for o in out.splitlines():
                q.put({"type": f"{which_buf}", "value": o})
        logging.debug(f"Finished thread _read_stdbuffer for {which_buf} finished {process}")
        
        self.notify()

    def _watch_queue(self):
        logging.debug(f"Start watching queue for process {self.__process}, Queue: {self.__queue}")
        while self.__process.poll() is None:
            if self.__queue.qsize() > 0:
                logging.debug(f"Notify Queue: size: {self.__queue.qsize()}")
                # self.__outputs.append(self.__queue.get_nowait())
                self.notify()
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
        self.__run_count += 1

        # Start new process
        try:
            if sys.platform == 'win32':
                self.__process = subprocess.Popen(shlex.split(cmd),
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True,
                                    bufsize=1)
            else:
                self.__process = subprocess.Popen(shlex.split(cmd),
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True,
                                    bufsize=1,)
        except Exception as e:
            logging.error(f"Error starting process: {e}")
            self.__outputs.append({
                "type": "stderr",
                "value": str(e)
            })
            self.notify()
            return
            
        # self.__outputs = []

        self._start_watch_stdout_stderr()

    # def attach(self, pid):
    #     logging.debug(f"Attaching to process {pid}")
    #     self.__process = psutil.Process(pid)
    #     logging.debug(f"Attached to process {self.__process}")
    #     self._start_watch_stdout_stderr()

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
        self.notify()

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

    def procMsg(self, msg):
        try:
            command = msg["command"]
            args = msg["args"]
            kwargs = msg["kwargs"]
        except:
            logging.error("Invalid message received")
            return msg

        is_new_msg = self.addCommandHash(msg)
        if not is_new_msg:
            logging.debug(f"Command already run: {msg}")
            return {}
        
        if command == "initialized":
            pass
        elif command == "run_command":
            logging.debug(f"Running command: {args[0]}")
            self.run(args[0])
        elif command == "terminate_process":
            if self.process:
                logging.debug(f"Terminating process {self.process}")
                self.process.terminate()
        elif command == "add_not_run_command":
            self.add_not_run_command(args[0])
        else:
            logging.error(f"Invalid command: {command}")
        
        return msg

    def notify(self):
        from .utils import notify
        self.streamlit_loop.call_soon_threadsafe(notify, self.streamlit_session)
        
 
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
    
    @property
    def is_running(self):
        return self.__process is not None and self.__process.poll() is None
    
    @property
    def outputs(self):
        return self.__outputs
    
    @property
    def run_count(self):
        return self.__run_count


