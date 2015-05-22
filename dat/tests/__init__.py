class CallRecorder(object):
    """Simple function-like object recording its calls.
    """
    def __init__(self, func=None):
        self.calls = []
        self._func = func

    def __call__(self, *args, **kwargs):
        self.calls.append((list(args), kwargs))
        if self._func is not None:
            return self._func(*args, **kwargs)


class FakeObj(object):
    """A simple object used in place of something else.

    Its attributes can be passed as keyword parameters.
    """
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class odict(dict):
    """Simple overload of dict with a predictable iteration order.

    Allows the used of assertEqual in tests.
    """
    def __init__(self, *args):
        """Create the dictionary from a list of tuples.

        >>> d = odict([(1, 2), ('key', 'value')])
        >>> d.items()
        [(1, 2), ('key', 'value')]
        """
        kwargs = {k: v for k, v in args}
        dict.__init__(self, **kwargs)
        self._ordered_keys = [k for k, v in args]

    def keys(self):
        return self._ordered_keys

    def iterkeys(self):
        return iter(self.keys())

    def values(self):
        return list(self.itervalues())

    def itervalues(self):
        return iter(self[k] for k in self._ordered_keys)

    def iteritems(self):
        return iter((k, self[k]) for k in self._ordered_keys)

    def items(self):
        return list(self.iteritems())


_application = None


def setup_application(setup=True):
    global _application
    if _application is None and setup:
        try:
            from dat.gui.application import Application
            _application = Application([], {
                'installBundles': False,
                'dontUnloadModules': True,
            })
        except Exception:
            pass
    return _application
