import httpx


class SpeakingApiClient:
    def __init__(self, base_url: str = 'http://127.0.0.1:8000', client=None):
        self.base_url = base_url.rstrip('/')
        self._client = client or httpx.AsyncClient(timeout=30)
        self._owns_client = client is None

    async def get(self, session_id: str):
        response = await self._client.get(f'{self.base_url}/api/speaking/sessions/{session_id}')
        response.raise_for_status()
        return response.json()

    async def submit(self, session_id: str, turn: dict):
        response = await self._client.post(
            f'{self.base_url}/api/speaking/sessions/{session_id}/turns', json=turn)
        response.raise_for_status()
        return response.json()

    async def close(self):
        if self._owns_client: await self._client.aclose()
