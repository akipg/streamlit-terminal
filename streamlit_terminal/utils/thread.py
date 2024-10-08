import threading
import socket
import logging

class _Thread:
    ### Constructor
    def __init__(self, target,  args=[], kwargs={}, daemon=True):
        # parameters
        self.__target = target
        self.__args = args
        self.__kwargs = kwargs
        self.__daemon = daemon

        # states
        self.__thread = None
        self.__exit_event = None
        self.__force_exit_event = None
        self.__exiterbuf_r = None
        self.__exiterbuf_w = None

    ### Initialize methods
    def _cleanup_states(self):
        self.__thread = None
        self.__exit_event = None
        self.__force_exit_event = None
        self.__exiterbuf_r = None
        self.__exiterbuf_w = None

    def _initialize_events_and_buf(self):
        # Prepare exit event
        self.__exit_event = threading.Event()
        self.__force_exit_event = threading.Event()
        # Prepare exiter buffer
        self.__exiterbuf_r, self.__exiterbuf_w = socket.socketpair()
        self.__exiterbuf_r.setblocking(False)
        self.__exiterbuf_w.setblocking(False)

    ### Thread methods
    def start(self):
        logging.debug(f"Starting thread {self.__thread}")
        self._initialize_events_and_buf()
        self.__kwargs_base = {
            "exit_event": self.__exit_event,
            "force_exit_event": self.__force_exit_event,
            "exiterbuf": self.__exiterbuf_r,
        }
        # self.__kwargs = self.__kwargs_base.update(self.__kwargs)
        self.__thread = threading.Thread(target=self.__target, args=self.__args, kwargs={**self.__kwargs_base, **self.__kwargs}, daemon=self.__daemon)
        self.__thread.start()

    def join(self):
        if self.__thread is not None:
            self.__thread.join()

    def is_alive(self):
        if self.__thread is None:
            return False
        else:
            return self.__thread.is_alive()

    ### Exit methods
    def set_exit_event(self, force=False):
        logging.debug(f"Setting exit event for thread {self.__thread}")
        if force:
            if self.__force_exit_event is not None:
                self.__force_exit_event.set()
            else:
                logging.warning(f"Force exit event is not set for thread {self.__thread}")
        if self.__exit_event is not None:
            self.__exit_event.set()
        else:
            logging.warning(f"Exit event is not set for thread {self.__thread}")
    
    def send_exit_signal(self):
        logging.debug(f"Sending exit signal for thread {self.__thread}")
        if self.__exiterbuf_w is not None:
            self.__exiterbuf_w.send(b"exit")
        else:
            logging.warning(f"Exiter buffer is not set for thread {self.__thread}")
    
    def close_socket(self):
        logging.debug(f"Closing socket for thread {self.__thread}")
        if self.__exiterbuf_r is not None:
            self.__exiterbuf_r.close()
        else:
            logging.warning(f"Exiter buffer reader is not set for thread {self.__thread}")
        if self.__exiterbuf_w is not None:
            self.__exiterbuf_w.close()    
        else:
            logging.warning(f"Exiter buffer writer is not set for thread {self.__thread}")    

    def exit(self, force=False):
        # Set exit event
        self.set_exit_event(force=force)
        # Send exit signal
        self.send_exit_signal()
        # Wait for the thread to exit
        self.join()
        # Close the socket
        self.close_socket()
        # Clean up
        self._cleanup_states()

    ### Destructor
    def __del__(self):
        self.exit(force=True)

    ### Properties
    def __repr__(self) -> str:
        return f"<_Thread: {self.__thread}>"

