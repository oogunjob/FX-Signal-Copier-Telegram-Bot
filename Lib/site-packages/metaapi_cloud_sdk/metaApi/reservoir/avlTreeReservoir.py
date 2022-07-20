from .avlTree import avl_tree
import random
import math
from datetime import datetime

switch_to_algorithm_z_constant = 22
debug = 'none'


def reservoir(reservoir_size, storage_period_in_milliseconds=60000, random_number_gen=None):
    interval = storage_period_in_milliseconds / 1000
    rng = random_number_gen or random.random
    reservoir_size = max(1, (math.floor(reservoir_size) >> 0) or 1)
    total_item_count = 0
    last_deleted_index = -1
    num_to_skip = -1

    def algorithm_r():
        """"Algorithm R"
        Selects random elements from an unknown-length input.
        Has a time-complexity of: O(N)
        Number of random numbers required:
        N - n
        Where:
        n = the size of the reservoir
        N = the size of the input"""
        local_item_count = total_item_count + 1
        random_value = math.floor(rng() * local_item_count)
        to_skip = 0

        while random_value >= reservoir_size:
            to_skip += 1
            local_item_count += 1
            random_value = math.floor(rng() * local_item_count)
        nonlocal evict_next
        evict_next = random_value
        return to_skip

    def algorithm_x():
        """Selects random elements from an unknown-length input.
        Has a time-complexity of: O(N)
        Number of random numbers required:
        2 * n * ln( N / n )
        Where:
        n = the size of the reservoir
        N = the size of the input"""
        nonlocal algorithm_x_count
        nonlocal current_algorithm
        local_item_count = total_item_count
        random_value = rng()
        to_skip = 0

        if total_item_count <= switch_threshold:
            local_item_count += 1
            algorithm_x_count += 1
            quotient = algorithm_x_count / local_item_count

            while quotient > random_value:
                to_skip += 1
                local_item_count += 1
                algorithm_x_count += 1
                quotient = (quotient * algorithm_x_count) / local_item_count
            return to_skip
        else:
            current_algorithm = algorithm_z
            return current_algorithm()

    def algorithm_z():
        """"Algorithm Z"
        Selects random elements from an unknown-length input.
        Has a time-complexity of:
        O(n(1 + log (N / n)))
        Number of random numbers required:
        2 * n * ln( N / n )
        Where:
        n = the size of the reservoir
        N = the size of the input"""
        term = total_item_count - reservoir_size + 1
        nonlocal w

        while True:
            random_value = rng()
            x = total_item_count * (w - 1)
            to_skip = math.floor(x)
            subterm = ((total_item_count + 1) / term)
            subterm *= subterm
            term_skip = term + to_skip
            lhs = math.exp(math.log(((random_value * subterm) * term_skip) / (total_item_count + x)) / reservoir_size)
            rhs = (((total_item_count + x) / term_skip) * term) / total_item_count

            if lhs <= rhs:
                w = rhs / lhs
                break

            y = (((random_value * (total_item_count + 1)) / term) * (total_item_count + to_skip + 1)) / \
                (total_item_count + x)

            if reservoir_size < to_skip:
                denom = total_item_count
                numer_lim = term + to_skip
            else:
                denom = total_item_count - reservoir_size + to_skip
                numer_lim = total_item_count + 1

            for numer in range(total_item_count + to_skip, numer_lim - 1, -1):
                y = y * numer / denom
                denom -= 1

            w = math.exp(-math.log(rng()) / reservoir_size)

            if math.exp(math.log(y) / reservoir_size) <= (total_item_count + x) / total_item_count:
                break
        return to_skip

    current_algorithm = algorithm_x
    switch_threshold = switch_to_algorithm_z_constant * reservoir_size

    if debug == 'R':
        current_algorithm = algorithm_r
    elif debug == 'X':
        switch_threshold = math.inf
    elif debug == 'Z':
        current_algorithm = algorithm_z

    algorithm_x_count = 0
    w = math.exp(-math.log(rng() / reservoir_size))
    evict_next = None

    def comparator(a, b):
        if a < b:
            return -1
        if a > b:
            return 1
        return 0

    index_tree = avl_tree(lambda a, b: comparator(a['index'] if (a and 'index' in a) else 0,
                                                  b['index'] if (b and 'index' in b) else 0))
    value_tree = avl_tree(lambda a, b: comparator(a, b))
    initial_index = 0

    def remove_old_records():
        while True:
            element = index_tree['at'](0)
            if element is not None and datetime.now().timestamp() > element['time'] + interval:
                index_tree['removeAt'](0)
                nonlocal last_deleted_index
                delete_index_diff = element['index'] - last_deleted_index
                last_deleted_index = element['index']
                value_tree['remove'](element['data'])
                nonlocal total_item_count
                total_item_count -= delete_index_diff
                nonlocal algorithm_x_count
                algorithm_x_count = max(0, algorithm_x_count - delete_index_diff)
            else:
                break

    index_tree['removeOldRecords'] = remove_old_records

    def get_percentile(percent):
        index_tree['removeOldRecords']()
        index = (index_tree['size']() - 1) * percent / 100
        lower = math.floor(index)
        fraction_part = index - lower
        percentile = value_tree['at'](lower) or 0
        if fraction_part > 0:
            percentile += fraction_part * ((value_tree['at'](lower + 1) or 0) - (value_tree['at'](lower) or 0))
        return float(percentile)

    index_tree['getPercentile'] = get_percentile

    def push_some(*args):
        nonlocal initial_index
        nonlocal index_tree
        len = min(index_tree['size'](), reservoir_size)
        for arg in args:
            index_tree['removeOldRecords']()
            value = {'index': initial_index, 'time': datetime.now().timestamp(), 'data': arg}
            index_tree = add_sample(index_tree, value)
            initial_index += 1
        return len

    index_tree['pushSome'] = push_some

    def from_plain_object(*args):
        nonlocal index_tree
        nonlocal initial_index
        len = min(index_tree['size'](), reservoir_size)
        for arg in args:
            value = {'index': arg['index'], 'time': arg['time'], 'data': arg['data']}
            add_sample(index_tree, value)
            initial_index += 1
        return len

    index_tree['fromPlainObject'] = from_plain_object

    def add_sample(tree: avl_tree, sample):
        nonlocal total_item_count
        if index_tree['size']() < reservoir_size:
            tree['insert'](sample)
            value_tree['insert'](sample['data'])
        else:
            nonlocal num_to_skip
            if num_to_skip < 0:
                num_to_skip = current_algorithm()
            if num_to_skip == 0:
                replace_random_sample(sample, tree)
            num_to_skip -= 1
        total_item_count += 1
        return tree

    def replace_random_sample(sample, reservoir):
        nonlocal evict_next
        if evict_next is not None:
            random_index = evict_next
            evict_next = None
        else:
            random_index = math.floor(rng() * reservoir_size)
        value = reservoir['at'](random_index)
        reservoir['removeAt'](random_index)
        value_tree['remove'](value['data'])
        value_tree['insert'](sample['data'])
        reservoir['insert'](sample)

    return index_tree
