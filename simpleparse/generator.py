"""Abstract representation of an in-memory grammar that generates parsers"""
import traceback

class Generator(object):
    '''Abstract representation of an in-memory grammar that generates parsers
    
    The generator class manages a collection of
    ElementToken objects.  These element token objects
    allow the generator to be separated from the
    particular parser associated with any particular EBNF
    grammar.  In fact, it is possible to create entire grammars
    using only the generator objects as a python API.
    '''
    def __init__( self ):
        """Initialise the Generator"""
        self.names = []
        self.rootObjects = {}
        self.methodSource = None
        self.definitionSources = []
    def getNameIndex( self, name ):
        '''Return the index into the main list for the given name'''
        return name
    def getRootObjects( self, ):
        '''Return the list of root generator objects'''
        return self.rootObjects
    def getNames( self ):
        '''Return the list of root generator objects'''
        names = self.rootObjects.keys()
        if not isinstance( names, list ):
            names = list(names)
        return names
    def getRootObject( self, name ):
        """Get a particular root object by name"""
        try:
            return self.rootObjects[ name ]
        except (KeyError,NameError) as err:
            for source in self.definitionSources:
                try:
                    return source[name]
                except (NameError,KeyError) as err:
                    pass 
        raise NameError( name )
    __getitem__ = getRootObject
    def get( self, name, default=None ):
        """Get a particular token, or return default"""
        try:
            return self[ name ]
        except (KeyError,NameError) as err:
            return default 
    
    def addDefinition( self, name, rootElement ):
        '''Add a new definition (object) to the generator'''
        if name in self.rootObjects :
            raise NameError( '''Attempt to redefine an existing name %s'''%(name), self )
        self.rootObjects[name] = rootElement
    def buildParser( self, name, methodSource=None ):
        '''Build the given parser definition, returning a Parser object'''
        
        return self.getRootObject(name).to_parser( self )
    def getObjectForName( self, name):
        """Determine whether our methodSource has a parsing method for the given name

        returns ( flags or 0 , tagobject)
        """
        testName = "_m_"+name
        if hasattr( self.methodSource, testName):
            method = getattr( self.methodSource, testName )
            if callable(method):
                return  TextTools.CallTag, method
            elif method == TextTools.AppendMatch:
                return method, name
            elif method in (TextTools.AppendToTagobj, TextTools.AppendTagobj):
                object = self.getTagObjectForName( name )
                if method == TextTools.AppendToTagobj:
                    if not ( hasattr( object, 'append') and callable(object.append)):
                        raise ValueError( """Method source %s declares production %s to use AppendToTagobj method, but doesn't given an object with an append method in _o_%s (gave %s)"""%(repr(self.methodSource), name,name, repr(object)))
                return method, object
            else:
                raise ValueError( """Unrecognised command value %s (not callable, not one of the Append* constants) found in methodSource %s, name=%s"""%( repr(method),repr(methodSource),name))
        return 0, name
    def getTagObjectForName( self, name ):
        """Get any explicitly defined tag object for the given name"""
        testName = "_o_"+name
        if hasattr( self.methodSource, testName):
            object = getattr( self.methodSource, testName )
            return object
        return name
    def addDefinitionSource( self, item ):
        """Add a source for definitions when the current grammar doesn't supply
        a particular rule (effectively common/shared items for the grammar)."""
        self.definitionSources.append( item )

### Compatability API
##  This API exists to allow much of the code written with SimpleParse 1.0
##  to work with SimpleParse 2.0
class GeneratorAPI1(object):
    """Stand-in class supporting operation of SimpleParse 1.0 applications

    There was really only the one method of interest, parserbyname,
    everything else was internal (and is now part of
    simpleparsegrammar.py).
    """
    def __init__( self, production, prebuilt=() ):
        from simpleparse.parser import Parser
        self.parser = Parser( production, prebuilts=prebuilt )
    def parserbyname( self, name ):
        """Retrieve a tag-table by production name"""
        return self.parser.buildTagger( name )

def buildParser( declaration, prebuiltnodes=() ):
    """API 1.0 primary entry point, returns a GeneratorAPI1 instance

    That object will respond to the parserbyname API expected by
    SimpleParse 1.0 applications.
    """
    return GeneratorAPI1( declaration, prebuiltnodes )
