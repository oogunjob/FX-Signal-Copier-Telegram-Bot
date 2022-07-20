from typing import Dict
from collections import deque
from datetime import datetime
import asyncio
from typing_extensions import TypedDict
from typing import Optional, List
from functools import reduce
from ..timeoutException import TimeoutException
from ..optionsValidator import OptionsValidator
from ...logger import LoggerManager
from ...metaApi.models import string_format_error
import math


class SynchronizationThrottlerOpts(TypedDict, total=False):
    """Options for synchronization throttler."""
    maxConcurrentSynchronizations: Optional[int]
    """Amount of maximum allowed concurrent synchronizations."""
    queueTimeoutInSeconds: Optional[float]
    """Allowed time for a synchronization in queue."""
    synchronizationTimeoutInSeconds: Optional[float]
    """Time after which a synchronization slot is freed to be used by another synchronization."""


class SynchronizationThrottler:
    """Synchronization throttler used to limit the amount of concurrent synchronizations to prevent application
    from being overloaded due to excessive number of synchronisation responses being sent."""

    def __init__(self, client, socket_instance_index: int, instance_number: int, region: str,
                 opts: SynchronizationThrottlerOpts = None):
        """Inits the synchronization throttler.

        Args:
            client: Websocket client.
            socket_instance_index: Index of socket instance that uses the throttler.
            instance_number: Instance index number.
            region: Server region.
            opts: Synchronization throttler options.
        """
        validator = OptionsValidator()
        opts: SynchronizationThrottlerOpts = opts or {}
        self._maxConcurrentSynchronizations = validator.validate_non_zero(
            opts['maxConcurrentSynchronizations'] if 'maxConcurrentSynchronizations' in opts else None, 15,
            'synchronizationThrottler.maxConcurrentSynchronizations')
        self._queueTimeoutInSeconds = validator.validate_non_zero(
            opts['queueTimeoutInSeconds'] if 'queueTimeoutInSeconds' in opts else None, 300,
            'synchronizationThrottler.queueTimeoutInSeconds')
        self._synchronizationTimeoutInSeconds = validator.validate_non_zero(
            opts['synchronizationTimeoutInSeconds'] if 'synchronizationTimeoutInSeconds' in opts else None, 10,
            'synchronizationThrottler.synchronizationTimeoutInSeconds')
        self._client = client
        self._region = region
        self._socketInstanceIndex = socket_instance_index
        self._synchronizationIds = {}
        self._accountsBySynchronizationIds = {}
        self._synchronizationQueue = deque([])
        self._removeOldSyncIdsInterval = None
        self._processQueueInterval = None
        self._instanceNumber = instance_number
        self._logger = LoggerManager.get_logger('SynchronizationThrottler')

    def start(self):
        """Initializes the synchronization throttler."""
        async def remove_old_sync_ids_interval():
            while True:
                await self._remove_old_sync_ids_job()
                await asyncio.sleep(1)

        async def process_queue_interval():
            while True:
                await self._process_queue_job()
                await asyncio.sleep(1)

        if not self._removeOldSyncIdsInterval:
            self._removeOldSyncIdsInterval = asyncio.create_task(remove_old_sync_ids_interval())
            self._processQueueInterval = asyncio.create_task(process_queue_interval())

    def stop(self):
        """Deinitializes the throttler."""
        if self._removeOldSyncIdsInterval:
            self._removeOldSyncIdsInterval.cancel()
            self._removeOldSyncIdsInterval = None
        if self._processQueueInterval:
            self._processQueueInterval.cancel()
            self._processQueueInterval = None

    async def _remove_old_sync_ids_job(self):
        now = datetime.now().timestamp()
        for key in list(self._synchronizationIds.keys()):
            if (now - self._synchronizationIds[key]) > self._synchronizationTimeoutInSeconds:
                del self._synchronizationIds[key]
        while len(self._synchronizationQueue) and \
                (datetime.now().timestamp() - self._synchronizationQueue[0]['queueTime']) > self._queueTimeoutInSeconds:
            self._remove_from_queue(self._synchronizationQueue[0]['synchronizationId'], 'timeout')
        self._advance_queue()
        await asyncio.sleep(1)

    def update_synchronization_id(self, synchronization_id: str):
        """Fills a synchronization slot with synchronization id.

        Args:
            synchronization_id: Synchronization id.
        """
        if synchronization_id in self._accountsBySynchronizationIds:
            self._synchronizationIds[synchronization_id] = datetime.now().timestamp()

    @property
    def synchronizing_accounts(self) -> List[str]:
        """Returns the list of currently synchronizing account ids."""
        synchronizing_accounts = []
        for key in self._synchronizationIds:
            account_data = self._accountsBySynchronizationIds[key] if key in \
                                                                      self._accountsBySynchronizationIds else None
            if account_data and (account_data['accountId'] not in synchronizing_accounts):
                synchronizing_accounts.append(account_data['accountId'])
        return synchronizing_accounts

    @property
    def active_synchronization_ids(self) -> List[str]:
        """Returns the list of currently active synchronization ids."""
        return list(self._accountsBySynchronizationIds.keys())

    @property
    def max_concurrent_synchronizations(self) -> int:
        """Returns the amount of maximum allowed concurrent synchronizations."""
        calculated_max = max(math.ceil(len(self._client.subscribed_account_ids(
            self._instanceNumber, self._socketInstanceIndex, self._region)) / 10), 1)
        return min(calculated_max, self._maxConcurrentSynchronizations)

    @property
    def is_synchronization_available(self) -> bool:
        """Whether there are free slots for synchronization requests."""

        def reducer_func(acc, socket_instance):
            return acc + len(socket_instance['synchronizationThrottler'].synchronizing_accounts)

        if reduce(reducer_func, self._client.socket_instances[self._region][self._instanceNumber],
                  0) >= self._maxConcurrentSynchronizations:
            return False
        return len(self.synchronizing_accounts) < self.max_concurrent_synchronizations

    def remove_id_by_parameters(self, account_id: str, instance_index: int = None, host: str = None):
        """Removes synchronizations from queue and from the list by parameters.

        Args:
            account_id: Account id.
            instance_index: Account instance index.
            host: Account host name.
        """
        for key in list(self._accountsBySynchronizationIds.keys()):
            if self._accountsBySynchronizationIds[key]['accountId'] == account_id and \
                    self._accountsBySynchronizationIds[key]['instanceIndex'] == instance_index and \
                    self._accountsBySynchronizationIds[key]['host'] == host:
                self.remove_synchronization_id(key)

    def remove_synchronization_id(self, synchronization_id: str):
        """Removes synchronization id from slots and removes ids for the same account from the queue.

        Args:
            synchronization_id: Synchronization id.
        """
        if synchronization_id in self._accountsBySynchronizationIds:
            account_id = self._accountsBySynchronizationIds[synchronization_id]['accountId']
            instance_index = self._accountsBySynchronizationIds[synchronization_id]['instanceIndex']
            host = self._accountsBySynchronizationIds[synchronization_id]['host']
            for key in list(self._accountsBySynchronizationIds.keys()):
                if self._accountsBySynchronizationIds[key]['accountId'] == account_id and \
                        self._accountsBySynchronizationIds[key]['instanceIndex'] == instance_index and \
                        self._accountsBySynchronizationIds[key]['host'] == host:
                    self._remove_from_queue(key, 'cancel')
                    del self._accountsBySynchronizationIds[key]
        if synchronization_id in self._synchronizationIds:
            del self._synchronizationIds[synchronization_id]
        self._advance_queue()

    def on_disconnect(self):
        """Clears synchronization ids on disconnect."""
        for synchronization in self._synchronizationQueue:
            if not synchronization['promise'].done():
                synchronization['promise'].set_result('cancel')
        self._synchronizationIds = {}
        self._accountsBySynchronizationIds = {}
        self._synchronizationQueue = deque([])
        self.stop()
        self.start()

    def _advance_queue(self):
        index = 0
        while self.is_synchronization_available and len(self._synchronizationQueue) and index < \
                len(self._synchronizationQueue):
            queue_item = self._synchronizationQueue[index]
            if not queue_item['promise'].done():
                queue_item['promise'].set_result('synchronize')
                self.update_synchronization_id(queue_item['synchronizationId'])
            index += 1

    def _remove_from_queue(self, synchronization_id: str, result: str):
        for i in range(len(self._synchronizationQueue)):
            sync_item = self._synchronizationQueue[i]
            if sync_item['synchronizationId'] == synchronization_id and not sync_item['promise'].done():
                sync_item['promise'].set_result(result)
        self._synchronizationQueue = deque(filter(lambda item: item['synchronizationId'] != synchronization_id,
                                                  self._synchronizationQueue))

    async def _process_queue_job(self):
        try:
            while len(self._synchronizationQueue):
                queue_item = self._synchronizationQueue[0]
                await queue_item['promise']
                if len(self._synchronizationQueue) and self._synchronizationQueue[0]['synchronizationId'] == \
                        queue_item['synchronizationId']:
                    self._synchronizationQueue.popleft()
        except Exception as err:
            self._logger.error('Error processing queue job ' + string_format_error(err))

    async def schedule_synchronize(self, account_id: str, request: Dict, get_hashes):
        """Schedules to send a synchronization request for account.

        Args:
            account_id: Account id.
            request: Request to send.
            get_hashes: Function to get terminal state hashes.
        """
        synchronization_id = request['requestId']
        for key in list(self._accountsBySynchronizationIds.keys()):
            if self._accountsBySynchronizationIds[key]['accountId'] == account_id and \
                     self._accountsBySynchronizationIds[key]['instanceIndex'] == \
                    (request['instanceIndex'] if 'instanceIndex' in request else None) and \
                    self._accountsBySynchronizationIds[key]['host'] == \
                    (request['host'] if 'host' in request else None):
                self.remove_synchronization_id(key)
        self._accountsBySynchronizationIds[synchronization_id] = {
            'accountId': account_id, 'instanceIndex': request['instanceIndex'] if 'instanceIndex' in request else None,
            'host': request['host'] if 'host' in request else None
        }
        if not self.is_synchronization_available:
            request_resolve = asyncio.Future()
            self._synchronizationQueue.append({
                'synchronizationId': synchronization_id,
                'promise': request_resolve,
                'queueTime': datetime.now().timestamp()
            })
            result = await request_resolve
            if result == 'cancel':
                return False
            elif result == 'timeout':
                raise TimeoutException(f'Account {account_id} synchronization {synchronization_id} timed out in '
                                       f'synchronization queue')
        self.update_synchronization_id(synchronization_id)
        hashes = await get_hashes()
        request['specificationsMd5'] = hashes['specificationsMd5']
        request['positionsMd5'] = hashes['positionsMd5']
        request['ordersMd5'] = hashes['ordersMd5']
        await self._client.rpc_request(account_id, request)
        return True
