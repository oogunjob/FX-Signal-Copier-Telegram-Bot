def create_new_node_(key):
    return {
        'key': key,
        'weight': 1,
        'height': 0,
        'left': None,
        'right': None
    }


def comparer_(a, b):
    if a < b:
        return -1
    if a > b:
        return 1
    return 0


def height_(p):
    return p['height'] if p else 0


def weight_(p):
    return p['weight'] if p else 0


def b_factor_(p):
    return height_(p['right']) - height_(p['left'])


def count_height_and_weight_(p):
    hl = height_(p['left'])
    hr = height_(p['right'])
    p['height'] = (hl if hl > hr else hr) + 1

    wl = weight_(p['left'])
    wr = weight_(p['right'])
    p['weight'] = wl + wr + 1


def rotate_right_(p):
    q = p['left']
    p['left'] = q['right']
    q['right'] = p
    count_height_and_weight_(p)
    count_height_and_weight_(q)
    return q


def rotate_left_(q):
    p = q['right']
    q['right'] = p['left']
    p['left'] = q
    count_height_and_weight_(q)
    count_height_and_weight_(p)
    return p


def balance_(p):
    count_height_and_weight_(p)
    if b_factor_(p) == 2:
        if b_factor_(p['right']) < 0:
            p['right'] = rotate_right_(p['right'])
        return rotate_left_(p)
    if b_factor_(p) == -2:
        if b_factor_(p['left']) > 0:
            p['left'] = rotate_left_(p['left'])
        return rotate_right_(p)
    return p


def at_(p, k):
    if not p:
        return None
    wl = weight_(p['left'])
    if wl <= k < wl + 1:
        return p['key']
    elif k < wl:
        return at_(p['left'], k)
    else:
        return at_(p['right'], k - wl - 1)


def get_minimum_(p):
    if not p:
        return None
    return get_minimum_(p['left']) if p['left'] else p


def get_maximum_(p):
    if not p:
        return None
    return get_maximum_(p['right']) if p['right'] else p


def remove_minimum_(p):
    if not p['left']:
        return p['right']
    p['left'] = remove_minimum_(p['left'])
    return balance_(p)


def to_array_(p):
    arr = []
    if p['left']:
        arr += to_array_(p['left'])
    arr.append(p['key'])
    if p['right']:
        arr += to_array_(p['right'])
    return arr


def to_value_array_(p):
    arr = []
    if p['left']:
        arr += to_array_(p['left'])
    arr.append(p['key']['data'])
    if p['right']:
        arr += to_array_(p['right'])
    return arr


def avl_tree(comparer=None):
    if comparer is None:
        comparer = comparer_

    def count_(p, k):
        return upper_bound_(p, k) - lower_bound_(p, k)

    def get_size():
        return weight_(avl['root'])

    def get_min():
        p = get_minimum_(avl['root'])
        if p:
            return p['key']
        return None

    def get_max():
        p = get_maximum_(avl['root'])
        if p:
            return p['key']
        return None

    def lower_bound(k):
        return avl['lowerBound_'](avl['root'], k)

    def lower_bound_(p, k):
        if not p:
            return 0
        cmp = avl['comparer_'](k, p['key'])
        if cmp <= 0:
            return avl['lowerBound_'](p['left'], k)
        elif cmp > 0:
            return weight_(p['left']) + avl['lower_bound_'](p['right'], k) + 1

    def upper_bound(k):
        return avl['upperBound_'](avl['root'])

    def upper_bound_(p, k):
        if not p:
            return 0
        cmp = avl['comparer_'](k, p['key'])
        if cmp < 0:
            return avl['upperBound_'](p['left'], k)
        elif cmp >= 0:
            return weight_(p['left']) + avl['upperBound_'](p['right'], k) + 1

    def count(k):
        return count_(avl['root'], k)

    def at(k):
        return at_(avl['root'], k)

    def insert(k):
        avl['root'] = avl['insert_'](avl['root'], k)

    def insert_(p, k):
        if not p:
            return create_new_node_(k)
        cmp = avl['comparer_'](k, p['key'])
        if cmp < 0:
            p['left'] = avl['insert_'](p['left'], k)
        elif cmp >= 0:
            p['right'] = avl['insert_'](p['right'], k)
        return balance_(p)

    def remove(k):
        avl['root'] = avl['remove_'](avl['root'], k)

    def remove_(p, k):
        if not p:
            return None
        cmp = avl['comparer_'](k, p['key'])
        if cmp < 0:
            p['left'] = avl['remove_'](p['left'], k)
        elif cmp > 0:
            p['right'] = avl['remove_'](p['right'], k)
        else:
            q = p['left']
            r = p['right']
            if not r:
                return q
            min = get_minimum_(r)
            min['right'] = remove_minimum_(r)
            min['left'] = q
            return balance_(min)
        return balance_(p)

    def remove_at(k):
        val = avl['at'](k)
        avl['root'] = avl['remove_'](avl['root'], val)

    def to_array():
        if avl['root'] is None:
            return []
        return to_array_(avl['root'])

    avl = {
        'root': None,
        'comparer_': comparer,
        'size': get_size,
        'min': get_min,
        'max': get_max,
        'lowerBound': lower_bound,
        'lowerBound_': lower_bound_,
        'upper_bound': upper_bound,
        'upperBound_': upper_bound_,
        'count': count,
        'at': at,
        'insert': insert,
        'insert_': insert_,
        'remove': remove,
        'remove_': remove_,
        'removeAt': remove_at,
        'toArray': to_array
    }
    return avl
