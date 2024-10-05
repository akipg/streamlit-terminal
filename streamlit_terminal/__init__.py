import os
import logging

import streamlit.components.v1 as components

from .utils import get_terminal_instance

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
_RELEASE = True

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
    build_dir = os.path.join(parent_dir, "frontend-vue/dist")
    _component_func = components.declare_component(
        "st_terminal",
        path=build_dir
    )


# Create a wrapper function for the component. This is an optional
# best practice - we could simply expose the component function returned by
# `declare_component` and call it done. The wrapper allows us to customize
# our component's API: we can pre-process its input args, post-process its
# output value, and add a docstring for users.
def st_terminal(command="",
                key=None,
                height=360,
                min_height=-1,
                max_height=-1,
                disable_input=False,
                show_welcome_message=False,
                welcome_message=ASCII_ART,
                ):
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

    updated = terminal_instance.getUpdatedOutputs()
    logging.debug(f"Updated: {updated}")
    # logging.debug(f"Outputs: {terminal_instance.outputs}")
        

    # Call through to our private component function. Arguments we pass here
    # will be sent to the frontend, where they'll be available in an "args"
    # dictionary.
    #
    # "default" is a special argument that specifies the initial return
    # value of the component before the user has interacted with it.
    msg = _component_func(command=command,
                          disable_input=disable_input,
                          height=height,
                          min_height=min_height,
                          max_height=max_height,
                          show_welcome_message=show_welcome_message,
                          welcome_message=welcome_message,
                          is_running=terminal_instance.is_running,
                          history=terminal_instance.outputs,
                          run_count=terminal_instance.run_count,
                          key=key,
                          default={
                              "command": "initialized",
                              "args": [],
                              "kwargs": {}})
    logging.debug(f"Received value from component: {msg}")

    ret = terminal_instance.procMsg(msg)

    # We could modify the value returned from the component if we wanted.
    # There's no need to do this in our simple example - but it's an option.
    return terminal_instance.outputs, updated

