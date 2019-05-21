"""Helper functions

Consists of functions to typically be used within templates, but also
available to Controllers. This module is available to both as 'h'.
"""
'''
from genshi.core import Markup
from webhelpers import *

def wrap_helpers(localdict):
    """Wrap the helpers for use in Genshi templates"""
    def helper_wrapper(func):
        def wrapped_helper(*args, **kwargs):
            return Markup(func(*args, **kwargs))
        try:
            wrapped_helper.__name__ = func.__name__
        except TypeError:
            # Python < 2.4
            pass
        wrapped_helper.__doc__ = func.__doc__
        return wrapped_helper
    for name, func in localdict.iteritems():
        if (not callable(func) or
            not func.__module__.startswith('webhelpers.rails')):
            continue
        localdict[name] = helper_wrapper(func)

wrap_helpers(locals())
'''

import logging
  
# Global cache for timezones
_tz_cache = {}
    
# Timezone corrected time formatting
def strftime(value, fmt, tzname=None):
    try:
        import pytz
        logging.info("'pytz' module is not installed")
    except:
        pytz = None
        
    global _tz_cache
    
    if pytz and isinstance(tzname, basestring):
        if tzname not in _tz_cache.keys():
            _tz_cache[tzname] = pytz.timezone(tzname)
        tz = _tz_cache[tzname]
        value = value.replace(tzinfo=pytz.utc).astimezone(tz)  
    return value.strftime(fmt)
