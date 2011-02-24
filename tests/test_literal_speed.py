from simpleparse.objectgenerator import Literal, Name

def main():
    a = Literal( 'a' )
    n = Name( 'a', repeating=True )
    n._target = a.final_method()
    ap = n.to_parser()
    print ap( 'a' * 1024 * 1024 )[-1]

if __name__ == "__main__":
    main()
