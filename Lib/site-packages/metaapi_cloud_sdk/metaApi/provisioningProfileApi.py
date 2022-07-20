from .provisioningProfile import ProvisioningProfile
from ..clients.metaApi.provisioningProfile_client import ProvisioningProfileClient, NewProvisioningProfileDto
from typing import List
from copy import deepcopy


class ProvisioningProfileApi:
    """Exposes provisioning profile API logic to the consumers."""

    def __init__(self, provisioning_profile_client: ProvisioningProfileClient):
        """Inits a provisioning profile API instance.

        Args:
            provisioning_profile_client: Provisioning profile REST API client.
        """
        self._provisioningProfileClient = provisioning_profile_client

    async def get_provisioning_profiles(self, version: int = None, status: str = None) -> List[ProvisioningProfile]:
        """Retrieves provisioning profiles

        Args:
            version: Optional version filter (allowed values are 4 and 5).
            status: Optional status filter (allowed values are new and active).

        Returns:
            A coroutine resolving with an array of provisioning profile entities.
        """

        profiles = await self._provisioningProfileClient.get_provisioning_profiles(version, status)
        return list(map(lambda profile: ProvisioningProfile(profile, self._provisioningProfileClient), profiles))

    async def get_provisioning_profile(self, provisioning_profile_id: str) -> ProvisioningProfile:
        """Retrieves a provisioning profile by id.

        Args:
            provisioning_profile_id: Provisioning profile id.

        Returns:
            A coroutine resolving with provisioning profile entity.
        """
        profile = await self._provisioningProfileClient.get_provisioning_profile(provisioning_profile_id)
        return ProvisioningProfile(profile, self._provisioningProfileClient)

    async def create_provisioning_profile(self, profile: NewProvisioningProfileDto) -> ProvisioningProfile:
        """Creates a provisioning profile.

        Args:
            profile: Provisioning profile data.

        Returns:
            A coroutine resolving with provisioning profile entity.
        """

        id = await self._provisioningProfileClient.create_provisioning_profile(profile)
        new_profile = deepcopy(profile)
        new_profile['_id'] = id['id']
        new_profile['status'] = 'new'
        return ProvisioningProfile(new_profile, self._provisioningProfileClient)
