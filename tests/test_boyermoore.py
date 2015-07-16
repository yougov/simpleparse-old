"""Tests for BoyerMoore implementation"""
from simpleparse.boyermoore import BoyerMoore, BoyerMooreBytes
from unittest import TestCase

class BaseTests( object ):
    def test_skiptable( self ):
        search = b'babc'
        text = b'thisabdefbabce'
        
        boy = self.b_class( search )
        position = boy.search( text )
        assert position == 9, position
        
        assert boy.search( b'moo' ) == -1
        assert boy.search( b'babc' ) == 0
        assert boy.search( b'bab' ) == -1
        assert boy.search( b'babc', 1 ) == -1
        assert boy.search( b'babc', 0, -1 ) == -1
        assert boy.search( b'babc', 0, 3 ) == -1
        assert boy.search( b'babc', 0, -5 ) == -1

    def test_edgecase(self):    
        boy = self.b_class( b'moomoomoo' )
        index = boy.search( b'this is the world and the world is quite large'+boy.search_text )
        assert index != -1, index
        
    def test_big(self):
        base = b'this is the world and the world is quite large'
        text = base * 50000 + b'moomoomoo'
        #print 'searching in', len(text)
        index = self.b_class( b'moomoomoo' ).search( text )
        assert index == len(base)*50000, index

    def test_re(self):
        import re
        r = re.compile( b'moomoomoo' )
        base = b'this is the world and the world is quite large'
        text = base * 50000 + b'moomoomoo'
        result = r.search( text )
        assert result
class BMTests(BaseTests, TestCase):
    b_class = BoyerMoore
    def test_ints(self):
        search = [1,2,3]
        text = [8,4,5,6,1,2,3]
        boy = self.b_class( search )
        result = boy.search( text )
        assert result == 4, result
        

if BoyerMooreBytes:
    class BMBTests(BaseTests, TestCase):
        b_class = BoyerMooreBytes
    
