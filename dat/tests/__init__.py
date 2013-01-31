class CallRecorder(object):
    def __init__(self, func=None):
        self.calls = []
        self._func = func

    def __call__(self, *args, **kwargs):
        self.calls.append((list(args), kwargs))
        if self._func is not None:
            return self._func(*args, **kwargs)


class FakeObj(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class odict(dict):
    def __init__(self, *args):
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
