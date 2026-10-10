from setuptools import setup, find_packages

setup(
    name="streamvid",
    version="1.0.0",
    author="IamJony",
    author_email="tu@email.com",
    description="Video extractor from multiple streaming platforms",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/IamJony/streamvid",
    packages=find_packages(exclude=("tests", "tests.*")),
    python_requires=">=3.8",
    install_requires=[
        "requests_html",
        "real_headers",
        "lxml_html_clean",
    ],
    entry_points={
        "console_scripts": [
            "streamvid=streamvid.main:main",
        ],
    },
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
