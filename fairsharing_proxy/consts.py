PACKAGE_NAME = 'fairsharing_proxy'
NICE_NAME = 'FAIRsharing proxy for DSW'
PACKAGE_VERSION = '0.1.0'
ENV_CONFIG = 'PROXY_CONFIG'
LOGGER_NAME = 'FAIRSHARING_PROXY'

_DEFAULT_BUILT_AT = 'BUILT_AT'
BUILT_AT = '--BUILT_AT--'
_DEFAULT_VERSION = 'VERSION'
VERSION = '--VERSION--'

DEFAULT_ENCODING = 'utf-8'
DEFAULT_CONFIG = '/app/config.yml'
DEFAULT_LOG_LEVEL = 'INFO'
DEFAULT_LOG_FORMAT = '%(asctime)s | %(levelname)s | %(module)s: %(message)s'

INFO_TEXT = 'This service can be used only for integration with DSW.' \
            'Any other use is strictly prohibited. All the data reachable ' \
            'through the proxy fall under the FAIRsharing license available ' \
            'at https://fairsharing.org/licence.'

BUILD_INFO = {
    'name': NICE_NAME,
    'packageVersion': PACKAGE_VERSION,
    'notice': INFO_TEXT,
    'version': VERSION if VERSION != f'--{_DEFAULT_VERSION}--' else 'unknown',
    'builtAt': BUILT_AT if BUILT_AT != f'--{_DEFAULT_BUILT_AT}--' else 'unknown',
}

URL_PREFIX = 'https://fairsharing.org/'
URL_PREFIX_LEN = len(URL_PREFIX)
