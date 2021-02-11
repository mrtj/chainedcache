import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="chainedcache", # Replace with your own username
    version="0.0.1",
    author="Janos Tolgyesi",
    author_email="janos.tolgyesi@gmail.com",
    description="A simple cache in python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mrtj/chainedcache",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(),
    python_requires='>=3.6',
)
