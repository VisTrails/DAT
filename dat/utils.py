def bisect(count, getter, element, lo=0, comp=lambda x, y: x<y):
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
