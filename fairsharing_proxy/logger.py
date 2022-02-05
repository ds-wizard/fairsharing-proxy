import logging
import sys

from fairsharing_proxy.config import ProxyConfig
from fairsharing_proxy.consts import LOGGER_NAME, \
    DEFAULT_LOG_LEVEL, DEFAULT_LOG_FORMAT


LOG = logging.getLogger(LOGGER_NAME)


def init_default_logging():
    logging.basicConfig(
        stream=sys.stdout,
        level=DEFAULT_LOG_LEVEL,
        format=DEFAULT_LOG_FORMAT,
    )


def init_config_logging(cfg: ProxyConfig):
    logging.basicConfig(
        stream=sys.stdout,
        level=cfg.logging.level,
        format=cfg.logging.format,
    )
