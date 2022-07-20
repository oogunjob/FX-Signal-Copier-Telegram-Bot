from typing import Callable, Dict
from .avlTreeReservoir import reservoir


class StatisticalReservoir:
    """Statistical reservoir of a fixed size capable calculating percentiles."""

    def __init__(self, size: int, interval: int, random_number_gen: Callable = None):
        """Inits reservoir.

        Args:
            size: Reservoir size.
            interval: Reservoir interval in milliseconds.
            random_number_gen: Custom number generator.
        """
        self.reservoir = reservoir(size, interval, random_number_gen)
        self.length = self.reservoir['size']()

    def push_measurement(self, data: float):
        """Add element to reservoir.

        Args:
            data: Data to add."""
        self.reservoir['pushSome'](data)
        self.length = self.reservoir['size']()

    def get_percentile(self, p: float):
        """Calculate percentile statistics for values stored in reservoir.

        Args:
            p: Value in percents from 0 to 100.

        Returns:
            Percentile value."""
        self.length = self.reservoir['size']()
        return self.reservoir['getPercentile'](p)

    def restore_values(self, value: Dict):
        """Restore reservoir from saving data.

        Args:
            value: Stored value."""
        self.reservoir['restoreValues'](value)

    def to_array(self):
        return self.reservoir['toArray']()

    def to_value_array(self):
        return self.reservoir['toValueArray']()
