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

    def to_parser( self, generator=None, noReport=False ):
        # TODO: support noReport (copy self and return copy's final_method)
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

class EOF( ElementToken ):
    def parse( self, state ):
        if state.current >= state.stop:
            return []
        raise NoMatch( self, state )

class ErrorOnFail(ElementToken):
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
        error.buffer = text
        error.position = position
        raise error
    def copy( self ):
        import copy
        return copy.copy( self )

class LibraryElement( ElementToken ):
    """Holder for a prebuilt item with it's own generator"""
    generator = None
    production = ""
    methodSource = None
    def to_parser( self, generator=None, noReport=0 ):
        if self.methodSource is None:
            source = generator.methodSource
        else:
            source = self.methodSource
        self.parse = self.generator.buildParser( self.production, source ).grammar
        return super( LibraryElement, self ).to_parser( generator, noReport )

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
    value = ""
    # following two flags are new ideas in the rewrite...
    report = 1
    def to_parser( self, generator, noReport=0 ):
        """Create the table for parsing a name-reference

        Note that currently most of the "compression" optimisations
        occur here.
        """
        command = TableInList
        target = generator.getRootObject(self.value)

        reportSelf = (
            (not noReport) and # parent hasn't suppressed reporting
            self.report and # we are not suppressing ourselves
            target.report and # target doesn't suppress reporting
            (not self.negative) and # we aren't a negation, which doesn't report anything by itself
            (not target.expanded) # we don't report the expanded production
        )
        reportChildren = (
            (not noReport) and # parent hasn't suppressed reporting
            self.report and # we are not suppressing ourselves
            target.report and # target doesn't suppress reporting
            (not self.negative) # we aren't a negation, which doesn't report anything by itself
        )
        
        new = copy.copy( target )
        
        flags = 0
        if target.expanded:
            # the target is the root of an expandedname declaration
            # so we need to do special processing to make sure that
            # it gets properly reported...
            command = SubTableInList
            tagobject = None
            # check for indirected reference to another name...
        elif not reportSelf:
            tagobject = svalue
        else:
            flags, tagobject = generator.getObjectForName( svalue )
            if flags:
                command = command | flags
        if tagobject is None and not flags:
            if self.terminal(generator):
                if extractFlags(self,reportChildren) != extractFlags(target):
                    composite = compositeFlags(self,target, reportChildren)
                    partial = generator.getCustomTerminalParser( sindex,composite)
                    if partial is not None:
                        return partial
                    partial = tuple(copyToNewFlags(target, composite).toParser(
                        generator,
                        not reportChildren
                    ))
                    generator.cacheCustomTerminalParser( sindex,composite, partial)
                    return partial
                else:
                    partial = generator.getTerminalParser( sindex )
                    if partial is not None:
                        return partial
                    partial = tuple(target.toParser(
                        generator,
                        not reportChildren
                    ))
                    generator.setTerminalParser( sindex, partial)
                    return partial
        # base, required, positive table...
        if (
            self.terminal( generator ) and
            (not flags) and
            isinstance(target, (SequentialGroup,Literal,Name,Range))
        ):
            partial = generator.getTerminalParser( sindex )
            if partial is None:
                partial = tuple(target.toParser(
                    generator,
                    #not reportChildren
                ))
                generator.setTerminalParser( sindex, partial)
            if len(partial) == 1 and len(partial[0]) == 3 and (
                partial[0][0] is None or tagobject is None
            ):
                # there is a single child
                # it doesn't report anything, or we don't
                partial = (partial[0][0] or tagobject,)+ partial[0][1:]
            else:
                partial = (tagobject, Table, tuple(partial))
            return self.permute( partial )
        basetable = (
            tagobject,
            command, (
                generator.getParserList (),
                sindex,
            )
        )
        return self.permute( basetable )
    terminalValue = None
    def terminal (self, generator):
        """Determine if this element is terminal for the generator"""
        if self.terminalValue in (0,1):
            return self.terminalValue
        self.terminalValue = 0
        target = generator.getRootObject( self.value )
        if target.terminal( generator):
            self.terminalValue = 1
        return self.terminalValue


def extractFlags( item, report=1 ):
    """Extract the flags from an item as a tuple"""
    return (
        item.negative,
        item.optional,
        item.repeating,
        item.errorOnFail,
        item.lookahead,
        item.report and report,
    )
def compositeFlags( first, second, report=1 ):
    """Composite flags from two items into overall flag-set"""
    result = []
    for a,b in map(None, extractFlags(first, report), extractFlags(second, report)):
        result.append( a or b )
    return tuple(result)
def copyToNewFlags( target, flags ):
    """Copy target using combined flags"""
    new = copy.copy( target )
    for name,value in map(None,
        ("negative","optional","repeating","errorOnFail","lookahead",'report'),
        flags,
    ):
        setattr(new, name,value)
    return new
