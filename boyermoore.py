#! /usr/bin/env python

class BoyerMoore( object ):
    def __init__( self, search_text ):
        self.search_text = search_text 
        self.jumps = []
        jumptables = {}
        # for each character, pass through creating dicts of char:previous position 
        for i,char in enumerate(search_text):
            self.jumps.append( jumptables.copy())
            jumptables[char] = i
    def search( self, text, start=0, stop=None ):
        offset = start
        if stop is None:
            stop = len(text)
        elif stop < 0:
            stop = len(text) + stop 
            if stop < 0:
                return -1
        indices = range(len(self.search_text))[::-1]
        search_text = self.search_text
        jumps = self.jumps
        stop = stop-len(self.search_text)+1
        while offset < stop:
            for i in indices:
                test = text[offset+i]
                if test != search_text[i]:
                    j = jumps[i].get(test,-1)
                    offset += i - j
                    break 
                if i == 0:
                    return offset 
        return -1

def test_skiptable( ):
    search = 'babc'
    text = 'thisabdefbabce'
    
    boy = BoyerMoore( search )
    position = boy.search( text )
    assert position == 9, position
    
    assert boy.search( 'moo' ) == -1
    assert boy.search( 'babc' ) == 0
    assert boy.search( 'bab' ) == -1
    assert boy.search( 'babc', 1 ) == -1
    assert boy.search( 'babc', 0, -1 ) == -1
    assert boy.search( 'babc', 0, 3 ) == -1
    assert boy.search( 'babc', 0, -5 ) == -1

def test_edgecase():    
    boy = BoyerMoore( 'moomoomoo' )
    index = boy.search( 'this is the world and the world is quite large'+boy.search_text )
    assert index != -1, index
    
def test_ints():
    search = [1,2,3]
    text = [8,4,5,6,1,2,3]
    boy = BoyerMoore( search )
    result = boy.search( text )
    assert result == 4, result
    
def test_big():
    base = 'this is the world and the world is quite large'
    text = base * 50000 + 'moomoomoo'
    #print 'searching in', len(text)
    index = BoyerMoore( 'moomoomoo' ).search( text )
    assert index == len(base)*50000, index

def test_re():
    import re
    r = re.compile( 'moomoomoo' )
    base = 'this is the world and the world is quite large'
    text = base * 50000 + 'moomoomoo'
    result = r.search( text )
    assert result

if __name__ == "__main__":
    for i in range( 50 ):
        #test_re()
        test_big()
    
