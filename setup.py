from setuptools import setup, find_packages


with open("README.md", "r", encoding="utf-8") as f:
    more_description = f.read()


setup(
    name="markdown_reader",
    version="2.0.0",
    author="Antonio Rodrigues",
    author_email="axtonio.code@gmail.com",
    description="Library to work with markdown",
    long_description=more_description,
    long_description_content_type="text/markdown",
    url="https://github.com/axtonio/markdown_reader",
    package_data={
        # Если файл находится внутри пакета
        "markdown_reader": ["**/*.css"],
    },
    packages=find_packages(),
    install_requires=[
        "PyYAML~=6.0.2",
        "pdfkit~=1.0.0",
        "pypandoc~=1.15",
        "python-frontmatter~=1.1.0",
        "terminal_app @ git+https://github.com/axtonio/terminal_app.git@v1.0.3",
    ],
)
