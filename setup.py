from setuptools import setup, find_packages

setup(
    name="jira-app",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        line.strip()
        for line in open("requirements.txt").readlines()
        if not line.startswith("#")
    ],
)
