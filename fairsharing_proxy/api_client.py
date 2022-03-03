import asyncio
import httpx

from fairsharing_proxy.config import ProxyConfig
from fairsharing_proxy.model import Token, Record, SearchQuery

_NEED_LOGIN_MESSAGE = 'please login before continuing'


def _headers_with(token: Token):
    return {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': token.auth_header,
    }


class FAIRSharingUnauthorizedError(Exception):

    CONTENT = {
        'message': _NEED_LOGIN_MESSAGE
    }

    MESSAGE = {
        _NEED_LOGIN_MESSAGE
    }


class FAIRSharingClient:

    def __init__(self, cfg: ProxyConfig):
        self.api = cfg.fairsharing.api
        self.url_sign_in = f'{self.api}/users/sign_in'
        self.url_list = f'{self.api}/fairsharing_records'
        self.url_search = f'{self.api}/search/fairsharing_records'

    @staticmethod
    def _check_response(response: httpx.Response):
        # FAIRSharing is not using HTTP codes... need to check
        # using message string that is human-readable
        if response.is_success:
            msg = response.json().get('message', '').lower()
            if msg == _NEED_LOGIN_MESSAGE:
                raise FAIRSharingUnauthorizedError()
        response.raise_for_status()

    async def client_login(
            self, client: httpx.AsyncClient,
            username: str, password: str,
    ) -> Token:
        response = await client.post(
            url=self.url_sign_in,
            json={
                'user': {
                    'login': username,
                    'password': password,
                }
            }
        )
        response.raise_for_status()
        result = response.json()
        return Token(result)

    async def login(self, username: str, password: str) -> Token:
        async with httpx.AsyncClient() as client:
            return await self.client_login(
                client=client,
                username=username,
                password=password,
            )

    async def client_search(
            self, client: httpx.AsyncClient,
            query: SearchQuery, token: Token,
    ) -> list[Record]:
        # TODO: page size? page number?
        response = await client.post(
            url=self.url_search,
            params=query.params,
            headers=_headers_with(token),
        )
        self._check_response(response)
        result = response.json().get('data', [])
        return [rec for rec in (Record(**item) for item in result)
                if rec.is_valid()]

    async def search(
            self, query: SearchQuery, token: Token,
    ) -> list[Record]:
        async with httpx.AsyncClient() as client:
            return await self.client_search(client, query, token)

    async def client_list_records_url(
            self, client: httpx.AsyncClient, url: str, token: Token,
    ) -> list[Record]:
        response = await client.get(
            url=url,
            headers=_headers_with(token),
        )
        self._check_response(response)
        result = response.json().get('data', [])
        return [rec for rec in (Record(**item) for item in result)
                if rec.is_valid()]

    async def client_list_records(
            self, client: httpx.AsyncClient, token: Token,
            page_size=1, page_number=25,
    ) -> list[Record]:
        return await self.client_list_records_url(
            client=client,
            token=token,
            url=f'{self.url_list}'
                f'?page[number]={page_number}'
                f'&page[size]={page_size}'
        )

    async def list_records_url(
            self, url: str, token: Token,
    ) -> list[Record]:
        async with httpx.AsyncClient() as client:
            return await self.client_list_records_url(
                client=client,
                url=url,
                token=token,
            )

    async def list_records(
            self, token: Token, page_size=1, page_number=25,
    ) -> list[Record]:
        async with httpx.AsyncClient() as client:
            return await self.client_list_records(
                client=client,
                token=token,
                page_size=page_size,
                page_number=page_number,
            )

    async def client_list_records_all(
            self, client: httpx.AsyncClient, token: Token,
            page_size=500, timeout=25, page_delay=None,
    ) -> list[Record]:
        next_url = f'{self.url_list}?page[number]=1&page[size]={page_size}'
        records = list()  # type: list[Record]
        while next_url is not None:
            response = await client.get(
                url=next_url,
                headers=_headers_with(token),
                timeout=timeout,
            )
            self._check_response(response)
            result = response.json().get('data', [])
            records.extend((rec for rec in (Record(**item) for item in result)
                            if rec.is_valid()))
            next_url = response.json().get('links', {}).get('next', None)
            if page_delay is not None:
                await asyncio.sleep(page_delay)
        return records
