from distutils.core import setup, Extension

module1 = Extension('gluesockets',
                    sources=['socketGlue.c'])

setup(name='gluesockets',
      version='1.0',
      description='Connects two sockets and moving data from one to another.',
      ext_modules=[module1])
