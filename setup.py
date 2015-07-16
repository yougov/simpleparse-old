#!/usr/bin/env python
"""Installs SimpleParse using distutils

Run:
    python setup.py install
to install the packages from the source archive.
"""
from __future__ import print_function
import sys,os
extra_commands = {}
try:
    from setuptools import setup, Extension
except ImportError:
    from distutils.core import setup, Extension
try:
    from distutils.command.build_py import build_py_2to3
    extra_commands['build_py'] = build_py_2to3
except ImportError:
    pass

try:
    from Cython.Distutils import build_ext
except ImportError:
    have_cython = False
else:
    have_cython = True
print('Have cython:', have_cython)


def findVersion( ):
    a = {}
    exec( open( os.path.join( 'simpleparse', '__init__.py') ).read(), a, a )
    return a['__version__']

def isPackage( filename ):
    """Is the given filename a Python package"""
    return (
        os.path.isdir(filename) and 
        os.path.isfile( os.path.join(filename,'__init__.py'))
    )
def packagesFor( filename, basePackage="" ):
    """Find all packages in filename"""
    set = {}
    for item in os.listdir(filename):
        dir = os.path.join(filename, item)
        if item.lower() != 'cvs' and isPackage( dir ):
            if basePackage:
                moduleName = basePackage+'.'+item
            else:
                moduleName = item
            set[ moduleName] = dir
            set.update( packagesFor( dir, moduleName))
    return set

packages = packagesFor( "simpleparse", 'simpleparse' )
packages.update( {'simpleparse':'simpleparse'} )

def cython_extension( name, include_dirs = (), ):
    """Create a cython extension object"""
    filenames = '%(name)s.c'%locals(), '%(name)s.pyx'%locals()
    filename = filenames[bool(have_cython)]
    return Extension(
        "simpleparse.%(name)s"%locals(),
        [
            os.path.join(
                'src',
                filename
            ),
        ],
    )

extensions = [
    cython_extension( '_boyermoore' ),
]
print('extensions', [x.name for x in extensions])

options = {
    'sdist': { 'force_manifest':1,'formats':['gztar','zip'] },
}
if sys.platform == 'win32':
    options.setdefault(
        'build_ext',{}
    )['define'] = 'BAD_STATIC_FORWARD'

if __name__ == "__main__":
    from sys import hexversion
    if hexversion >= 0x2030000:
        # work around distutils complaints under Python 2.2.x
        extraArguments = {
            'classifiers': [
                """Programming Language :: Python""",
                """Topic :: Software Development :: Libraries :: Python Modules""",
                """Intended Audience :: Developers""",
            ],
            'keywords': 'parse,parser,parsing,text,ebnf,grammar,generator',
            'long_description' : """A Parser Generator for Python (w/mxTextTools derivative)

Provides a moderately fast parser generator for use with Python,
includes a forked version of the mxTextTools text-processing library
modified to eliminate recursive operation and fix a number of 
undesirable behaviours.

Converts EBNF grammars directly to single-pass parsers for many
largely deterministic grammars.""",
            'platforms': ['Any'],
        }
    else:
        extraArguments = {
        }
    if have_cython:
        extra_commands['build_ext'] = build_ext
    setup (
        name = "SimpleParse",
        version = findVersion(),
        description = "A Parser Generator for Python (w/mxTextTools derivative)",
        author = "Mike C. Fletcher",
        author_email = "mcfletch@users.sourceforge.net",
        url = "http://simpleparse.sourceforge.net/",

        package_dir = packages,
        options = options,
        cmdclass= extra_commands,
        ext_modules=extensions,

        packages = list(packages.keys()),
        **extraArguments
    )
