import string


def bisect(count, getter, element, lo=0, comp=lambda x, y: x<y):
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
        mid = (lo + hi)/2
        mid_elem = getter(mid)
        if comp(element, mid_elem):
            hi = mid
        else:
            lo = mid + 1
    return lo


_whitespace = set(iter(string.whitespace))

def iswhitespace(s):
    return all(c in _whitespace for c in s)
