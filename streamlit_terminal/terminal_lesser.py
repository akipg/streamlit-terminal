

import streamlit as st
import logging
from .terminal import Terminal

class TerminalLesser(Terminal):
    def __init__(self, key):
        super().__init__(key=key)

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
