"""Pure-python implementation of ObjectGenerator classes"""
from simpleparse.error import ParserSyntaxError

EMPTY = None

class CallableParser( object ):
    def __init__( self, grammar ):
        self.grammar = grammar 
    def __call__( self, content, start=0, stop=None, *args, **named ):
        if not isinstance( content, State ):
            state = State( content, start, stop, *args, **named )
        else:
            state = content
        try:
            result = self.grammar( state )
        except NoMatch, err:
            return (False,[],start)
        else:
            if result is EMPTY:
                result = []
            return (True,result,state.current)

class State( object ):
    """Parser state for a parsing run"""
    def __init__( self, buffer, start=0, stop=None, generator=None ):
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
        self.generator = generator
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
    """A token generated during a parse
    
    token -- the token which matched 
    tag -- the tag (token.value) which matched 
    state -- the state object against which we matched 
    start -- the index at which the match started 
    children -- the children (if any) of the match
    """
    def __init__( self, token, state,start=None,stop=None,children=None ):
        self.tag = token.value 
        self.state = state 
        self.start = start 
        self.stop = stop
        self.children = children
    def __len__( self ):
        return 4
    def __cmp__( self, other ):
        return cmp( (self.tag,self.start,self.stop,self.children), other )
    def __getitem__( self, index ):
        return (self.tag,self.start,self.stop,self.children)[index]
    def __repr__( self ):
        return '%s(%r,%r,%r,%r)'%(
            self.__class__.__name__,
            self.tag,
            self.start,
            self.stop,
            self.children,
        )

class NoMatch( Exception ):
    """Raised when no match is found"""
class EOFReached( NoMatch ):
    """Raised when no match because EOF reached"""

class ElementToken( object ):
    """Base class for ElementTokens, provides fallback implementations for flag-parsing based on core "parse" method"""
    def __init__( 
        self,
        value = None,
        negative = False,
        optional = False,
        repeating = False,
        report = True,
        errorOnFail = None,
        expanded = False,
        lookahead = False,
        generator = None,
    ):
        """Initialize the object with named attributes

        This method simply takes the named attributes and
        updates the object's dictionary with them
        """
        self.value = value
        self.negative = negative
        self.optional = optional
        self.repeating = repeating
        self.report = report 
        self.errorOnFail = errorOnFail
        self.expanded = expanded 
        self.lookahead = lookahead 
        self.generator = generator

    def parse( self, state ):
        raise NotImplementedError( self, 'parse' )
    def parse_optional( self, state ):
        """By default, run the base parse and consider failure success"""
        start = state.current
        try:
            return self.parse( state )
        except NoMatch, err:
            state.current = start
            return None
    def parse_repeating_optional( self, state ):
        result = EMPTY
        while state.current < state.stop:
            try:
                new = self.parse( state )
            except NoMatch, err:
                break
            else:
                if new is not EMPTY:
                    if result is EMPTY:
                        result = []
                    result.extend( new )
        return result
    def parse_repeating( self, state ):
        """By default, run base parse until it fails, push all tokens to the stack"""
        result = EMPTY
        found = False
        while state.current < state.stop:
            try:
                new = self.parse( state )
            except NoMatch, err:
                break
            else:
                found = True
                if new is not EMPTY:
                    if result is EMPTY:
                        result = []
                    result.extend( new )
        if not found:
            raise NoMatch( self, state )
        return result
    def parse_negative( self, state ):
        start = state.current
        try:
            self.parse( state )
        except (EOFReached,NoMatch), err:
            state.current += 1
            return EMPTY
        else:
            state.current = start
            raise NoMatch( self, state )
    def parse_negative_optional( self, state ):
        try:
            return self.parse_negative( state )
        except NoMatch, err:
            return EMPTY
    def parse_negative_repeating( self, state ):
        start = stop = state.current
        while state.current < state.stop:
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
            return EMPTY
        raise NoMatch( self, state )
    def parse_negative_repeating_optional( self, state ):
        try:
            return self.parse_negative_repeating( state )
        except NoMatch, err:
            return EMPTY

    def to_parser( self, generator=None, noReport=False ):
        # TODO: support noReport (copy self and return copy's final_method)
        return CallableParser( self.final_method( generator, noReport) )
    _final_method = None
    def final_method( self, generator=None, noReport=False ):
        if self._final_method is None:
            if not self.generator:
                self.generator = generator 
            name = ['parse']
            for attribute in ('negative','repeating','optional'):
                if getattr( self, attribute ):
                    name.append( attribute )
            self._final_method = self._update( getattr( self, "_".join( name )), noReport=noReport)
        return self._final_method
    def _update( self, final_parser, noReport=False ):
        def updater( state ):
            state.enter( self )
            start = state.current
            try:
                try:
                    result = final_parser( state )
                except NoMatch, err:
                    if self.errorOnFail:
                        self.errorOnFail( state )
                    else:
                        state.current = start
                        raise
                if self.lookahead:
                    # does not advance...
                    state.current = start
                return result 
            finally:
                state.exit( self )
        updater.__name__ = '%s_%s'%( self.__class__.__name__, final_parser.__name__)
        updater.__doc__ = final_parser.__doc__
        return updater
    def __repr__( self ):
        return '%s(value=%r,report=%r,negative=%r,optional=%r,repeating=%r,expanded=%r,lookahead=%r )'%(
            self.__class__.__name__,
            getattr(self,'value',None),
            self.report,
            self.negative,
            self.optional,
            self.repeating,
            self.expanded,
            self.lookahead,
        )

class Literal( ElementToken ):
    def __init__( 
        self, value, 
        negative = False,
        optional = False,
        repeating = False,
        report = True,
        errorOnFail = None,
        expanded = False,
        lookahead = False,
        generator = None,
    ):
        super( Literal, self ).__init__( 
            value,negative,optional,repeating,report,errorOnFail,expanded,lookahead,generator 
        )
        self.length = len(self.value)
    def parse( self, state ):
        if state.buffer[state.current:state.current+self.length] == self.value :
            state.current = state.current + self.length
            return EMPTY
        elif state.current + self.length >= state.stop:
            raise EOFReached( self, state )
        else:
            raise NoMatch( self, state )
class CILiteral( ElementToken ):
    def __init__( 
        self, value, 
        negative = False,
        optional = False,
        repeating = False,
        report = True,
        errorOnFail = None,
        expanded = False,
        lookahead = False,
        generator = None,
    ):
        super( CILiteral, self ).__init__( 
            value,negative,optional,repeating,report,errorOnFail,expanded,lookahead,generator 
        )
        self.value = value
        self.length = len(value)
        self._lower = value.lower()
    def parse( self, state ):
        test = state.buffer[state.current:state.current+self.length]
        if test.lower() == self._lower:
            state.current = state.current + self.length
            return EMPTY
        elif state.current + self.length >= state.stop:
            raise EOFReached( self, state )
        else:
            raise NoMatch( self, state )

class Range( ElementToken ):
    """Match a range (set of ranges) of characters"""
    def parse( self, state ):
        if state.current >= state.stop:
            raise EOFReached( state, self )
        if state.buffer[state.current] in self.value:
            state.current += 1
            return EMPTY
        else:
            raise NoMatch( self, state )
        
    def parse_negative( self, state ):
        if state.current >= state.stop:
            raise EOFReached( state, self )
        if state.buffer[state.current] not in self.value:
            state.current += 1
            return EMPTY
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
            return EMPTY
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
            return EMPTY
        else:
            raise NoMatch( self, state )

class Group( ElementToken ):
    def __init__( 
        self, children, 
        negative = False,
        optional = False,
        repeating = False,
        report = True,
        errorOnFail = None,
        expanded = False,
        lookahead = False,
        generator = None,
    ):
        super( Group, self ).__init__( 
            children,negative,optional,repeating,report,errorOnFail,expanded,lookahead,generator 
        )
        self.parsers = None
    
    def final_method( self, generator=None, noReport=False ):
        self.parsers = [ 
            item.final_method( generator=generator, noReport=noReport ) 
            for item in self.value
        ]
        return super( Group, self ).final_method( generator, noReport )

class SequentialGroup( Group ):
    """Parse a sequence of elements as a single token (with back-tracking)"""
    
    def parse( self, state ):
        results = EMPTY
        for item in self.parsers:
            new = item(state)
            if new is not EMPTY:
                if results is EMPTY:
                    results = []
                results.extend( new )
        return results 
class FirstOfGroup( Group ):
    def parse( self, state ):
        for item in self.parsers:
            try: 
                return item( state )
            except NoMatch, err:
                pass
        raise NoMatch( self, state )

class EOF( ElementToken ):
    def parse( self, state ):
        if state.current >= state.stop:
            return EMPTY
        raise NoMatch( self, state )

class ErrorOnFail(object):
    """When called as a matching function, raises a SyntaxError

    Attributes:
        expected -- list of strings describing expected productions
        production -- string name of the production that's failing to parse
        message -- overrides default message generation if non-null


    (something,something)+!
    (something,something)!
    (something,something)+!"Unable to parse somethings in my production"
    (something,something)!"Unable to parse somethings in my production"

    if string -> give an explicit message (with optional % values)
    else -> use a default string

    """
    production = ""
    message = ""
    expected = ""
    def __init__( self, production="", message="", expected = "" ):
        self.production = production
        self.message = message 
        self.expected = expected
    def __call__( self, state ):
        """Method called if our attached production fails"""
        error = ParserSyntaxError( self.message )
        error.error_message = self.message
        error.production = self.production
        error.expected= self.expected
        error.buffer = state.buffer
        error.position = state.current
        raise error
    def copy( self ):
        import copy
        return copy.copy( self )

class Name( ElementToken ):
    """Reference to another rule in the grammar

    The Name element token allows you to reference another
    production within the grammar.  There are three major
    sub-categories of reference depending on both the Name
    element token and the referenced table's values.

    if the Name token's report attribute is false,
    or the target table's report attribute is false,
    or the Name token negative attribute is true,
        the Name reference will report nothing in the result tree

    if the target's expand attribute is true, however,
        the Name reference will report the children
        of the target production without reporting the
        target production's results (SubTable match)

    finally:
        if the target is not expanded and the Name token
        should report something, the generator object is
        asked to supply the tag object and flags for
        processing the results of the target.  See the
        generator.MethodSource documentation for details.

    Notes:
        expanded and un-reported productions won't get any
        methodsource methods called when
        they are finished, that's just how I decided to
        do it, not sure if there's some case where you'd
        want it.  As a result, it's possible to have a
        method getting called for one instance (where a
        name ref is reporting) and not for another (where
        the name ref isn't reporting).
    """
    expand_child = False 
    report_child = True
    _target = None 
    @property
    def target( self ):
        if not self._target:
            element = self.generator.get( self.value )
            if element is None:
                raise RuntimeError( """Undefined production: %s"""%( self.value, ))
            
            # if we point to an expanded or non-reporting "table", adopt those features.
            self.report_child = element.report and self.report
            self.expand_child = element.expanded
            self._target = element.final_method( 
                generator = self.generator,
            )
        return self._target
    def parse( self, state ):
        """Implement wrapping of results for name references"""
        start = state.current
        result = self.target( state )
        stop = state.current
        if self.report_child:
            if self.value and not self.expand_child:
                if self.lookahead or stop > start:
                    if result is EMPTY:
                        result = []
                    result = [ Match( self,state, start=start, stop=stop, children = result ) ]
            return result 
        else:
            return EMPTY

class LibraryElement( ElementToken ):
    """Holder for a prebuilt item with it's own generator"""
    _target = None
    def __init__( 
        self, production, 
        negative = False,
        optional = False,
        repeating = False,
        report = True,
        errorOnFail = None,
        expanded = False,
        lookahead = False,
        generator = None,
        methodSource=None,
    ):
        super( LibraryElement, self ).__init__( 
            production,negative,optional,repeating,report,errorOnFail,expanded,lookahead,generator 
        )
        self.methodSource = methodSource
    @property 
    def target( self):
        if self._target is None:
            self._target = self.generator.buildParser( self.value, self.methodSource )
            element = self.generator.get( self.value )
            self.report_child = element.report and self.report
            self.expand_child = True
        return self._target
    def parse( self, state ):
        """Implement expanded references for library elements"""
        start = state.current
        success,result,stop = self.target( state )
        if not success:
            raise NoMatch( self, state )
        else:
            if self.report_child:
                if self.value and not self.expand_child:
                    if self.lookahead or stop > start:
                        result = [ Match( self,state, start=start, stop=stop, children = result ) ]
                return result 
            else:
                return EMPTY
