from setuptools import setup, find_packages


with open('README.md') as f:
    long_description = ''.join(f.readlines())

setup(
    name='fairsharing_proxy',
    version='0.1.0',
    description='Proxy service for using FAIRsharing API in DSW',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Marek Suchánek',
    keywords='dsw proxy fairsharing api rest',
    license='Apache License 2.0',
    url='https://github.com/ds-wizard/fairsharing-proxy',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Topic :: Internet :: Proxy Servers',
        'Topic :: Internet :: WWW/HTTP :: HTTP Servers',
    ],
    zip_safe=False,
    python_requires='>=3.9, <4',
    install_requires=[
        'click',
        'fastapi',
        'httpx',
        'PyYAML',
        'uvicorn[standard]',
    ],
    entry_points={
        'console_scripts': [
            'fairsharing_proxy=fairsharing_proxy:main',
        ],
    },
)
