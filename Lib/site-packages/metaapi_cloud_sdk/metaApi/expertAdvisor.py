from ..clients.metaApi.expertAdvisor_client import ExpertAdvisorClient, ExpertAdvisorDto, NewExpertAdvisorDto


class ExpertAdvisor:
    """Implements an expert advisor entity."""

    def __init__(self, data: ExpertAdvisorDto, account_id: str, expert_advisor_client: ExpertAdvisorClient):
        """Inits an expert advisor entity.

        Args:
            data: Expert advisor data.
            account_id: Account id.
            expert_advisor_client: Expert advisor client.
        """
        self._data = data
        self._accountId = account_id
        self._expertAdvisorClient = expert_advisor_client

    @property
    def expert_id(self) -> str:
        """Returns expert id.

        Returns:
            Expert id.
        """
        return self._data['expertId']

    @property
    def period(self) -> str:
        """Returns expert period.

        Returns:
            Expert period.
        """
        return self._data['period']

    @property
    def symbol(self) -> str:
        """Returns expert symbol.

        Returns:
            Expert symbol.
        """
        return self._data['symbol']

    @property
    def file_uploaded(self) -> bool:
        """Returns true if expert file was uploaded."""
        return self._data['fileUploaded']

    async def reload(self):
        """Reloads expert advisor from API
        (see https://metaapi.cloud/docs/provisioning/api/expertAdvisor/readExpertAdvisor/).

        Returns:
            A coroutine resolving when expert advisor is updated.
        """
        self._data = await self._expertAdvisorClient.get_expert_advisor(self._accountId, self.expert_id)

    async def update(self, expert: NewExpertAdvisorDto):
        """Updates expert advisor data
        (see https://metaapi.cloud/docs/provisioning/api/expertAdvisor/updateExpertAdvisor/).

        Args:
            expert: New expert advisor data.

        Returns:
            A coroutine resolving when expert advisor is updated.
        """
        await self._expertAdvisorClient.update_expert_advisor(self._accountId, self.expert_id, expert)
        await self.reload()

    async def upload_file(self, file: str or memoryview):
        """Uploads an expert advisor file. EAs which use DLLs are not supported
        (see https://metaapi.cloud/docs/provisioning/api/expertAdvisor/uploadEAFile/).

        Args:
            file: Expert advisor file.

        Returns:
            A coroutine resolving when file upload is completed.
        """
        await self._expertAdvisorClient.upload_expert_advisor_file(self._accountId, self.expert_id, file)
        await self.reload()

    async def remove(self):
        """Removes expert advisor (see https://metaapi.cloud/docs/provisioning/api/expertAdvisor/deleteExpertAdvisor/).

        Returns:
            A coroutine resolving when expert advisor is removed.
        """
        await self._expertAdvisorClient.delete_expert_advisor(self._accountId, self.expert_id)
