import os
from setuptools import setup, find_packages

with open(os.path.join("", "mechanic/VERSION")) as version_file:
    current_version = version_file.read().strip()

setup(
    name="mechanic-gen",
    packages=["mechanic"],
    version="%s" % current_version,
    description="Generates python code from the controller layer to the DB layer from an OpenAPI specification file.",
    author="Zack Schrag",
    author_email="zack.schrag@factioninc.com",
    url="https://github.com/factioninc/mechanic",
    download_url="https://github.com/factioninc/mechanic/archive/%s.tar.gz" % current_version,
    keywords=["openapi", "api", "generation"],
    license="Mozilla Public License 2.0 (MPL 2.0)",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Programming Language :: Python :: 3.6",
    ],
    entry_points={
        "console_scripts": [
            "mechanic=mechanic.main:main",
        ],
    },
    install_requires=[
        "docopt==0.6.2",
        "inflect==0.2.5",
        "itsdangerous==0.24",
        "Jinja2==2.10",
        "PyYAML==3.12",
        "yamlordereddictloader==0.4.0"
    ],
    include_package_data=True
)
