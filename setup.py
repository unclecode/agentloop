"""
Setup script for agentloop.
"""

from setuptools import setup, find_packages

setup(
    name="agentloop",
    version="0.1.0",
    description="A lightweight, transparent Python library for building AI assistants with OpenAI's API",
    author="MojitoFilms",
    packages=find_packages(),
    install_requires=[
        "openai>=1.0.0",
        "tiktoken>=0.5.0"
    ],
    dependency_links=[
        "git+https://github.com/unclecode/mem4ai.git#egg=mem4ai"
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)