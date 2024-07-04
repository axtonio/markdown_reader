from setuptools import setup, find_packages


with open("README.md", "r", encoding="utf-8") as f:
    more_description = f.read()


setup(
    name="markdown_reader",
    version="2.0.0",
    author="Antonio Rodrigues",
    author_email="antonio.projects.studio@gmail.com",
    description="Library to work with markdown",
    long_description=more_description,
    long_description_content_type="text/markdown",
    url="ssh://github.com/antonio-projects-studio/markdown_reader",
    packages=find_packages(),
    install_requires=[
        "PyYAML",
        "python-frontmatter",
    ],
)
