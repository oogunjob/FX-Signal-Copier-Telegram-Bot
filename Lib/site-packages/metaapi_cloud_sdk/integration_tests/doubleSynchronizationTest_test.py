from .. import MetaApi
import os
import pytest
import asyncio
import json

token = os.getenv('TOKEN')
login = os.getenv('LOGIN')
password = os.getenv('PASSWORD')
server_name = os.getenv('SERVER')
server_dat_file = os.getenv('PATH_TO_SERVERS_DAT')


class TestDoubleSync:
    @pytest.mark.asyncio
    async def test_not_corrupt(self):
        """Should not corrupt files after simultaneous synchronization."""
        if token:
            if not os.path.exists('.metaapi'):
                os.mkdir('.metaapi')
            api = MetaApi(token, {'application': 'MetaApi', 'domain': 'project-stock.v2.agiliumlabs.cloud'})
            profiles = await api.provisioning_profile_api.get_provisioning_profiles()
            profile = None
            for item in profiles:
                if item.name == server_name:
                    profile = item
                    break
            if not profile:
                profile = await api.provisioning_profile_api.create_provisioning_profile({
                    'name': server_name,
                    'version': 5,
                    'brokerTimezone': 'EET',
                    'brokerDSTSwitchTimezone': 'EET'
                })
                await profile.upload_file('servers.dat', server_dat_file)
            if profile and profile.status == 'new':
                await profile.upload_file('servers.dat', server_dat_file)
            accounts = await api.metatrader_account_api.get_accounts()
            account = None
            for item in accounts:
                if item.login == login and item.type.startswith('cloud'):
                    account = item
                    break
            if not account:
                account = await api.metatrader_account_api.create_account({
                    'name': 'Test account',
                    'type': 'cloud',
                    'login': login,
                    'password': password,
                    'server': server_name,
                    'provisioningProfileId': profile.id,
                    'application': 'MetaApi',
                    'magic': 1000
                })
            account_copy = await api.metatrader_account_api.get_account(account.id)
            await asyncio.gather(*[
                account.deploy(),
                account_copy.deploy()
            ])
            await asyncio.gather(*[
                account.wait_connected(),
                account_copy.wait_connected()
            ])
            connection = account.get_streaming_connection()
            connection_copy = account_copy.get_streaming_connection()
            await connection.connect()
            await connection_copy.connect()
            await asyncio.gather(*[
                connection.wait_synchronized({'timeoutInSeconds': 1200}),
                connection_copy.wait_synchronized({'timeoutInSeconds': 1200})
            ])
            await account.undeploy()
            await account_copy.undeploy()
            api._metaApiWebsocketClient.remove_all_listeners()
            json.loads(open(f'.metaapi/{account.id}-{account.application}-deals.bin').read())
            json.loads(open(f'.metaapi/{account.id}-{account.application}-historyOrders.bin').read())
