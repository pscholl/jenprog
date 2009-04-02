from distutils.core import setup

setup(name='jenprog',
      version='1.0',
      author='Philipp Scholl',
      author_email='scholl@teco.edu',
      url='http://www.teco.edu/~scholl/jenprog-1.0.tar.gz',
      py_modules=['con_ftdi', 'con_serial', 'con_ipv6', 'flashutils'],
      scripts=['jenprog'],
      requires=('pyserial'))
