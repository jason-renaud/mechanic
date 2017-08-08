from setuptools import setup, find_packages

setup(
    name="mechanic-gen",
    packages=["mechanic"],
    version="0.1.1",
    description="Generates python code from the controller layer to the DB layer from an OpenAPI specification file.",
    author="Zack Schrag",
    author_email="zack.schrag@factioninc.com",
    url="https://github.com/factioninc/mechanic",
    download_url="https://github.com/factioninc/mechanic/archive/0.1.1.tar.gz",
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
