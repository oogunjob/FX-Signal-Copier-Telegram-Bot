from abc import abstractmethod


class StopoutListener:
    """Stopout listener for handling a stream of stopout events."""

    @abstractmethod
    async def on_stopout(self, strategy_stopout_event):
        """Calls a predefined function with the packets data.

        Args:
            strategy_stopout_event: Strategy stopout event with an array of packets.
        """
        pass
