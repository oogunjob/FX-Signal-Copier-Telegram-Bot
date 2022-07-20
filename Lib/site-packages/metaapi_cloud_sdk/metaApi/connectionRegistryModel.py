from .historyStorage import HistoryStorage
from ..metaApi.metatraderAccountModel import MetatraderAccountModel
from abc import ABC, abstractmethod
from datetime import datetime


class ConnectionRegistryModel(ABC):
    """Defines interface for a connection registry class."""

    @abstractmethod
    def connect(self, account: MetatraderAccountModel, history_storage: HistoryStorage,
                history_start_time: datetime = None):
        """Creates and returns a new account connection if doesnt exist, otherwise returns old.

        Args:
            account: MetaTrader account to connect to.
            history_storage: Terminal history storage.
            history_start_time: History start time.

        Returns:
           Streaming metaapi connection.
        """

    @abstractmethod
    def remove(self, account_id: str):
        """Removes an account from registry.

        Args:
            account_id: MetaTrader account id to remove.
        """
