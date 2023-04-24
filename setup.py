from setuptools import setup, find_packages

with open("README.md", "r") as f:
    readme = f.read()

setup(
    name='pydhcp3',
    version='0.0.1',
    license='MIT',
    author='Andrew Scott',
    author_email='imgurbot12@gmail.com',
    url='https://github.com/imgurbot12/pydhcp',
    description="Simple Python DHCP Library. DHCP Packet-Parsing/Client/Server",
    long_description=readme,
    long_description_content_type="text/markdown",
    python_requires='>=3.6',
    packages=find_packages(),
    install_requires=[
        'pystructs3',
        'dataclasses',
        'typing_extensions'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ]
)
