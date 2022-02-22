import setuptools

# with open("README.md", "r") as fh:
#     long_description = fh.read()

setuptools.setup(
    name='nresaguflexure',
    version='1.2.0',
    packages=setuptools.find_packages(),
    url='',
    author='Daniel Harbeck',
    author_email='dharbeck@lco.global',
    description='NRES AGU pinhole location monitor',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': ['agupinholesearch = lcogt_nres_aguanalysis.agupinholesearch:main',
                             'aguanalysis = lcogt_nres_aguanalysis.aguanalysis:main'],

    }
)
