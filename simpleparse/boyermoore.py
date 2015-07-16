#! /usr/bin/env python
try:
    from ._boyermoore import BoyerMooreBytes
except ImportError as err:
    BoyerMooreBytes = None

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

    