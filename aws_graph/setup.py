from setuptools import setup

setup(name='aws-graph',
      version='0.1',
      author='Guillaume Lasne',
      author_email='guillaume.lasne@socgen.com',
      install_requires=[
          'boto3',
          'graphviz',
      ],
      scripts=['aws_graph.py'],
      entry_points={
          'console_scripts': ['aws-graph=aws_graph:main'],
      },
      zip_safe=False)
