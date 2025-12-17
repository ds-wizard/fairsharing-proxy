import asyncio
import httpx

from gql import gql, Client
from gql.transport.httpx import HTTPXAsyncTransport

from .config import ProxyConfig
from .model import Token, Record, SearchQuery, GraphQLFastSearchQuery

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
        self.timeout = cfg.fairsharing.timeout

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
            },
            timeout=self.timeout,
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
            timeout=self.timeout,
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
            page_size=500, timeout=None, page_delay=None,
    ) -> list[Record]:
        next_url = f'{self.url_list}?page[number]=1&page[size]={page_size}'
        records = list()  # type: list[Record]
        while next_url is not None:
            response = await client.get(
                url=next_url,
                headers=_headers_with(token),
                timeout=timeout or self.timeout,
            )
            self._check_response(response)
            result = response.json().get('data', [])
            records.extend((rec for rec in (Record(**item) for item in result)
                            if rec.is_valid()))
            next_url = response.json().get('links', {}).get('next', None)
            if page_delay is not None:
                await asyncio.sleep(page_delay)
        return records


def gql_list(values):
    return "[" + ", ".join(f'"{v}"' for v in values) + "]"


def build_where_literal(
    registries: list[str] | None = None,
    types: list[str] | None = None,
    statuses: list[str] | None = None,
):
    filters = []
    if registries:
        filters.append(f"registry: {gql_list(registries)}")
    if types:
        filters.append(f"type: {gql_list(types)}")
    if statuses:
        filters.append(f"status: {gql_list(statuses)}")
    if not filters:
        return """
        {
          operator: "_and"
          fields: []
        }
        """
    inner = "\n".join(filters)
    return f"""
    {{
      operator: "_and"
      fields: [
        {{
          operator: "_and"
          {inner}
        }}
      ]
    }}
    """


class FAIRSharingGraphQLClient:

    def __init__(self, cfg: ProxyConfig):
        self.transport = HTTPXAsyncTransport(
            url=cfg.fairsharing.graphql_api,
            headers={
                'User-Agent': 'fairsharing-proxy/0.1',
                'X-GraphQL-Key': cfg.fairsharing.graphql_key,
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
        )

    async def _execute(self, query, variables=None):
        async with Client(transport=self.transport,
                          fetch_schema_from_transport=False) as client:
            result = await client.execute(query, variables)
            return result

    async def search(self, query: GraphQLFastSearchQuery):
        where_literal = build_where_literal(
            registries=query.registry,
            types=query.record_type,
            statuses=query.status,
        )
        gquery = gql(f"""
        query {{
          advancedSearchFast(
            q: "{query.q}"
            where: {where_literal}
          ) {{
            id
            type
            name
            homepage
            abbreviation
            doi
            description
            registry
            status
          }}
        }}
        """)
        result = await self._execute(
            query=gquery,
        )
        return result['advancedSearchFast']
