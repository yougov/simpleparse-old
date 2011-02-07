"""Pure-python implementation of ObjectGenerator classes"""
from simpleparse.error import ParserSyntaxError

class Parser( object ):
    def __init__( self, grammar ):
        self.grammar = grammar 
    def __call__( self, content, start=0, end=None, *args, **named ):
        state = State( content, start, end, *args, **named )
        try:
            result = self.grammar( state )
        except NoMatch, err:
            return (False,[],start)
        else:
            return (True,result,state.current)

class State( object ):
    """Parser state for a parsing run"""
    def __init__( self, buffer, start=0, stop=None ):
        self.buffer = buffer 
        self.start = start 
        self.current = start
        if stop is None:
            stop = len(buffer)
        if stop < 0:
            stop = 0
        if stop > len(buffer):
            stop = len(buffer)
        if stop < start:
            raise ValueError( "stop < start", stop, start )
        self.stop = stop
        self.stack = []
    def enter( self, token ):
        """Enter parsing of the given (grouping) element token (save internal state)"""
        self.stack.append( token )
    def exit( self, token ):
        """Exit parsing of the given (grouping) element token (pop internal state)"""
        try:
            token = self.stack.pop( )
        except IndexError, err:
            raise RuntimeError( """Unbalanced calls to enter/exit on %s""", token )

class Match( object ):
    """A token generated during a parse"""
    def __init__( self, state, token, **named ):
        named['state'] = state 
        named['token'] = token
        self.__dict__.update( **named )
    success = True 
    start = None 
    stop = None 
    children = None
class NoMatch( Exception ):
    """Raised when no match is found"""
class EOFReached( NoMatch ):
    """Raised when no match because EOF reached"""

class ElementToken( object ):
    """Base class for ElementTokens, provides fallback implementations for flag-parsing based on core "parse" method"""
    negative = 0
    optional = 0
    repeating = 0
    report = 1
    name = None
    # note that optional and errorOnFail are mutually exclusive
    errorOnFail = None
    # any item may be marked as expanded,
    # which says that it's a top-level declaration
    # and that links to it should automatically expand
    # as if the name wasn't present...
    expanded = 0
    lookahead = 0
    def __init__( self, **namedarguments ):
        """Initialize the object with named attributes

        This method simply takes the named attributes and
        updates the object's dictionary with them
        """
        self.__dict__.update( namedarguments )

    def parse( self, state ):
        raise NotImplementedError( self, 'parse' )
    def parse_optional( self, state ):
        """By default, run the base parse and consider failure success"""
        start = state.current
        try:
            return self.parse( state )
        except NoMatch, err:
            state.current = start
            return []
    def parse_repeating_optional( self, state ):
        result = []
        while True:
            try:
                match = self.parse( state )
                result.extend( match )
            except NoMatch, err:
                break
        return result
    def parse_repeating( self, state ):
        """By default, run base parse until it fails, push all tokens to the stack"""
        result = []
        found = False
        while True:
            try:
                match = self.parse( state )
                result.extend( match )
                found = True
            except NoMatch, err:
                break
        if not found:
            raise NoMatch( self, state )
        return result
    def parse_negative( self, state ):
        start = state.current
        try:
            self.parse( state )
        except NoMatch, err:
            state.current += 1
            return [ Match( self, state, start = state.current, stop=state.current +1 ) ]
        else:
            state.current = start
            raise NoMatch( self, state )
    def parse_negative_optional( self, state ):
        try:
            return self.parse_negative( state )
        except NoMatch, err:
            return []
    def parse_negative_repeating( self, state ):
        result = []
        start = stop = state.current
        while True:
            try:
                self.parse( state )
            except EOFReached, err:
                # child can read EOF before we do...
                stop += 1
                if stop >= state.stop:
                    break
            except NoMatch, err:
                stop += 1
                state.current += 1
            else:
                break # fail due to match
        state.current = stop
        if stop > start:
            return [ Match( self, state, start=start, stop=stop ) ]
        raise NoMatch( self, state )
    def parse_negative_repeating_optional( self, state ):
        try:
            return self.parse_negative_repeating( state )
        except NoMatch, err:
            return []

    def to_parser( self ):
        return Parser( self.final_method() )
    def final_method( self ):
        name = ['parse']
        for attribute in ('negative','repeating','optional'):
            if getattr( self, attribute ):
                name.append( attribute )
        return self._update( getattr( self, "_".join( name )) )
    def _update( self, final_parser ):
        def updater( state ):
            state.enter( self )
            start = state.current
            try:
                try:
                    result = final_parser( state )
                except NoMatch, err:
                    if self.errorOnFail:
                        raise ParserSyntaxError( 
                            buffer = state.buffer, 
                            position = state.current,
                            line = -1,
                            production = self,
                        )
                    else:
                        raise
                stop = state.current
                if self.report and self.name:
                    return [ Match(state, self, start=start, stop=stop, children = result ) ]
                else:
                    del result[:]
                return result 
            finally:
                state.exit( self )
        updater.__name__ = '%s_%s'%( self.__class__.__name__, final_parser.__name__)
        updater.__doc__ = final_parser.__doc__
        return updater

class Literal( ElementToken ):
    value = None
    def __init__( self, **named ):
        super( Literal, self ).__init__( **named )
        self.length = len(self.value)
    def parse( self, state ):
        if state.buffer[state.current:state.current+self.length] == self.value :
            state.current = state.current + self.length
            return [Match( self, state, start=state.current, stop=state.current + self.length )]
        elif state.current + self.length >= state.stop:
            raise EOFReached( self, state )
        else:
            raise NoMatch( self, state )
class CILiteral( ElementToken ):
    value = None 
    def __init__( self, **named ):
        super( CILiteral, self ).__init__( **named )
        self.length = len(self.value)
        self._lower = self.value.lower()
    def parse( self, state ):
        test = state.buffer[state.current:state.current+self.length]
        if test.lower() == self._lower:
            state.current = state.current + self.length
            return [Match( self, state, start=state.current, stop=state.current + self.length )]
        elif state.current + self.length >= state.stop:
            raise EOFReached( self, state )
        else:
            raise NoMatch( self, state )

class Range( ElementToken ):
    """Match a range (set of ranges) of characters"""
    value = None 
    def parse( self, state ):
        if state.current >= state.stop:
            raise EOFReached( state, self )
        if state.buffer[state.current] in self.value:
            state.current += 1
            return [Match( self, state, start=state.current, stop=state.current+1)]
        else:
            raise NoMatch( self, state )
        
    def parse_negative( self, state ):
        if state.current >= state.stop:
            raise EOFReached( state, self )
        if state.buffer[state.current] not in self.value:
            state.current += 1
            return [Match( self, state, start=state.current, stop=state.current+1)]
        else:
            raise NoMatch( self, state )
    def parse_repeating( self, state ):
        current = start = state.current 
        stop = state.stop 
        content = state.buffer
        set = self.value
        while current < stop:
            if content[current] in self.value:
                current += 1
            else:
                break 
        if current > start:
            state.current = current
            return [Match( self, state, start=start, stop=current)]
        else:
            raise NoMatch( self, state )
    def parse_negative_repeating( self, state ):
        current = start = state.current 
        stop = state.stop 
        content = state.buffer
        set = self.value
        while current < stop:
            if content[current] not in set:
                current += 1
            else:
                break 
        if current > start:
            state.current = current
            return [Match( self, state, start=start, stop=current)]
        else:
            raise NoMatch( self, state )

class Group( ElementToken ):
    parsers = None
    def to_parser( self ):
        self.parsers = [ item.final_method( ) for item in self.children ]
        return super( Group, self ).to_parser()

class SequentialGroup( Group ):
    """Parse a sequence of elements as a single token (with back-tracking)"""
    
    def parse( self, state ):
        results = []
        for item in self.parsers:
            results.extend( item( state ))
        return results 
class FirstOfGroup( Group ):
    def parse( self, state ):
        for item in self.parsers:
            try: 
                return item( state )
            except EOFReached, err:
                break
            except NoMatch, err:
                pass
        raise NoMatch( self, state )
