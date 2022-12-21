import os

from setuptools import find_packages, setup


def readme() -> str:
    """Utility function to read the README.md.

    Used for the `long_description`. It's nice, because now
    1) we have a top level README file and
    2) it's easier to type in the README file than to put a raw string in below.

    Args:
        nothing

    Returns:
        String of readed README.md file.
    """
    return open(os.path.join(os.path.dirname(__file__), "README.md")).read()


setup(
    name="rayduino",
    version="0.1.0",
    author="Tom Roseberry",
    author_email="tomkroseberry@gmail.com",
    description="Parallelized data acquisition using Arduino's and Ray",
    python_requires=">=3.7",
    license="MIT",
    url="https://github.com/tomkr000/rayduino",
    packages=find_packages(),
    long_description=readme(),
)