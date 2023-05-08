import yaml

from typing import List

from fairsharing_proxy.consts import DEFAULT_LOG_LEVEL, DEFAULT_LOG_FORMAT


class MissingConfigurationError(Exception):

    def __init__(self, missing: List[str]):
        self.missing = missing


class FAIRSharingConfig:

    def __init__(self, api: str, timeout: float):
        self.api = api
        self.timeout = timeout


class CacheConfig:

    def __init__(self, enabled: bool, username: str, password: str,
                 filename: str, page_delay: float, page_size: int,
                 page_timeout: int):
        self.enabled = enabled
        self.username = username
        self.password = password
        self.filename = filename
        self.page_delay = page_delay
        self.page_size = page_size
        self.page_timeout = page_timeout


class LoggingConfig:

    def __init__(self, level, message_format: str):
        self.level = level
        self.format = message_format


class ProxyConfig:

    def __init__(self, fairsharing: FAIRSharingConfig, logging: LoggingConfig,
                 cache: CacheConfig):
        self.fairsharing = fairsharing
        self.logging = logging
        self.cache = cache


class ProxyConfigParser:

    DEFAULTS = {
        'fairsharing': {
            'timeout': 25,
        },
        'logging': {
            'level': DEFAULT_LOG_LEVEL,
            'format': DEFAULT_LOG_FORMAT,
        },
        'cache': {
            'enabled': False,
            'username': '',
            'password': '',
            'file': '',
            'page_delay': 20,
            'page_size': 500,
            'page_timeout': 20,
        }
    }

    REQUIRED = [
        ['fairsharing', 'api'],
    ]

    def __init__(self):
        self.cfg = dict()

    def has(self, *path):
        x = self.cfg
        for p in path:
            if not hasattr(x, 'keys') or p not in x.keys():
                return False
            x = x[p]
        return True

    def _get_default(self, *path):
        x = self.DEFAULTS
        for p in path:
            x = x[p]
        return x

    def get_or_default(self, *path):
        x = self.cfg
        for p in path:
            if not hasattr(x, 'keys') or p not in x.keys():
                return self._get_default(*path)
            x = x[p]
        return x

    def validate(self):
        missing = []
        for path in self.REQUIRED:
            if not self.has(*path):
                missing.append('.'.join(path))
        if len(missing) > 0:
            raise MissingConfigurationError(missing)

    @property
    def _fairsharing(self):
        return FAIRSharingConfig(
            api=self.get_or_default('fairsharing', 'api'),
            timeout=float(self.get_or_default('fairsharing', 'timeout')),
        )

    @property
    def _logging(self):
        return LoggingConfig(
            level=self.get_or_default('logging', 'level'),
            message_format=self.get_or_default('logging', 'format'),
        )

    @property
    def _cache(self):
        return CacheConfig(
            enabled=self.get_or_default('cache', 'enabled'),
            username=self.get_or_default('cache', 'username'),
            password=self.get_or_default('cache', 'password'),
            filename=self.get_or_default('cache', 'file'),
            page_delay=float(self.get_or_default('cache', 'page_delay')),
            page_size=int(self.get_or_default('cache', 'page_size')),
            page_timeout=int(self.get_or_default('cache', 'page_timeout')),
        )

    def parse_file(self, fp) -> ProxyConfig:
        self.cfg = yaml.full_load(fp)
        self.validate()
        return self.config

    @property
    def config(self) -> ProxyConfig:
        return ProxyConfig(
            fairsharing=self._fairsharing,
            logging=self._logging,
            cache=self._cache,
        )


cfg_parser = ProxyConfigParser()
