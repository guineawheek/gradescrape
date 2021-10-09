import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

#with open("requirements.txt") as f:
#    reqs = f.read().splitlines()
reqs = ['requests', 'beautifulsoup4']

setuptools.setup(
    name="gradescrape",
    version="0.0.1r1",
    author="guineawheek",
    author_email="guineawheek@gmail.com",
    license="BSD",
    description="requests-based library to automatically provision assignments on Gradescope",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/guineawheek/gradescrape",
    packages=["gradescrape"],
    install_requires=reqs,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
    python_requires = ">=3.6",
)
