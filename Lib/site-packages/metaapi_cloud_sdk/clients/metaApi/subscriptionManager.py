import asyncio
from random import uniform
from ..errorHandler import TooManyRequestsException
from ...metaApi.models import date, format_error, string_format_error
from datetime import datetime
from typing import List
from ...logger import LoggerManager


class SubscriptionManager:
    """Subscription manager to handle account subscription logic."""

    def __init__(self, websocket_client):
        """Inits the subscription manager.

        Args:
            websocket_client: Websocket client to use for sending requests.
        """
        self._websocketClient = websocket_client
        self._subscriptions = {}
        self._awaitingResubscribe = {}
        self._subscriptionState = {}
        self._logger = LoggerManager.get_logger('SubscriptionManager')

    def is_account_subscribing(self, account_id: str, instance_number: int = None):
        """Returns whether an account is currently subscribing.

        Args:
            account_id: Id of the MetaTrader account.
            instance_number: Instance index number.
        """
        if instance_number is not None:
            return account_id + ':' + str(instance_number) in self._subscriptions.keys()
        else:
            for key in self._subscriptions.keys():
                if key.startswith(account_id):
                    return True
            return False

    def is_disconnected_retry_mode(self, account_id: str, instance_number: int):
        """Returns whether an instance is in disconnected retry mode.

        Args:
            account_id: Id of the MetaTrader account.
            instance_number: Instance index number.
        """
        instance_id = account_id + ':' + str(instance_number or 0)
        return self._subscriptions[instance_id]['isDisconnectedRetryMode'] if instance_id in \
            self._subscriptions else False

    def is_subscription_active(self, account_id: str) -> bool:
        """Returns whether an account subscription is active.

        Args:
            account_id: account id.

        Returns:
            Instance actual subscribe state.
        """
        return account_id in self._subscriptionState

    def subscribe(self, account_id: str, instance_number):
        """Subscribes to the Metatrader terminal events
        (see https://metaapi.cloud/docs/client/websocket/api/subscribe/).

        Args:
            account_id: Id of the MetaTrader account to subscribe to.
            instance_number: Instance index number.

        Returns:
            A coroutine which resolves when subscription started.
        """
        self._subscriptionState[account_id] = True
        packet = {'type': 'subscribe'}
        if instance_number is not None:
            packet['instanceIndex'] = instance_number
        return self._websocketClient.rpc_request(account_id, packet)

    async def schedule_subscribe(self, account_id: str, instance_number: int = None, is_disconnected_retry_mode=False):
        """Schedules to send subscribe requests to an account until cancelled.

        Args:
            account_id: Id of the MetaTrader account.
            instance_number: Instance index number.
            is_disconnected_retry_mode: Whether to start subscription in disconnected retry mode. Subscription
                task in disconnected mode will be immediately replaced when the status packet is received.
        """
        instance_id = account_id + ':' + str(instance_number or 0)
        if instance_id not in self._subscriptions:
            self._subscriptions[instance_id] = {
                'shouldRetry': True,
                'task': None,
                'wait_task': None,
                'future': None,
                'isDisconnectedRetryMode': is_disconnected_retry_mode
            }
            subscribe_retry_interval_in_seconds = 3
            while self._subscriptions[instance_id]['shouldRetry']:
                async def subscribe_task():
                    try:
                        await self.subscribe(account_id, instance_number)
                    except TooManyRequestsException as err:
                        socket_instance_index = \
                            self._websocketClient.socket_instances_by_accounts[instance_number][account_id]
                        if err.metadata['type'] == 'LIMIT_ACCOUNT_SUBSCRIPTIONS_PER_USER':
                            self._logger.error(f'{instance_id}: Failed to subscribe ' + string_format_error(err))
                        if err.metadata['type'] in ['LIMIT_ACCOUNT_SUBSCRIPTIONS_PER_USER',
                                                    'LIMIT_ACCOUNT_SUBSCRIPTIONS_PER_SERVER',
                                                    'LIMIT_ACCOUNT_SUBSCRIPTIONS_PER_USER_PER_SERVER']:
                            del self._websocketClient.socket_instances_by_accounts[instance_number][account_id]
                            asyncio.create_task(self._websocketClient.lock_socket_instance(
                                instance_number, socket_instance_index,
                                self._websocketClient.get_account_region(account_id), err.metadata))
                        else:
                            nonlocal subscribe_retry_interval_in_seconds
                            retry_time = date(err.metadata['recommendedRetryTime']).timestamp()
                            if datetime.now().timestamp() + subscribe_retry_interval_in_seconds < retry_time:
                                await asyncio.sleep(retry_time - datetime.now().timestamp() -
                                                    subscribe_retry_interval_in_seconds)
                    except Exception as err:
                        pass

                self._subscriptions[instance_id]['task'] = asyncio.create_task(subscribe_task())
                await asyncio.wait({self._subscriptions[instance_id]['task']})
                if not self._subscriptions[instance_id]['shouldRetry']:
                    break
                retry_interval = subscribe_retry_interval_in_seconds
                subscribe_retry_interval_in_seconds = min(subscribe_retry_interval_in_seconds * 2, 300)
                subscribe_future = asyncio.Future()

                async def subscribe_task():
                    await asyncio.sleep(retry_interval)
                    subscribe_future.set_result(True)

                self._subscriptions[instance_id]['wait_task'] = asyncio.create_task(subscribe_task())
                self._subscriptions[instance_id]['future'] = subscribe_future
                result = await self._subscriptions[instance_id]['future']
                self._subscriptions[instance_id]['future'] = None
                if not result:
                    break
            del self._subscriptions[instance_id]

    async def unsubscribe(self, account_id: str, instance_number: int):
        """Unsubscribe from account (see https://metaapi.cloud/docs/client/websocket/api/synchronizing/unsubscribe).

        Args:
            account_id: Id of the MetaTrader account to retrieve symbol price for.
            instance_number: Instance index number.

        Returns:
            A coroutine which resolves when socket is unsubscribed."""
        self.cancel_account(account_id)
        if account_id in self._subscriptionState:
            del self._subscriptionState[account_id]
        return await self._websocketClient.rpc_request(account_id, {'type': 'unsubscribe',
                                                                    'instanceIndex': instance_number})

    def cancel_subscribe(self, instance_id: str):
        """Cancels active subscription tasks for an instance id.

        Args:
            instance_id: Instance id to cancel subscription task for.
        """
        if instance_id in self._subscriptions:
            subscription = self._subscriptions[instance_id]
            if subscription['future'] and not subscription['future'].done():
                subscription['future'].set_result(False)
                subscription['wait_task'].cancel()
            if subscription['task']:
                subscription['task'].cancel()
            subscription['shouldRetry'] = False

    def cancel_account(self, account_id):
        """Cancels active subscription tasks for an account.

        Args:
            account_id: Account id to cancel subscription tasks for.
        """
        for instance_id in list(filter(lambda key: key.startswith(account_id), self._subscriptions.keys())):
            self.cancel_subscribe(instance_id)
        for instance_number in self._awaitingResubscribe.keys():
            if account_id in self._awaitingResubscribe[instance_number]:
                del self._awaitingResubscribe[instance_number][account_id]

    def on_timeout(self, account_id: str, instance_number: int = None):
        """Invoked on account timeout.

        Args:
            account_id: Id of the MetaTrader account.
            instance_number: Instance index number.
        """
        region = self._websocketClient.get_account_region(account_id)
        if account_id in self._websocketClient.socket_instances_by_accounts[instance_number] and \
            self._websocketClient.connected(
                instance_number, self._websocketClient.socket_instances_by_accounts[instance_number][account_id],
                region):
            asyncio.create_task(self.schedule_subscribe(account_id, instance_number, is_disconnected_retry_mode=True))

    async def on_disconnected(self, account_id: str, instance_number: int = None):
        """Invoked when connection to MetaTrader terminal terminated.

        Args:
            account_id: Id of the MetaTrader account.
            instance_number: Instance index number.
        """
        await asyncio.sleep(uniform(1, 5))
        if instance_number in self._websocketClient.socket_instances_by_accounts and \
                account_id in self._websocketClient.socket_instances_by_accounts[instance_number]:
            asyncio.create_task(self.schedule_subscribe(account_id, instance_number, is_disconnected_retry_mode=True))

    def on_reconnected(self, instance_number: int, socket_instance_index: int, reconnect_account_ids: List[str]):
        """Invoked when connection to MetaApi websocket API restored after a disconnect.

        Args:
            instance_number: Instance index number.
            socket_instance_index: Socket instance index.
            reconnect_account_ids: Account ids to reconnect.
        """
        if instance_number not in self._awaitingResubscribe:
            self._awaitingResubscribe[instance_number] = {}

        async def wait_resubscribe(account_id):
            try:
                if account_id not in self._awaitingResubscribe[instance_number]:
                    self._awaitingResubscribe[instance_number][account_id] = True
                    while self.is_account_subscribing(account_id, instance_number):
                        await asyncio.sleep(1)
                    await asyncio.sleep(uniform(0, 5))
                    if account_id in self._awaitingResubscribe[instance_number]:
                        del self._awaitingResubscribe[instance_number][account_id]
                        asyncio.create_task(self.schedule_subscribe(account_id, instance_number))
            except Exception as err:
                self._logger.error(f'{account_id}: Account resubscribe task failed ' + string_format_error(err))

        try:
            socket_instances_by_accounts = self._websocketClient.socket_instances_by_accounts[instance_number]
            for instance_id in self._subscriptions.keys():
                account_id = instance_id.split(':')[0]
                if account_id in socket_instances_by_accounts and \
                        socket_instances_by_accounts[account_id] == socket_instance_index:
                    self.cancel_subscribe(instance_id)

            for account_id in reconnect_account_ids:
                asyncio.create_task(wait_resubscribe(account_id))
        except Exception as err:
            self._logger.error(f'Failed to process subscribe manager reconnected event ' + string_format_error(err))
