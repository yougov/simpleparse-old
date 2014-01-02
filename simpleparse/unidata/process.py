#! /usr/bin/env python
import json, urllib, os

SOURCE_FILE = 'UnicodeData.txt'

def main():
    if not os.path.exists( SOURCE_FILE ):
        urllib.urlretrieve( 'ftp://ftp.unicode.org/Public/4.1.0/ucd/UnicodeData.txt', SOURCE_FILE ) 
    classes = {}
    for line in open( 'UnicodeData.txt', 'r'):
        line = line.split(';')
        if len(line) > 3:   
            point,_,cls = line[:3]
            point = int(point,16)
            set = classes.setdefault( cls, [] )
            set.append( point )
    for cls,points in classes.items():
        points = u"".join([ unichr( pt ) for pt in points])
        open( '%s.txt'%( cls, ),'w').write( points.encode( 'utf-8' ))

if __name__ == "__main__":
    main()

