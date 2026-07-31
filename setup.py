from setuptools import setup, find_packages

setup(
    name="quantrun-cli",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0",
        "sqlmodel>=0.0.14",
        "httpx>=0.24",
        "websockets>=11.0",
        "PyJWT>=2.8",
        "fastapi>=0.110",
        "uvicorn>=0.27",
    ],
    entry_points={
        "console_scripts": [
            "quantrun=quantrun.cli:cli",
        ],
    },
    python_requires=">=3.10",
)
