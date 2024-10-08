import subprocess
import threading
import shlex
import sys
import logging
import select
import time
import socket
import os
from queue import Queue

from .utils.session import get_browser_session_id, find_streamlit_main_loop, get_streamlit_session, notify
from .utils.thread import _Thread

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
        self.streamlit_loop = find_streamlit_main_loop()
        self.streamlit_session = get_streamlit_session(get_browser_session_id())

        # This can be called on any thread you want.
        # self.streamlit_loop.call_soon_threadsafe(notify)

    def __del__(self):
        logging.debug("DDDDDDDDDDDDDDD Deleting Terminal instance")
        self.terminate()

    def _read_stdbuffer(self, which_buf, q, process, read_interval=0.01, read_timeout=0.1, exit_event=None, force_exit_event=False, exiterbuf=None):
        # Get the stdbuffer
        if which_buf == "stdout":
            stdbuf = process.stdout
        elif which_buf == "stderr":
            stdbuf = process.stderr
        else:
            raise ValueError("Invalid buffer")
        
        # Start reading the buffer
        logging.debug(f"Start _read_stdbuffer for {which_buf} {process}, {q}")
        while process.poll() is None:

            # Check if exit event is set
            ### exit_eevnt: When fired, exit this thread after reading remaining buffer(stdout/stderr)
            ### force_exit_event: When fired, exit this thread **without** reading remaining buffer(stdout/stderr)
            if (exit_event is not None and not exit_event.is_set()) or (force_exit_event and force_exit_event.is_set()):
                logging.debug(f"Exit event set for {which_buf} {process}: exit_event: {exit_event}, force_exit_event: {force_exit_event}")
                break
            
            # Wait for the file descriptor to be ready for reading
            ready_to_read = False
            logging.debug(f"Polling {which_buf} for process {process}")
            logging.debug(f"Current qsize for process {process} is {q.qsize()}, {q}")
            if os.name == 'linux':
                if exiterbuf is None:
                    # Wait for the buffer to be ready
                    ready, _, _ = select.select([stdbuf], [], [], read_timeout)
                else:
                    # Wait for either buffer to be ready
                    ready, _, _ = select.select([stdbuf, exiterbuf], [], [], read_timeout)
                    # If exiter buffer is ready, break the loop
                    if exiterbuf in ready:
                        logging.debug(f"Exiter buffer ready for {which_buf} {process}")
                        break
                ready_to_read = stdbuf in ready
            else:
                # Windows does not support select for file descriptors
                # So we cannot set tiemout for reading stdout/stderr
                ready_to_read = True
            
            # Check if the buffer is ready
            if ready_to_read:
                # Read from the buffer
                out = stdbuf.readline()
                logging.debug(f"{process}: {which_buf.upper()}: {out}")
                if out:
                    # Put the read line to the queue
                    q.put({"type": f"{which_buf}", "value": out})
                    # Notify the main thread to update the UI
                    self.notify()

            # If exit event is set, break the loop
            if (exit_event is not None and not exit_event.is_set()) or (force_exit_event and force_exit_event.is_set()):
                break

            # Sleep for a while to avoid busy waiting
            time.sleep(read_interval) 
        
        # Read remaining
        if (force_exit_event and force_exit_event.is_set()):
            # Not to read remaining when force exit event is set
            pass
        else:
            # Read remaining
            logging.debug(f"Force exit event set for {which_buf} {process}")
            out = stdbuf.read()
            if out:
                # Put the read line to the queue
                logging.debug(f"{process}: {which_buf.upper()}(remaining): {out}")
                for o in out.splitlines():
                    q.put({"type": f"{which_buf}", "value": o})
            
        # Notify the main thread to update the UI
        self.notify()

        logging.debug(f"Finished thread _read_stdbuffer for {which_buf} finished {process}")

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
        for _which_buf in ("stdout", "stderr"):
            logging.debug(f"Starting thread for {_which_buf} {self._read_stdbuffer}")
            # _th = threading.Thread(target=self._read_stdbuffer, daemon=True,
            _th = _Thread(target=self._read_stdbuffer, daemon=True,
                                   args=(_which_buf,
                                         self.__queue,
                                         self.__process,))
            _th.start()
            self.__threads.append(_th)
            logging.debug(f"Append thread: idx {len(self.__threads)-1}")

    def run(self, cmd):
        logging.debug(f"Running subprocess: {cmd}")

        if self.__process is not None:
            logging.debug(f"Terminating existing process {self.__process}")
            self.terminate()

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
                self.terminate()
        elif command == "add_not_run_command":
            self.add_not_run_command(args[0])
        else:
            logging.error(f"Invalid command: {command}")
        
        return msg

    def notify(self):
        # Notify the main thread to update the UI
        self.streamlit_loop.call_soon_threadsafe(notify, self.streamlit_session)
    
    def terminate(self):
        if self.__process is not None and self.__process.poll() is None:
            logging.debug(f"Terminating process {self.__process}")
            self.__process.terminate()
        else:
            self.__process = None
        logging.debug(f"Number of threads: {len(self.__threads)}")
        self._check_threads_alive()
        for i, _th in enumerate(self.__threads):
            try:
                logging.debug(f"Terminating thread {_th}")
                _th.exit()
                del self.__threads[i]
            except:
                logging.warning(f"Error terminating thread {_th}")
                pass
        
        logging.debug(f"Number of threads after terminate: {len(self.__threads)}")
        
    def _check_threads_alive(self):
        for i, _th in enumerate(self.__threads):
            if not _th.is_alive():
                logging.debug(f"Thread {_th} is not alive")
            else:
                logging.warning(f"Thread_{i} {_th} is alive")

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
