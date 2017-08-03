from distutils.core import setup

setup(
    name="mechanic",
    packages=["starter_files", "templates"],
    version="0.1.0",
    description="Generates python code from the controller layer to the DB layer from an OpenAPI specification file.",
    author="Zack Schrag",
    author_email="zack.schrag@factioninc.com",
    url="https://github.com/factioninc/mechanic",
    download_url="https://github.com/factioninc/mechanic/archive/0.1.1.tar.gz",
    keywords=["openapi", "api", "generation"],
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
    ],
    entry_points={
        "console_scripts": [
            "mechanic=mechanic:main",
        ],
    },
)
