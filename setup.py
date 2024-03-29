from setuptools import setup, find_packages

with open("README.md", "r") as f:
    readme = f.read()

setup(
    name='pydhcp3',
    version='0.0.5',
    license='MIT',
    author='Andrew Scott',
    author_email='imgurbot12@gmail.com',
    url='https://github.com/imgurbot12/pydhcp',
    description="Simple Python DHCP Library. DHCP Packet-Parsing/Client/Server",
    long_description=readme,
    long_description_content_type="text/markdown",
    python_requires='>=3.8',
    packages=find_packages(),
    install_requires=[
        'pyderive3>=0.0.6',
        'pystructs3>=0.0.7',
        'pyserve3>=0.0.7',
        'typing_extensions>=4.7.1',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ]
)
