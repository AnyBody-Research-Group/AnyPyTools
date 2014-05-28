try:
    from future_builtins import *
except ImportError:
    pass

try:
    input = raw_input
    range = xrange
except NameError:
    pass

try:
    string_types = basestring
except NameError:
    string_types = str
    
    
# This handles pprint always returns string witout ' prefix 
# important when running doctest in both python 2 og python 2
import pprint as _pprint
class MyPrettyPrinter(_pprint.PrettyPrinter):
    def format(self, object, context, maxlevels, level):
        try:
            if isinstance(object, unicode):
                rep = u"'"  + object + u"'"
                return ( rep.encode('utf8'), True, False)
        except NameError:
            pass
        return _pprint.PrettyPrinter.format(self, object, context, maxlevels, level)

def py3k_pprint(s):
    printer = MyPrettyPrinter(width = 110)
    printer.pprint(s)
