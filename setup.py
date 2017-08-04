from setuptools import setup, find_packages

setup(
    name="mechanic",
    packages=["mechanic"],
    version="0.1.0",
    description="Generates python code from the controller layer to the DB layer from an OpenAPI specification file.",
    author="Zack Schrag",
    author_email="zack.schrag@factioninc.com",
    url="https://github.com/factioninc/mechanic",
    download_url="https://github.com/factioninc/mechanic/archive/0.1.0",
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
    install_requires=[
        "docopt==0.6.2",
        "inflect==0.2.5",
        "itsdangerous==0.24",
        "Jinja2==2.9.6"
    ],
    include_package_data=True
)
