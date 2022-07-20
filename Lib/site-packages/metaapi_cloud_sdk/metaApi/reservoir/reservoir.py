from typing import Dict
from datetime import datetime
import math


class Reservoir:
    """FIFO-like reservoir of a fixed size capable
    calculating running sums, min/max, average, msdev and stddev
    msdev and stddev calculation by Naive algorithm
    (Mean square deviation) msdev = sqrt((∑{i = from 1 to n}(Xi)^2 -(∑{i = from 1 to n}Xi)^2 / N) / N)
    (Standard deviation) stddev = sqrt((∑{i = from 1 to n}(Xi)^2 -(∑{i = from 1 to n}Xi)^2 / N) / N - 1)
    link: https://goo.gl/MAEGP2"""

    def __init__(self, size: int, observation_interval_in_ms: int, object: Dict = None):
        """Inits reservoir

        Args:
            size: Reservoir size.
            observation_interval_in_ms: Reservoir observation interval in ms.
            object: Reservoir options.
        """
        if not object:
            self.array = []
            self.size = size
            self._interval = observation_interval_in_ms / size / 1000
            self._queueEndTime = datetime.now().timestamp()
            self._firstQueueIndex = 0
            self._intermediaryRecord = None
            self.statistics = {
                'count': 0,
                'sum': 0,
                'max': None,
                'min': None,
                'average': 0,
                'sumOfSquares': 0,
                'msdev': 0,
                'stddev': 0
            }
        else:
            self.array = object['array']
            self.size = object['size']
            self._interval = object['_interval']
            self._queueEndTime = object['_queueEndTime']
            self._firstQueueIndex = object['_firstQueueIndex']
            self._intermediaryRecord = object['_intermediaryRecord']
            self.statistics = self.check_statistics_on_restore(object['statistics'])

    def fill_array(self, index: int):
        while len(self.array) <= index:
            self.array.append(None)

    def check_statistics_on_restore(self, statistics):
        if statistics['count'] == 0:
            statistics = {
                'count': 0,
                'sum': 0,
                'max': None,
                'min': None,
                'average': None,
                'sumOfSquares': 0,
                'msdev': None,
                'stddev': None
            }
        elif statistics['count'] < 2:
            statistics['msdev'] = None
            statistics['stddev'] = None
        return statistics

    def push_measurement(self, data: float):
        """Add element to reservoir.

        Args:
            data: Data to add.
        """
        if math.isfinite(data):
            self._update_queue()
            self._update_intermediary_record(data)
            self._update_statistics_on_add(data)

    def get_statistics(self):
        """Return reservoir statistics

        Returns:
            Reservoir statistics
        """
        self._update_queue()
        return self.statistics

    def to_plain_object(self):
        self._update_queue()
        return {
            'array': self.array,
            'size': self.size,
            '_interval': self._interval,
            '_queueEndTime': self._queueEndTime,
            '_firstQueueIndex': self._firstQueueIndex,
            '_intermediaryRecord': self._intermediaryRecord,
            'statistics': self.statistics
        }

    def _update_queue(self):
        intervals_count = self._take_time_intervals_count()
        empty_elements_count = self._take_empty_elements_add_count()
        if empty_elements_count > 0:
            self._add_record(empty_elements_count)
            self._queueEndTime += intervals_count * self._interval

    def _take_empty_elements_add_count(self):
        empty_elements_count = self._take_time_intervals_count()
        if empty_elements_count > self.size:
            empty_elements_count = self.size
        return empty_elements_count

    def _take_time_intervals_count(self) -> float:
        time_now = datetime.now().timestamp()
        time_diff = time_now - self._queueEndTime
        time_intervals_count = math.floor(time_diff / self._interval)
        return time_intervals_count

    def _update_running_statistics_on_remove(self, remove_count: int):
        remove_element_index = self._firstQueueIndex + 1
        for i in range(remove_count):
            if remove_element_index >= self.size:
                remove_element_index = 0

            self.fill_array(remove_element_index)
            self._update_statistics_on_remove(self.array[remove_element_index], remove_element_index)
            self.array[remove_element_index] = {
                'count': 0,
                'sum': 0,
                'max': None,
                'min': None,
                'average': 0,
                'sumOfSquares': 0
            }
            remove_element_index += 1
        remove_element_index -= 1
        if remove_element_index < 0:
            remove_element_index = self.size - 1
        return remove_element_index

    def _update_statistics_on_remove(self, remove_element, remove_element_index):
        if remove_element is not None:
            self.statistics['count'] -= remove_element['count']
            self.statistics['sumOfSquares'] -= remove_element['sumOfSquares']
            self.statistics['sum'] -= remove_element['sum']
            self._update_statistics_min_and_max_on_remove(remove_element, remove_element_index)
            if self.statistics['count'] > 0:
                self.statistics['average'] = self.statistics['sum'] / self.statistics['count']
                if self.statistics['count'] > 1:
                    dif_of_sums = self._calculate_difference_of_sums(
                        self.statistics['sumOfSquares'], self.statistics['sum'], self.statistics['count'])
                    self.statistics['msdev'] = float(math.sqrt(dif_of_sums / self.statistics['count']))
                    self.statistics['stddev'] = float(math.sqrt(dif_of_sums / (self.statistics['count'] - 1)))
                else:
                    self.statistics['stddev'] = None
                    self.statistics['msdev'] = None
            else:
                self.statistics['average'] = None
                self.statistics['stddev'] = None
                self.statistics['msdev'] = None

    def _update_statistics_min_and_max_on_remove(self, remove_element, remove_element_index):
        if remove_element['max'] is not None and remove_element['max'] == self.statistics['max']:
            self.statistics['max'] = self._find_max(remove_element_index)

        if remove_element['min'] is not None and remove_element['min'] == self.statistics['min']:
            self.statistics['min'] = self._find_min(remove_element_index)

    def _update_statistics_on_add(self, el):
        if el is not None:
            self.statistics['count'] += 1
            self.statistics['sum'] += el
            self._update_statistics_min_and_max_on_add(el)
            self.statistics['sumOfSquares'] += math.pow(el, 2)
            if self.statistics['count'] > 0:
                self.statistics['average'] = self.statistics['sum'] / self.statistics['count']
                dif_of_sums = self._calculate_difference_of_sums(
                    self.statistics['sumOfSquares'], self.statistics['sum'], self.statistics['count'])
                if self.statistics['count'] > 1:
                    self.statistics['msdev'] = float(math.sqrt(dif_of_sums / self.statistics['count']))
                    self.statistics['stddev'] = float(math.sqrt(dif_of_sums / (self.statistics['count'] - 1)))
                else:
                    self.statistics['stddev'] = None
                    self.statistics['msdev'] = None

    def _update_statistics_min_and_max_on_add(self, el):
        if self.statistics['max'] is None or self.statistics['max'] < el:
            self.statistics['max'] = el

        if self.statistics['min'] is None or self.statistics['min'] > el:
            self.statistics['min'] = el

    def _add_record(self, empty_elements_count):
        if self._intermediaryRecord is not None:
            self.fill_array(self._firstQueueIndex)
            self.array[self._firstQueueIndex] = self._intermediaryRecord
            self._intermediaryRecord = None
        cur_index_in_array = self._update_running_statistics_on_remove(empty_elements_count)
        self._firstQueueIndex = cur_index_in_array

    def _calculate_difference_of_sums(self, sum1, sum2, count):
        return sum1 - math.pow(sum2, 2) / count

    def _update_intermediary_record(self, el):
        if self._intermediaryRecord is None:
            self._intermediaryRecord = {
                'count': 1,
                'sum': el,
                'max': el,
                'min': el,
                'average': el,
                'sumOfSquares': math.pow(el, 2)
            }
        else:
            if self._intermediaryRecord['max'] < el:
                self._intermediaryRecord['max'] = el
            if self._intermediaryRecord['min'] > el:
                self._intermediaryRecord['min'] = el
            self._intermediaryRecord['count'] += 1
            self._intermediaryRecord['sum'] += el
            self._intermediaryRecord['sumOfSquares'] += math.pow(el, 2)

    def _find_min(self, index):
        min = math.inf
        for i in range(len(self.array)):
            el = self.array[i]
            if el is not None and el['min'] is not None and el['min'] < min and i != index:
                min = el['min']
        if min == math.inf:
            return self._intermediaryRecord['min'] if self._intermediaryRecord is not None else None
        return min

    def _find_max(self, index):
        max = -math.inf
        for i in range(len(self.array)):
            el = self.array[i]
            if el is not None and el['max'] is not None and el['max'] > max and i != index:
                max = el['max']
        if max == -math.inf:
            return self._intermediaryRecord['max'] if self._intermediaryRecord is not None else None
        return max
