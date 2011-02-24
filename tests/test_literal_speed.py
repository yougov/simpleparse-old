from simpleparse.objectgenerator import Literal

def main():
    a = Literal( 'a', repeating=True )
    ap = a.to_parser()
    print ap( 'a' * 1024 * 1024 * 2 )

if __name__ == "__main__":
    main()
