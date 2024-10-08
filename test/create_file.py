from pathlib import Path
import os

p = Path(__file__)
print("script location:", p.absolute())

# Create a file
file = (p.parent/".."/"test.txt").resolve()
with open(file, "w") as f:
    f.write("Hello, World!")

print("file created:", file.absolute())

