from typing_extensions import TypedDict
from httpx import Response
from ..metaApi_client import MetaApiClient
from typing import List


class ProvisioningProfileDto(TypedDict):
    """Provisioning profile model"""

    _id: str
    """Provisioning profile unique identifier"""
    name: str
    """Provisioning profile name"""
    version: int
    """MetaTrader version (allowed values are 4 and 5)"""
    status: str
    """Provisioning profile status (allowed values are new and active)"""
    brokerTimezone: str
    """Broker timezone name from Time Zone Database."""
    brokerDSTSwitchTimezone: str
    """Broker DST switch timezone name from Time Zone Database."""


class NewProvisioningProfileDto(TypedDict):
    """New provisioning profile model."""

    name: str
    """Provisioning profile name."""
    version: int
    """MetaTrader version (allowed values are 4 and 5)."""
    brokerTimezone: str
    """Broker timezone name from Time Zone Database."""
    brokerDSTSwitchTimezone: str
    """Broker DST switch timezone name from Time Zone Database."""


class ProvisioningProfileIdDto(TypedDict):
    """Provisioning profile id model."""

    id: str
    """Provisioning profile unique identifier."""


class ProvisioningProfileUpdateDto(TypedDict):
    """Updated provisioning profile data."""

    name: str
    """Provisioning profile name."""


class ProvisioningProfileClient(MetaApiClient):
    """metaapi.cloud provisioning profile API client (see https://metaapi.cloud/docs/provisioning/)"""

    async def get_provisioning_profiles(self, version: int, status: str) -> 'Response[List[ProvisioningProfileDto]]':
        """Retrieves provisioning profiles owned by user
        (see https://metaapi.cloud/docs/provisioning/api/provisioningProfile/readProvisioningProfiles/)

        Args:
            version: Optional version filter (allowed values are 4 and 5).
            status: Optional status filter (allowed values are new and active).

        Returns:
            A coroutine resolving with provisioning profiles found
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('get_provisioning_profiles')
        params = {}
        if version:
            params['version'] = version
        if status:
            params['status'] = status
        opts = {
            'url': f"{self._host}/users/current/provisioning-profiles",
            'method': 'GET',
            'params': params,
            'headers': {
                'auth-token': self._token
            }
        }
        return await self._httpClient.request(opts)

    async def get_provisioning_profile(self, id: str) -> 'Response[ProvisioningProfileDto]':
        """Retrieves a provisioning profile by id (see
        https://metaapi.cloud/docs/provisioning/api/provisioningProfile/readProvisioningProfile/). Throws an error if
        profile is not found.

        Args:
            id: Provisioning profile id.

        Returns:
            A coroutine resolving with provisioning profile found.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('get_provisioning_profile')
        opts = {
            'url': f"{self._host}/users/current/provisioning-profiles/{id}",
            'method': 'GET',
            'headers': {
                'auth-token': self._token
            }
        }
        return await self._httpClient.request(opts)

    async def create_provisioning_profile(self, provisioning_profile: NewProvisioningProfileDto) -> Response:
        """Creates a new provisioning profile (see
        https://metaapi.cloud/docs/provisioning/api/provisioningProfile/createNewProvisioningProfile/). After creating
        a provisioning profile you are required to upload extra files in order to activate the profile for further use.

        Args:
            provisioning_profile: Provisioning profile to create.

        Returns:
            A coroutine resolving with an id of the provisioning profile created.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('create_provisioning_profile')
        opts = {
            'url': f"{self._host}/users/current/provisioning-profiles",
            'method': 'POST',
            'headers': {
                'auth-token': self._token
            },
            'body': provisioning_profile
        }
        return await self._httpClient.request(opts)

    async def upload_provisioning_profile_file(self, provisioning_profile_id: str,
                                               file_name: str, file: str or memoryview) -> Response:
        """Uploads a file to a provisioning profile (see
        https://metaapi.cloud/docs/provisioning/api/provisioningProfile/uploadFilesToProvisioningProfile/).

        Args:
            provisioning_profile_id: Provisioning profile id to upload file to.
            file_name: Name of the file to upload. Allowed values are servers.dat for MT5 profile, broker.srv for
            MT4 profile.
            file: Path to a file to upload or buffer containing file contents.

        Returns:
            A coroutine resolving when file upload is completed.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('upload_provisioning_profile_file')
        if type(file) == str:
            file = open(file, 'rb').read()
        opts = {
            'method': 'PUT',
            'url': f'{self._host}/users/current/provisioning-profiles/{provisioning_profile_id}/{file_name}',
            'files': {
                'file': file
            },
            'headers': {
                'auth-token': self._token
            }
        }
        return await self._httpClient.request(opts)

    async def delete_provisioning_profile(self, id: str) -> Response:
        """ Deletes a provisioning profile (see
        https://metaapi.cloud/docs/provisioning/api/provisioningProfile/deleteProvisioningProfile/).
        Please note that in order to delete a provisioning profile you need to delete MT accounts connected to it first.

        Args:
            id: Provisioning profile id.

        Returns:
            A coroutine resolving when provisioning profile is deleted.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('delete_provisioning_profile')
        opts = {
            'url': f'{self._host}/users/current/provisioning-profiles/{id}',
            'method': 'DELETE',
            'headers': {
                'auth-token': self._token
            }
        }
        return await self._httpClient.request(opts)

    async def update_provisioning_profile(self, id: str, provisioning_profile: ProvisioningProfileUpdateDto):
        """Updates existing provisioning profile data (see
        https://metaapi.cloud/docs/provisioning/api/provisioningProfile/updateProvisioningProfile/).

        Args:
            id: Provisioning profile id.
            provisioning_profile: Updated provisioning profile.

        Returns:
            A coroutine resolving when provisioning profile is updated.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('update_provisioning_profile')
        opts = {
            'url': f'{self._host}/users/current/provisioning-profiles/{id}',
            'method': 'PUT',
            'headers': {
                'auth-token': self._token
            },
            'body': provisioning_profile
        }
        return await self._httpClient.request(opts)
