from ..metaApi_client import MetaApiClient
from typing_extensions import TypedDict
from typing import List
from httpx import Response


class ExpertAdvisorDto(TypedDict):
    """Expert advisor model"""
    expertId: str
    """Expert advisor id."""
    period: str
    """Expert advisor period."""
    symbol: str
    """Expert advisor symbol."""
    fileUploaded: bool
    """True if expert file was uploaded."""


class NewExpertAdvisorDto(TypedDict):
    """Updated expert advisor data."""
    period: str
    """Expert advisor period.
    For MetaTrader 4 allowed periods are 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1mn
    For MetaTrader 5 allowed periods are 1m, 2m, 3m, 4m, 5m, 6m, 10m, 12m, 15m, 20m, 30m, 1h, 2h, 3h, 4h, 6h, 8h, 12h,
    1d, 1w, 1mn"""
    symbol: str
    """Expert advisor symbol."""
    preset: str
    """Base64-encoded preset file."""


class ExpertAdvisorClient(MetaApiClient):
    """metaapi.cloud expert advisor API client (see https://metaapi.cloud/docs/provisioning/)"""

    async def get_expert_advisors(self, account_id: str) -> List[ExpertAdvisorDto]:
        """Retrieves expert advisors by account id (see
        https://metaapi.cloud/docs/provisioning/api/expertAdvisor/readExpertAdvisors/)
        Method is accessible only with API access token

        Args:
            account_id: Metatrader account id.

        Returns:
            A coroutine resolving with List[ExpertAdvisorDto] - expert advisors found.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('get_expert_advisors')
        opts = {
            'url': f'{self._host}/users/current/accounts/{account_id}/expert-advisors',
            'method': 'GET',
            'headers': {
                'auth-token': self._token
            }
        }
        return await self._httpClient.request(opts)

    async def get_expert_advisor(self, account_id: str, expert_id: str) -> ExpertAdvisorDto:
        """Retrieves an expert advisor by id (see
        https://metaapi.cloud/docs/provisioning/api/expertAdvisor/readExpertAdvisor/).
        Thrown an error if expert is not found. Method is accessible only with API access token

        Args:
            account_id: Metatrader account id.
            expert_id: Expert advisor id.

        Returns:
            A coroutine resolving with ExpertAdvisorDto - expert advisor found.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('get_expert_advisor')
        opts = {
            'url': f'{self._host}/users/current/accounts/{account_id}/expert-advisors/{expert_id}',
            'method': 'GET',
            'headers': {
                'auth-token': self._token
            }
        }
        return await self._httpClient.request(opts)

    async def update_expert_advisor(self, account_id: str, expert_id: str, expert: NewExpertAdvisorDto) -> Response:
        """Updates or creates expert advisor data (see
        https://metaapi.cloud/docs/provisioning/api/expertAdvisor/updateExpertAdvisor/).
        Method is accessible only with API access token

        Args:
            account_id: Metatrader account id.
            expert_id: Expert advisor id.
            expert: New expert advisor data.

        Returns:
            A coroutine resolving when expert advisor is updated.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('update_expert_advisor')
        opts = {
            'url': f'{self._host}/users/current/accounts/{account_id}/expert-advisors/{expert_id}',
            'method': 'PUT',
            'headers': {
                'auth-token': self._token
            },
            'body': expert
        }
        return await self._httpClient.request(opts)

    async def upload_expert_advisor_file(self, account_id: str, expert_id: str, file: str or memoryview) -> Response:
        """Uploads an expert advisor file (see https://metaapi.cloud/docs/provisioning/api/expertAdvisor/uploadEAFile/)
        Method is accessible only with API access token

        Args:
            account_id: Metatrader account id.
            expert_id: Expert advisor id.
            file: Path to a file to upload or buffer containing file contents.

        Returns:
            A coroutine resolving when file upload is completed.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('upload_expert_advisor_file')
        if type(file) == str:
            file = open(file, 'rb').read()
        opts = {
            'url': f'{self._host}/users/current/accounts/{account_id}/expert-advisors/{expert_id}/file',
            'method': 'PUT',
            'files': {
                'file': file
            },
            'headers': {
                'auth-token': self._token
            }
        }
        return await self._httpClient.request(opts)

    async def delete_expert_advisor(self, account_id: str, expert_id: str) -> Response:
        """Deletes an expert advisor
        (see https://metaapi.cloud/docs/provisioning/api/expertAdvisor/deleteExpertAdvisor/)
        Method is accessible only with API access token.

        Args:
            account_id: Metatrader account id.
            expert_id: Expert advisor id.

        Returns:
            A coroutine resolving when expert advisor is deleted.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('delete_expert_advisor')
        opts = {
            'url': f'{self._host}/users/current/accounts/{account_id}/expert-advisors/{expert_id}',
            'method': 'DELETE',
            'headers': {
                'auth-token': self._token
            }
        }
        return await self._httpClient.request(opts)
