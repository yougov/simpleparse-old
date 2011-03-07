from simpleparse.objectgenerator import Literal, Name, Range, SequentialGroup

def main():
    b = Literal( 'a', repeating=True )
    b = b.to_parser()
    print b( 'a' * 1024 * 1024 *8 )[-1]

if __name__ == "__main__":
    main()
