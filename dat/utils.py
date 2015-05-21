import functools
from itertools import izip
import string
import warnings

from PyQt4 import QtCore


def bisect(count, getter, element, lo=0, comp=lambda x, y: x < y):
    """Version of bisect.bisect_right that uses lambdas.

    Contrary to bisect.bisect_right which takes a list, this version accepts a
    'getter' function to retrieve a specific element, and a 'comp' function to
    compare them.

    It is useful for list views in widgets.
    """
    if lo < 0:
        raise ValueError("lo must be non-negative")
    hi = count
    while lo < hi:
        mid = (lo + hi) // 2
        mid_elem = getter(mid)
        if comp(element, mid_elem):
            hi = mid
        else:
            lo = mid + 1
    return lo


_whitespace = set(iter(string.whitespace))


def iswhitespace(s):
    return all(c in _whitespace for c in s)


class catch_warning(object):
    """Context manager that intercepts a specific category of warnings.

    The 'record' argument specifies whether warnings should be captured and
    returned by the context manager, as a list.
    The 'handle' argument is a function that will be called to handle warnings
    as soon as they are emitted.
    The 'category' argument specifies which category of warnings we want to
    catch. The other categories will be handled as they previously were.
    """
    def __init__(self, category, record=False, handle=None):
        self._category = category
        self._record = record
        self._handle = handle

    def __enter__(self):
        self._orig_filters = warnings.filters
        warnings.filters = []
        self._orig_showwarning = warnings.showwarning
        if self._record:
            log = []
        else:
            log = None

        def showwarning(message, category, filename, lineno,
                        file=None, line=None):
            if issubclass(category, self._category):
                if log is not None:
                    log.append(warnings.WarningMessage(
                        message, category, filename, lineno,
                        file, line))
                if self._handle is not None:
                    self._handle(
                        message, category, filename, lineno,
                        file, line)
            else:
                current_filters = warnings.filters
                warnings.filters = self._orig_filters + current_filters
                current_showwarning = warnings.showwarning
                warnings.showwarning = self._orig_showwarning
                # This is not perfect as some arguments are missing
                # Might cause some issues with the warning repetition logic,
                # but should be acceptable in most cases
                warnings.warn_explicit(
                    message, category, filename, lineno)
                warnings.filters = current_filters
                warnings.showwarning = current_showwarning

        warnings.showwarning = showwarning
        if log is not None:
            return log
        else:
            return None

    def __exit__(self, *exc_info):
        warnings.filters = self._orig_filters
        warnings.showwarning = self._orig_showwarning


class DeferredResult(object):
    def __nonzero__(self, *args):
        raise RuntimeError("DeferredResult should be ignored!")
    __eq__ = __ne__ = __hash__ = __nonzero__

deferred_result = DeferredResult()


def deferrable_via_qt(*argtypes):
    def wrapper(func):
        @QtCore.pyqtSlot(*argtypes)
        @functools.wraps(func)
        def wrapped(self, *args, **kwargs):
            # defer=False is a keyword-only argument
            defer = kwargs.pop('defer', False)
            if kwargs:
                raise TypeError("wrapped function %s got unexpected keyword "
                                "arguments" % func.__name__)
            if defer:
                qtargs = [QtCore.Q_ARG(t, v) for t, v in izip(argtypes, args)]
                QtCore.QMetaObject.invokeMethod(
                    self,
                    func.__name__,
                    QtCore.Qt.QueuedConnection,
                    *qtargs)
                return deferred_result
            else:
                return func(self, *args)
        return wrapped
    return wrapper
