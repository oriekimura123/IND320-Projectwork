# File: streamlit/utils/setup.py
from setuptools import setup, find_packages

setup(
    name="common_utils", # Choose a descriptive name, e.g., 'common_utils' or 'my_utils'
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        # List any dependencies that ONLY your utilities need here
    ],
)
