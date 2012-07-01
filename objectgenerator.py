"""Abstraction point to load either the pure-python or Cython parser implementation"""
#try:
from simpleparse._objectgenerator import *
#except ImportError, err:
#    from simpleparse._pureobjectgenerator import *
