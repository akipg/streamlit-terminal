import psutil

def get_child_processes():
    current_process = psutil.Process()
    children = current_process.children(recursive=True)
    return children

def kill_child_processes():
    children = get_child_processes()
    for child in children:
        child.terminate()
