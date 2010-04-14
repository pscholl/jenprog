from distutils.core import setup

setup(name='jenprog',
      version='1.1',
      author='Philipp Scholl',
      author_email='scholl@teco.edu',
      url='http://www.teco.edu/~scholl/ba-toolchain/jenprog-1.1.tar.gz',
      py_modules=['con_ftdi', 'con_serial', 'con_ipv6', 'flashutils'],
      scripts=['jenprog'],
      requires=('pyserial'))
