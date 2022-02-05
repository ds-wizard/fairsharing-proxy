import base64
import httpx
import os
import pathlib

import fastapi

from fairsharing_proxy.cache import RecordsCache
from fairsharing_proxy.config import ProxyConfig, cfg_parser
from fairsharing_proxy.consts import DEFAULT_CONFIG, ENV_CONFIG
from fairsharing_proxy.api_client import FAIRSharingClient, \
    FAIRSharingUnauthorizedError
from fairsharing_proxy.logger import LOG, init_config_logging
from fairsharing_proxy.model import Token, ProxyRequest, \
    LegacySearchQuery, SearchQuery, RecordSet


def _load_config() -> ProxyConfig:
    config_file = os.getenv(ENV_CONFIG, DEFAULT_CONFIG)
    try:
        with pathlib.Path(config_file).open() as fp:
            cfg = cfg_parser.parse_file(fp=fp)
    except Exception as e:
        LOG.error(f'[CONFIG] Failed to load config: {config_file}')
        LOG.debug(str(e))
        exit(1)
    LOG.info(f'Loaded config: {config_file}')
    return cfg


class TokenStore:

    def __init__(self):
        self._tokens = dict()  # type: dict[str, Token]

    def has_token(self, username: str) -> bool:
        return username in self._tokens

    def get_token(self, username: str) -> Token:
        return self._tokens[username]

    def clear_token(self, username: str):
        self._tokens.pop(username)

    def has_usable_token(self, username: str) -> bool:
        if not self.has_token(username):
            return False
        return not self.get_token(username).should_refresh

    def store_token(self, username: str, token: Token):
        self._tokens[username] = token


class _ProxyCore:

    _instance = None

    def __new__(cls):
        try:
            assert cls._instance is not None
            return cls._instance
        except AssertionError:
            cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self):
        self.cfg = _load_config()  # type: ProxyConfig
        self.cache = RecordsCache(cfg=self.cfg)
        self.client = FAIRSharingClient(cfg=self.cfg)
        self.token_store = TokenStore()

    @staticmethod
    def _extract_credentials(rq: ProxyRequest, auth_str: str) -> tuple[str, str]:
        try:
            decoded = base64.b64decode(auth_str).decode('utf-8')
            parts = decoded.split(':', maxsplit=1)
            assert len(parts) == 2
            return parts[0], parts[1]
        except Exception as e:
            LOG.warning(f'[RQ:{rq.trace_id}] Invalid authorization: {str(e)}')
            raise fastapi.HTTPException(
                status_code=400,
                detail='Invalid authorization provided.',
            )

    async def _get_token(self, rq: ProxyRequest, auth_str: str) -> Token:
        username, password = self._extract_credentials(rq, auth_str)
        if self.token_store.has_usable_token(username):
            return self.token_store.get_token(username)
        try:
            token = await self.client.login(username, password)
            if not token.ok:
                raise fastapi.HTTPException(
                    status_code=401,
                    detail=f'Could not authenticate via remote API: {token.message}'
                )
            self.token_store.store_token(username, token)
            return token
        except Exception as e:
            LOG.warning(f'[RQ:{rq.trace_id}] Failed to login: {str(e)}')
            raise fastapi.HTTPException(
                status_code=500,
                detail='Failed to login via remote API.'
            )

    async def legacy_search(
            self, request: fastapi.Request, *, retry=True,
    ) -> fastapi.Response:
        # TODO: use fastapi.HTTPException
        # TODO: cache
        rq = ProxyRequest(request=request)
        head_auth = rq.headers.get('Api-Key', '')
        token = await self._get_token(rq, head_auth)
        query = LegacySearchQuery.from_params(params=request.query_params)
        try:
            results = await self.client.search(
                token=token,
                query=query.to_query(),
            )
        except FAIRSharingUnauthorizedError as e:
            self.token_store.clear_token(token.username)
            if retry:
                return await self.legacy_search(request, retry=False)
            else:
                return fastapi.responses.JSONResponse(
                    status_code=401,
                    content=e.CONTENT,
                )
        except httpx.HTTPStatusError as e:
            return fastapi.responses.JSONResponse(
                status_code=e.response.status_code,
                content=e.response.json(),
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return fastapi.responses.JSONResponse(
                status_code=500,
                content={
                    'message': f'Failed to execute FAIRSharing request: {str(e)}',
                },
            )
        result_set = RecordSet(results)
        return fastapi.responses.JSONResponse(
            status_code=200,
            content=result_set.to_legacy_json(),
        )

    async def search(
            self, request: fastapi.Request, *, retry=True,
    ) -> fastapi.Response:
        # TODO: use fastapi.HTTPException
        # TODO: cache
        rq = ProxyRequest(request=request)
        head_auth = rq.headers.get('Authorization', '')
        token = await self._get_token(rq, head_auth)
        query = SearchQuery.from_params(params=request.query_params)
        try:
            results = await self.client.search(
                token=token,
                query=query,
            )
        except FAIRSharingUnauthorizedError as e:
            self.token_store.clear_token(token.username)
            if retry:
                return await self.search(request, retry=False)
            else:
                return fastapi.responses.JSONResponse(
                    status_code=401,
                    content=e.CONTENT,
                )
        except httpx.HTTPStatusError as e:
            return fastapi.responses.JSONResponse(
                status_code=e.response.status_code,
                content=e.response.json(),
            )
        except Exception as e:
            return fastapi.responses.JSONResponse(
                status_code=500,
                content={
                    'message': f'Failed to execute FAIRSharing request: {str(e)}',
                },
            )
        result_set = RecordSet(results)
        return fastapi.responses.JSONResponse(
            status_code=200,
            content=result_set.to_json(),
        )

    async def startup(self):
        init_config_logging(cfg=self.cfg)

    async def shutdown(self):
        self.cache.finalize()


CORE = _ProxyCore()
