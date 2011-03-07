from simpleparse.objectgenerator import Literal, Name, Range, SequentialGroup

def main():
    r = Range( 'abc' )
    b = Literal( 'a' )
    b = SequentialGroup( [b,r])
    n = Name( 'a', repeating=True )
    n._target = b.final_method()
    ap = n.to_parser()
    print ap( 'abacaa' * 1024 * 256 )[-1]

if __name__ == "__main__":
    main()


"""Re-written version of simpleexample for 2.0"""
from simpleparse.common import numbers, strings, comments

declaration = r'''# note use of raw string when embedding in python code...
b := a+
a := 'a',[abc]
'''
from simpleparse.parser import Parser

testData = 'abacaa'

parser = Parser( declaration, "b" )
if __name__ =="__main__":
    import cProfile
    cProfile.runctx( "result = parser.parse( testData * 500 )", globals(), locals(), 'grammar.profile' )
    #print result[-1]
