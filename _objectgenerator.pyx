"""Pure-python implementation of ObjectGenerator classes"""
from simpleparse.error import ParserSyntaxError

EMPTY = None

class CallableParser( object ):
    def __init__( self, grammar ):
        self.grammar = grammar 
    def __call__( self, buffer, start=0, stop=None, current=None, *args, **named ):
        if stop is None:
            stop = len(buffer)
        if current is None:
            current = start
        if start < 0:
            start = len(buffer) + start 
            if start < 0:
                start = 0
        if stop < 0:
            stop = stop + len(buffer)
            if stop < start:
                stop = start
        try:
            current,result = self.grammar( buffer, start, stop, current )
        except NoMatch as err:
            return (False,[],start)
        else:
            if result is EMPTY:
                result = []
            return (True,result,current)

cdef class Match( object ):
    """A token generated during a parse
    
    token -- the token which matched 
    tag -- the tag (token.value) which matched 
    start -- the index at which the match started 
    children -- the children (if any) of the match
    """
    cdef public object tag
    cdef public long start
    cdef public long stop
    cdef public object current
    cdef public object children
    def __init__( self, token,start=None,stop=None,current=None,children=None ):
        self.tag = token.value 
        self.start = start 
        self.stop = stop
        self.current = current
        self.children = children
    def __len__( self ):
        return 4
    def __richcmp__( self, other, int comparison ):
        cdef tuple comparator = (self.tag,self.start,self.stop,self.children)
        if comparison == 2:
            # an == comparison...
            return comparator == other
        elif comparison == 0:
            return comparator < other 
        elif comparison == 1:
            return comparator <= other 
        elif comparison == 3:
            return comparator != other
        elif comparison == 4:
            return comparator > other 
        elif comparison == 5:
            return comparison >= other 
        raise RuntimeError( "Unknown comparison operation: %s"%( comparison, ))
    def __getitem__( self, long index ):
        cdef long lookup
        if index < 0:
            lookup = index + 4
        else:
            lookup = index
        if lookup == 0:
            return self.tag 
        elif lookup == 1:
            return self.start 
        elif lookup == 2:
            return self.stop 
        elif lookup == 3:
            return self.children
        raise IndexError( index )
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

cdef class ElementToken( object ):
    """Base class for ElementTokens, provides fallback implementations for flag-parsing based on core "parse" method"""
    cdef public object value 
    cdef public bint negative 
    cdef public bint optional 
    cdef public bint repeating 
    cdef public bint report 
    cdef public object errorOnFail
    cdef public bint expanded 
    cdef public bint lookahead
    cdef public object generator
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

    def parse( self, buffer,start,stop,current ):
        return self.c_parse( buffer, start, stop, current )
    def __call__( self, buffer,start,stop,current ):
        return self.c_final_parse( buffer, start, stop, current )
    
    cdef c_parse( self, buffer, long start, long stop, long current ):
        raise NotImplementedError( self, 'parse' )
    
    cdef c_parse_optional( self, buffer, long start, long stop, long current ):
        """By default, run the base parse and consider failure success"""
        try:
            return self.c_parse( buffer,start,stop,current )
        except NoMatch as err:
            return current,EMPTY
    cdef c_parse_repeating_optional( self, buffer, long start, long stop, long current ):
        result = EMPTY
        while current < stop:
            try:
                current,new = self.c_parse( buffer,start,stop,current )
            except NoMatch as err:
                break
            else:
                if new is not EMPTY:
                    if result is EMPTY:
                        result = []
                    result.extend( new )
        return current,result
    cdef c_parse_repeating( self, buffer, long start, long stop, long current ):
        """By default, run base parse until it fails, push all tokens to the stack"""
        result = EMPTY
        found = False
        while current < stop:
            try:
                current,new = self.c_parse( buffer,start,stop,current )
            except NoMatch as err:
                break
            else:
                found = True
                if new is not EMPTY:
                    if result is EMPTY:
                        result = []
                    result.extend( new )
        if not found:
            raise NoMatch( self, buffer,start,stop,current )
        return current,result
    cdef c_parse_negative( self, buffer, long start, long stop, long current ):
        original = current
        try:
            self.c_parse( buffer,start,stop,current )
        except (EOFReached,NoMatch) as err:
            current += 1
            return current,EMPTY
        else:
            raise NoMatch( self, buffer,start,stop,original )
    cdef c_parse_negative_optional( self, buffer, long start, long stop, long current ):
        try:
            return self.c_parse_negative( buffer,start,stop,current )
        except NoMatch as err:
            return current,EMPTY
    cdef c_parse_negative_repeating( self, buffer, long start, long stop, long current ):
        original = final = current
        while current < stop:
            try:
                self.c_parse( buffer,start,stop,current )
            except EOFReached as err:
                # child can read EOF before we do...
                final += 1
                if final >= stop:
                    break
            except NoMatch as err:
                final += 1
                current += 1
            else:
                break # fail due to match
        current = final
        if final > original:
            return current,EMPTY
        raise NoMatch( self, buffer,start,stop,current )
    cdef c_parse_negative_repeating_optional( self, buffer, long start, long stop, long current ):
        try:
            return self.c_parse_negative_repeating( buffer,start,stop,current )
        except NoMatch as err:
            return current,EMPTY

    def to_parser( self, generator=None, noReport=False ):
        # TODO: support noReport (copy self and return copy's final_method)
        return CallableParser( self.final_method( generator, noReport) )
    def final_method( self, generator=None, noReport=False ):
        if not self.generator:
            self.generator = generator 
        return self
    
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
    
    cdef c_final_parse( self, buffer, long start, long stop, long current ):
        """Final parsing operation, including all options"""
        try:
            new,result = self.c_base_parse( buffer, start, stop, current )
        except NoMatch as err:
            if self.errorOnFail is not None:
                return self.errorOnFail( buffer,start,stop,current )
            raise
        else:
            if self.lookahead:
                return current,result
            return new, result 

    cdef c_base_parse( self, buffer, long start, long stop, long current ):
        """Base parsing, not looking at error on fail or lookahead"""
        if self.negative:
            if self.optional:
                if self.repeating:
                    return self.c_parse_negative_repeating_optional( buffer, start, stop, current )
                else:
                    return self.c_parse_negative_optional( buffer, start, stop, current )
            else:
                if self.repeating:
                    return self.c_parse_negative_repeating( buffer, start, stop, current )
                else:
                    return self.c_parse_negative( buffer, start, stop, current )
        else:
            if self.optional:
                if self.repeating:
                    return self.c_parse_repeating_optional( buffer, start, stop, current )
                else:
                    return self.c_parse_optional( buffer, start, stop, current )
            else:
                if self.repeating:
                    return self.c_parse_repeating( buffer, start, stop, current )
                else:
                    return self.c_parse( buffer, start, stop, current )

cdef class Literal( ElementToken ):
    cdef long length
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
    cdef c_parse( self, buffer,long start,long stop, long current ):
        cdef long end_of_me
        end_of_me = current+self.length
        if buffer[current:end_of_me] == self.value :
            return end_of_me,EMPTY
        elif end_of_me >= stop:
            raise EOFReached( self, buffer,start,stop,current )
        else:
            raise NoMatch( self, buffer,start,stop,current )
cdef class CILiteral( ElementToken ):
    cdef public long length
    cdef object _lower
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
    cdef c_parse( self, buffer,long start,long stop, long current ):
        cdef long end_of_me
        end_of_me = current+self.length
        test = buffer[current:end_of_me]
        if test.lower() == self._lower:
            return end_of_me,EMPTY
        elif end_of_me >= stop:
            raise EOFReached( self, buffer,start,stop,current )
        else:
            raise NoMatch( self, buffer,start,stop,current )

cdef class Range( ElementToken ):
    """Match a range (set of ranges) of characters"""
    cdef c_parse( self, buffer,long start,long stop, long current ):
        if current >= stop:
            raise EOFReached( self, buffer,start,stop,current )
        if buffer[current] in self.value:
            return current+1, EMPTY
        else:
            raise NoMatch( self, buffer,start,stop,current )
        
    cdef c_parse_negative( self, buffer,long start,long stop, long current ):
        if current >= stop:
            raise EOFReached( self,buffer,start,stop,current )
        if buffer[current] not in self.value:
            return current+1,EMPTY
        else:
            raise NoMatch( self,buffer,start,stop,current )
    cdef c_parse_repeating( self, buffer,long start,long stop, long current ):
        original = current 
        set = self.value
        while current < stop:
            if buffer[current] in self.value:
                current += 1
            else:
                break 
        if current > original:
            return current,EMPTY
        else:
            raise NoMatch( self, buffer,start,stop,current )
    cdef c_parse_negative_repeating( self, buffer,long start,long stop, long current ):
        original = current 
        set = self.value
        while current < stop:
            if buffer[current] not in set:
                current += 1
            else:
                break 
        if current > original:
            return current,EMPTY
        else:
            raise NoMatch( self, buffer,start,stop,current )

cdef class Group( ElementToken ):
    cdef public list parsers
    cdef public int length
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
        # children becomes "value"
    def final_method( self, generator=None, noReport=False ):
        super( Group, self ).final_method( generator, noReport )
        for item in self.value:
            item.final_method( generator, noReport )
        return self

cdef class SequentialGroup( Group ):
    """Parse a sequence of elements as a single token (with back-tracking)"""
    
    cdef c_parse( self, buffer,long start,long stop, long current ):
        results = EMPTY
        cdef ElementToken item
        for item in self.value:
            current,new = item.c_final_parse(buffer,start,stop,current)
            if new is not EMPTY:
                if results is EMPTY:
                    results = []
                results.extend( new )
        return current,results 
cdef class FirstOfGroup( Group ):
    cdef c_parse( self, buffer,long start,long stop, long current ):
        cdef ElementToken item
        for item in self.value:
            try: 
                return item.c_final_parse( buffer,start,stop,current )
            except NoMatch as err:
                pass
        raise NoMatch( self, buffer,start,stop,current )

cdef class EOF( ElementToken ):
    cdef c_parse( self, buffer,long start,long stop, long current ):
        if current >= stop:
            return current,EMPTY
        raise NoMatch( self, buffer,start,stop,current )

cdef class ErrorOnFail(object):
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
    cdef public object production 
    cdef public object message 
    cdef public object expected
    def __init__( self, production="", message="", expected = "" ):
        self.production = production
        self.message = message 
        self.expected = expected
    def __call__( self, buffer,start,stop,current ):
        """Method called if our attached production fails"""
        error = ParserSyntaxError( self.message )
        error.error_message = self.message
        error.production = self.production
        error.expected= self.expected
        error.buffer = buffer
        error.position = current
        raise error
    def copy( self ):
        return ErrorOnFail( self.production, self.message, self.expected )

cdef class Name( ElementToken ):
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
    cdef public bint expand_child
    cdef public bint report_child
    cdef public object _target
    @property
    def target( self ):
        current = self._target
        if not current:
            element = self.generator.get( self.value )
            if element is None:
                raise RuntimeError( """Undefined production: %s"""%( self.value, ))
            
            # if we point to an expanded or non-reporting "table", adopt those features.
            self.report_child = element.report and self.report
            self.expand_child = element.expanded
            self._target = current = element.final_method( 
                generator = self.generator,
            )
        return current
    cdef c_parse( self, buffer,long start,long stop, long current ):
        """Implement wrapping of results for name references"""
        original = current
        current,result = self.target( buffer,start,stop,current )
        if self.report_child:
            if self.value and not self.expand_child:
                if self.lookahead or current > original:
                    result = [ Match( self,start=original, stop=current, children = result ) ]
            return current,result 
        else:
            return current,EMPTY

cdef class LibraryElement( ElementToken ):
    """Holder for a prebuilt item with it's own generator"""
    cdef object _target
    cdef object methodSource
    cdef public bint report_child
    cdef public bint expand_child
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
        self._target = None
        self.methodSource = methodSource
    @property 
    def target( self):
        if self._target is None:
            self._target = self.generator.buildParser( self.value, self.methodSource )
            element = self.generator.get( self.value )
            self.report_child = element.report and self.report
            self.expand_child = True
        return self._target
    cdef c_parse( self, buffer,long start,long stop, long current ):
        """Implement expanded references for library elements"""
        original = current
        success,result,current = self.target( buffer,start,stop,current )
        if not success:
            raise NoMatch( self, buffer,start,stop,current )
        else:
            if self.report_child:
                if self.value and not self.expand_child:
                    if self.lookahead or stop > original:
                        result = [ Match( self,start=original, stop=current, children = result ) ]
                return current,result 
            else:
                return current,EMPTY
