from ..clients.metaApi.provisioningProfile_client import ProvisioningProfileDto, ProvisioningProfileClient
from httpx import Response


class ProvisioningProfile:
    """Implements a provisioning profile entity"""
    def __init__(self, data: ProvisioningProfileDto, provisioning_profile_client: ProvisioningProfileClient):
        """Inits a provisioning profile entity.

        Args:
            data: Provisioning profile data.
            provisioning_profile_client: Provisioning profile REST API client.
        """
        self._data = data
        self._provisioningProfileClient = provisioning_profile_client

    @property
    def id(self) -> str:
        """Returns profile id.

        Returns:
            Profile id.
        """
        return self._data['_id']

    @property
    def name(self) -> str:
        """Returns profile name.

        Returns:
            Profile name.
        """
        return self._data['name']

    @property
    def version(self) -> int:
        """Returns profile version. Possible values are 4 and 5.

        Returns:
            Profile version.
        """
        return self._data['version']

    @property
    def status(self) -> str:
        """Returns profile status. Possible values are new and active.

        Returns:
            Profile status.
        """
        return self._data['status']

    @property
    def broker_timezone(self) -> str:
        """Returns broker timezone name from Time Zone Database.

        Returns:
            Broker timezone name.
        """
        return self._data['brokerTimezone']

    @property
    def broker_dst_switch_timezone(self) -> str:
        """Returns broker DST timezone name from Time Zone Database.

        Returns:
            Broker DST switch timezone name.
        """
        return self._data['brokerDSTSwitchTimezone']

    async def reload(self):
        """Reloads provisioning profile from API.

        Returns:
            A coroutine resolving when provisioning profile is updated.
        """
        self._data = await self._provisioningProfileClient.get_provisioning_profile(self.id)

    async def remove(self) -> Response:
        """Removes provisioning profile. The current object instance should be discarded after returned promise
        resolves.

        Returns:
            A coroutine resolving when provisioning profile is removed.
        """
        return await self._provisioningProfileClient.delete_provisioning_profile(self.id)

    async def upload_file(self, file_name: str, file: str or memoryview) -> Response:
        """Uploads a file to provisioning profile.

        Args:
            file_name: Name of the file to upload. Allowed values are servers.dat for MT5 profile, broker.srv for
            MT4 profile.
            file: Path to a file to upload or buffer containing file contents.

        Returns:
            A coroutine which resolves when the file was uploaded.
        """
        return await self._provisioningProfileClient.upload_provisioning_profile_file(self.id, file_name, file)

    async def update(self, profile):
        """Updates provisioning profile.

        Args:
            profile: Provisioning profile update.

        Returns:
            A coroutine resolving when provisioning profile is updated.
        """
        await self._provisioningProfileClient.update_provisioning_profile(self.id, profile)
        await self.reload()
