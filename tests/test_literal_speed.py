from simpleparse.objectgenerator import Literal, Name, Range, SequentialGroup

def main():
    r = Range( 'abc' )
    b = Literal( 'a' )
    b = SequentialGroup( [b,r])
    n = Name( 'a', repeating=True )
    n._target = b.final_method()
    ap = n.to_parser()
    print ap( 'a' * 1024 * 1024 )[-1]

if __name__ == "__main__":
    main()
