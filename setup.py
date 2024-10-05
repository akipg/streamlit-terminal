from pathlib import Path

import setuptools

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setuptools.setup(
    name="streamlit-terminal",
    version="0.0.1",
    author="akipg",
    author_email="akipg.dev@gmail.com",
    description="Run command and get realtime stdout/stderr output on streamlit (inprogress)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/akipg/streamlit-terminal",
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=[],
    python_requires=">=3.7",
    install_requires=[
        # By definition, a Custom Component depends on Streamlit.
        # If your component has other Python dependencies, list
        # them here.
        "streamlit >= 0.63",
    ],
)
