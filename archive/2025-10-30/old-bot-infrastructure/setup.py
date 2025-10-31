from setuptools import setup, find_packages

setup(
    name="pacifica-trading-bot",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "requests",
        "python-dotenv",
        "solders",
        "lighter-v3-python @ git+https://github.com/elliottech/lighter-v3-python.git",
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "pacifica-bot=pacifica.bots.pacifica_bot:main",
            "lighter-bot=pacifica.bots.lighter_bot:main",
        ],
    },
)
