import setuptools

SHORT_DISCRIPTION = 'This is a library that bridges '\
    'server-side python and browser-side javascript.'
with open('README.md', encoding='utf-8') as f:
    long_description = f.read()

setuptools.setup(
    name='JsMeetsStarlette',
    version='0.0.0',
    description=SHORT_DISCRIPTION,
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='meloncookie',
    author_email='',
    license='MIT',
    url='https://github.com/meloncookie/JsMeetsStarlette',
    install_requires=[],
    extras_require={
        "full": [
            "aiofiles",
            "graphene",
            "itsdangerous",
            "jinja2",
            "python-multipart",
            "pyyaml",
            "requests",
            "ujson",
            "starlette"
        ]
    },
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Internet :: WWW/HTTP"
    ],
    python_requires='>=3.7'
)