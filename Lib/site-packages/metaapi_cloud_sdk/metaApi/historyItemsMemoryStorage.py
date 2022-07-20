import json
from copy import copy
from .models import format_date, date
from datetime import datetime


class HistoryItemsMemoryStorage:
    """Class to handle deals and history orders storage"""

    def __init__(self, comparator):
        self._items = {}
        self._comparator = comparator

    def insert(self, key: dict, value: dict):
        key = self._convert_key(key)
        self._items[key] = value

    def delete(self, key: dict):
        key = self._convert_key(key)
        if key in self._items:
            del self._items[key]

    def between_bounds(self, gte, lte):
        found_items = []
        for key in self._items.keys():
            valid = True

            item = self._items[key]

            if lte:
                for lte_key in lte.keys():
                    lte_item = lte[lte_key]
                    check_value = item[lte_key] if lte_key in item else date(0)

                    if check_value.timestamp() > lte_item.timestamp():
                        valid = False
                        break

            if not valid:
                continue

            if gte:
                for gte_key in gte.keys():
                    gte_item = gte[gte_key]
                    check_value = item[gte_key] if gte_key in item else date(0)

                    if check_value.timestamp() < gte_item.timestamp():
                        valid = False
                        break

            if valid:
                found_items.append(item)

        sorted_items = sorted(found_items, key=self._comparator)
        return sorted_items

    @staticmethod
    def _convert_key(key: dict) -> str:
        key = copy(key)
        for prop in key.keys():
            if isinstance(key[prop], datetime):
                key[prop] = format_date(key[prop])
        return json.dumps(key)
