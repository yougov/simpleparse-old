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
