from setuptools import setup

setup(name='techela',
      version='0.1',
      description='Utilities for techela.',
      url='http://github.com/jkitchin/s17-06364',
      author='John Kitchin',
      author_email='jkitchin@andrew.cmu.edu',
      license='GPL',
      platforms=[],
      packages=['techela'],
      scripts=['bin/techela'],
      data_files=['techela/templates'],
      long_description='''A python version of techela''',
      install_requires=['Flask'],)
