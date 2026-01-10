"""
Setup script for Mortgage Data Gathering Neural Network module
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="datagod-mortgage-nn",
    version="0.1.0",
    author="DataGod Team",
    author_email="datagod@example.com",
    description="Neural network for gathering mortgage data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/datagod/datagod",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.7",
    install_requires=[
        "numpy>=1.21.0",
        "pandas>=1.3.0",
        "scikit-learn>=1.0.0",
        "regex>=2021.8.0",
        "python-dateutil>=2.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.10.0",
        ],
        "ml": [
            "tensorflow>=2.8.0",
            "torch>=1.9.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "mortgage-nn-example=datagod.examples.mortgage_nn_example:main",
        ],
    },
)
