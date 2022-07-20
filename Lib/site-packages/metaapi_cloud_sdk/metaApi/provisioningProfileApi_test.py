from .provisioningProfile import ProvisioningProfile
from .provisioningProfileApi import ProvisioningProfileApi
from ..clients.metaApi.provisioningProfile_client import ProvisioningProfileClient, ProvisioningProfileDto
import pytest
from mock import MagicMock, AsyncMock


class MockClient(ProvisioningProfileClient):
    async def get_provisioning_profiles(self, version: int, status: str):
        pass

    async def get_provisioning_profile(self, id: str):
        pass

    async def create_provisioning_profile(self, provisioning_profile: ProvisioningProfileDto):
        pass

    async def delete_provisioning_profile(self, id: str):
        pass

    async def upload_provisioning_profile_file(self, provisioning_profile_id: str,
                                               file_name: str, file: str or memoryview):
        pass


client = MockClient(MagicMock(), 'token')
api = ProvisioningProfileApi(client)


class TestProvisioningProfileApi:

    @pytest.mark.asyncio
    async def test_retrieve_provisioning_profiles(self):
        """Should retrieve provisioning profiles."""

        client.get_provisioning_profiles = AsyncMock(return_value=[{'_id': 'id'}])
        profiles = await api.get_provisioning_profiles(4, 'new')
        for p in profiles:
            assert p.id == 'id'
            assert isinstance(p, ProvisioningProfile)

        client.get_provisioning_profiles.assert_called_with(4, 'new')

    @pytest.mark.asyncio
    async def test_retrieve_provisioning_profile(self):
        """Should retrieve provisioning profile by id."""

        client.get_provisioning_profile = AsyncMock(return_value={'_id': 'id', 'name': 'name',
                                                                  'version': 4, 'status': 'new',
                                                                  'brokerTimezone': 'EET',
                                                                  'brokerDSTSwitchTimezone': 'EET'})
        profile = await api.get_provisioning_profile('id')
        assert profile.id == 'id'
        assert profile.name == 'name'
        assert profile.version == 4
        assert profile.status == 'new'
        assert profile.broker_timezone == 'EET'
        assert profile.broker_dst_switch_timezone == 'EET'
        assert isinstance(profile, ProvisioningProfile)
        client.get_provisioning_profile.assert_called_with('id')

    @pytest.mark.asyncio
    async def test_create_provisioning_profile(self):
        """Should create provisioning profile."""

        client.create_provisioning_profile = AsyncMock(return_value={'id': 'id'})
        profile = await api.create_provisioning_profile({'name': 'name', 'version': 4, 'brokerTimezone': 'EET',
                                                         'brokerDSTSwitchTimezone': 'EET'})
        assert profile.id == 'id'
        assert profile.name == 'name'
        assert profile.version == 4
        assert profile.status == 'new'
        assert profile.broker_timezone == 'EET'
        assert profile.broker_dst_switch_timezone == 'EET'
        assert isinstance(profile, ProvisioningProfile)
        client.create_provisioning_profile.assert_called_with({'name': 'name', 'version': 4, 'brokerTimezone': 'EET',
                                                               'brokerDSTSwitchTimezone': 'EET'})

    @pytest.mark.asyncio
    async def test_reload_provisioning_profile(self):
        """Should reload provisioning profile."""

        client.get_provisioning_profile = AsyncMock(side_effect=[{'_id': 'id', 'name': 'name',
                                                                  'version': 4, 'status': 'new',
                                                                  'brokerTimezone': 'EET',
                                                                  'brokerDSTSwitchTimezone': 'EET'},
                                                                 {'_id': 'id', 'name': 'name',
                                                                  'version': 4, 'status': 'active',
                                                                  'brokerTimezone': 'EET',
                                                                  'brokerDSTSwitchTimezone': 'EET'
                                                                  }
                                                                 ])
        profile = await api.get_provisioning_profile('id')
        await profile.reload()
        assert profile.status == 'active'
        client.get_provisioning_profile.assert_called_with('id')
        assert client.get_provisioning_profile.call_count == 2

    @pytest.mark.asyncio
    async def test_remove_provisioning_profile(self):
        """Should remove provisioning profile."""

        client.get_provisioning_profile = AsyncMock(return_value={'_id': 'id', 'name': 'name',
                                                                  'version': 4, 'status': 'new',
                                                                  'brokerTimezone': 'EET',
                                                                  'brokerDSTSwitchTimezone': 'EET'
                                                                  })
        client.delete_provisioning_profile = AsyncMock()
        profile = await api.get_provisioning_profile('id')
        await profile.remove()
        client.delete_provisioning_profile.assert_called_with('id')

    @pytest.mark.asyncio
    async def test_upload_file_to_provisioning_profile(self):
        """Should upload a file to provisioning profile."""

        client.get_provisioning_profile = AsyncMock(return_value={'_id': 'id', 'name': 'name',
                                                                  'version': 4, 'status': 'new',
                                                                  'brokerTimezone': 'EET',
                                                                  'brokerDSTSwitchTimezone': 'EET'
                                                                  })
        client.upload_provisioning_profile_file = AsyncMock()
        profile = await api.get_provisioning_profile('id')
        await profile.upload_file('broker.srv', '/path/to/file.srv')
        client.upload_provisioning_profile_file.assert_called_with('id', 'broker.srv', '/path/to/file.srv')

    @pytest.mark.asyncio
    async def test_update_provisioning_profile(self):
        """Should update provisioning profile."""

        client.get_provisioning_profile = AsyncMock(return_value={'_id': 'id', 'name': 'name',
                                                                  'version': 4, 'status': 'new',
                                                                  'brokerTimezone': 'EET',
                                                                  'brokerDSTSwitchTimezone': 'EET'
                                                                  })
        client.update_provisioning_profile = AsyncMock()
        profile = await api.get_provisioning_profile('id')
        await profile.update({'name': 'name'})
        client.update_provisioning_profile.assert_called_with('id', {'name': 'name'})
