"""Pure-python implementation of ObjectGenerator classes"""
from simpleparse.error import ParserSyntaxError
try:
    import pypy 
except ImportError as err:
    pypy = None

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

class Match( object ):
    """A token generated during a parse
    
    token -- the token which matched 
    tag -- the tag (token.value) which matched 
    start -- the index at which the match started 
    children -- the children (if any) of the match
    """
    def __init__( self, token,start=None,stop=None,current=None,children=None ):
        self.tag = token.value 
        self.start = start 
        self.stop = stop
        self.current = current
        self.children = children
    def __len__( self ):
        return 4
    def __cmp__( self, other ):
        return cmp( (self.tag,self.start,self.stop,self.children), other )
    def __eq__( self, other ):
        tup = (self.tag,self.start,self.stop,self.children)
        return tup == other
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

    def parse( self, buffer,start,stop,current ):
        raise NotImplementedError( self, 'parse' )
    def parse_optional( self,buffer,start,stop,current ):
        """By default, run the base parse and consider failure success"""
        try:
            return self.parse( buffer,start,stop,current )
        except NoMatch as err:
            return current,EMPTY
    def parse_repeating_optional( self, buffer,start,stop,current ):
        result = EMPTY
        while current < stop:
            try:
                current,new = self.parse( buffer,start,stop,current )
            except NoMatch as err:
                break
            else:
                if new is not EMPTY:
                    if result is EMPTY:
                        result = []
                    result.extend( new )
        return current,result
    def parse_repeating( self, buffer,start,stop,current ):
        """By default, run base parse until it fails, push all tokens to the stack"""
        result = EMPTY
        found = False
        while current < stop:
            try:
                current,new = self.parse( buffer,start,stop,current )
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
    def parse_negative( self, buffer,start,stop,current ):
        original = current
        try:
            self.parse( buffer,start,stop,current )
        except (EOFReached,NoMatch) as err:
            current += 1
            return current,EMPTY
        else:
            raise NoMatch( self, buffer,start,stop,original )
    def parse_negative_optional( self, buffer,start,stop,current ):
        try:
            return self.parse_negative( buffer,start,stop,current )
        except NoMatch as err:
            return current,EMPTY
    def parse_negative_repeating( self, buffer,start,stop,current ):
        original = final = current
        while current < stop:
            try:
                self.parse( buffer,start,stop,current )
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
    def parse_negative_repeating_optional( self, buffer,start,stop,current ):
        try:
            return self.parse_negative_repeating( buffer,start,stop,current )
        except NoMatch as err:
            return current,EMPTY

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
        if self.errorOnFail:
            if self.lookahead:
                updater = UpdateErrorOnFailLookahead( final_parser, self, self.errorOnFail )
            else:
                updater = UpdateErrorOnFail( final_parser, self, self.errorOnFail )
        else:
            if self.lookahead:
                updater = UpdateLookahead( final_parser, self )
            else:
                updater = UpdateStandard( final_parser, self )
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

class Updater( object ):
    """Base class for the various updater algorithms"""
    def __init__( self, final_parser, token ):
        self.final_parser = final_parser
        self.token = token
    def __call__( self, buffer,start,stop,current ):
        raise NotImplementedError("Updater class %s needs a __call__ method"%(self.__class__.__name__,))

class UpdateStandard( Updater ):
    def __call__( self, buffer,start,stop,current ):
        return self.final_parser( buffer,start,stop,current )
class UpdateErrorOnFail( Updater ):
    def __init__( self, final_parser, token, errorOnFail ):
        super( UpdateErrorOnFail, self ).__init__( final_parser, token )
        self.errorOnFail = errorOnFail
    def __call__( self, buffer,start,stop,current ):
        try:
            return self.final_parser( buffer,start,stop,current )
        except NoMatch as err:
            return self.errorOnFail( buffer,start,stop,current )
class UpdateLookahead( Updater ):
    def __call__( self, buffer,start,stop,current ):
        _,result =  self.final_parser( buffer,start,stop,current )
        return current,result
class UpdateErrorOnFailLookahead( UpdateLookahead, UpdateErrorOnFail ):
    """Combines both types of update customization"""
    def __call__( self, buffer,start,stop,current ):
        try:
            _,result = self.final_parser( buffer,start,stop,current )
        except NoMatch as err:
            return self.errorOnFail( buffer,start,stop,current )
        else:
            return current,result

class UpdateLookahead( Updater ):
    def __call__( self, buffer,start,stop,current ):
        _,result = self.final_parser( buffer,start,stop,current )
        return current,result

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
    def parse( self, buffer,start,stop,current ):
        end_of_me = current+self.length
        if buffer[current:end_of_me] == self.value :
            return end_of_me,EMPTY
        elif end_of_me >= stop:
            raise EOFReached( self, buffer,start,stop,current )
        else:
            raise NoMatch( self, buffer,start,stop,current )
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
    def parse( self, buffer,start,stop,current ):
        end_of_me = current+self.length
        test = buffer[current:end_of_me]
        if test.lower() == self._lower:
            return end_of_me,EMPTY
        elif end_of_me >= stop:
            raise EOFReached( self, buffer,start,stop,current )
        else:
            raise NoMatch( self, buffer,start,stop,current )

class Range( ElementToken ):
    """Match a range (set of ranges) of characters"""
    def parse( self, buffer,start,stop,current ):
        if current >= stop:
            raise EOFReached( self, buffer,start,stop,current )
        if buffer[current] in self.value:
            return current+1, EMPTY
        else:
            raise NoMatch( self, buffer,start,stop,current )
        
    def parse_negative( self, buffer,start,stop,current ):
        if current >= stop:
            raise EOFReached( self,buffer,start,stop,current )
        if buffer[current] not in self.value:
            return current+1,EMPTY
        else:
            raise NoMatch( self,buffer,start,stop,current )
    def parse_repeating( self, buffer,start,stop,current ):
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
    def parse_negative_repeating( self, buffer,start,stop,current ):
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
        if not self._final_method:
            self.parsers = [ 
                item.final_method( generator=generator, noReport=noReport ) 
                for item in self.value
            ]
        return super( Group, self ).final_method( generator, noReport )

class SequentialGroup( Group ):
    """Parse a sequence of elements as a single token (with back-tracking)"""
    
    def parse( self, buffer,start,stop,current ):
        results = EMPTY
        for item in self.parsers:
            current,new = item(buffer,start,stop,current)
            if new is not EMPTY:
                if results is EMPTY:
                    results = []
                results.extend( new )
        return current,results 
class FirstOfGroup( Group ):
    if pypy:
        def parse( self, buffer,start,stop,current, where=0):
            if where >= len(self.parsers):
                raise NoMatch( self, buffer,start,stop,current )
            else:
                try:
                    return self.parsers[where]( buffer,start,stop,current )
                except NoMatch as err:
                    return self.parse(buffer, start, stop, current, where+1)
    else:
        def parse( self, buffer,start,stop,current, where=0):
            for item in self.parsers:
                try: 
                    return item( buffer,start,stop,current )
                except NoMatch as err:
                    pass
            raise NoMatch( self, buffer,start,stop,current )

class EOF( ElementToken ):
    def parse( self, buffer,start,stop,current ):
        if current >= stop:
            return current,EMPTY
        raise NoMatch( self, buffer,start,stop,current )

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
    def parse( self, buffer,start,stop,current ):
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
    def parse( self, buffer,start,stop,current ):
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
