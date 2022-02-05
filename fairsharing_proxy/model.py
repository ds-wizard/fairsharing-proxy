import datetime
import fastapi
import json
import uuid

from typing import Optional, Mapping

from fairsharing_proxy.consts import URL_PREFIX, URL_PREFIX_LEN


class ProxyRequest:

    def __init__(self, request: fastapi.Request):
        self.trace_id = str(uuid.uuid4())
        self.ts_started = datetime.datetime.utcnow()
        self.ts_finished = None  # type: Optional[datetime.datetime]
        self.request = request

    @property
    def headers(self):
        return self.request.headers


class Token:

    EXPIRY_EPSILON = 300  # seconds

    def __init__(self, data: dict):
        self.token = data.get('jwt', '')  # type: str
        self.username = data.get('username', '')  # type: str
        self.message = data.get('message', '')  # type: str
        self.expiry = int(data.get('expiry', 0))  # type: int
        self.success = data.get('success', False) and self.token != ''

    @property
    def ok(self) -> bool:
        return self.success and self.token != '' and not self.is_expired

    @property
    def auth_header(self) -> str:
        return f'Bearer {self.token}'

    @property
    def is_expired(self) -> bool:
        now = datetime.datetime.utcnow()
        return now.timestamp() >= self.expiry

    @property
    def is_almost_expired(self) -> bool:
        now = datetime.datetime.utcnow()
        return now.timestamp() + self.EXPIRY_EPSILON >= self.expiry

    @property
    def should_refresh(self) -> bool:
        return not self.ok or self.is_almost_expired


class SearchQuery:

    def __init__(self, query: str, **kwargs):
        self.query = query  # type: str
        self.registry = kwargs.get('registry', None)  # type: Optional[str]
        self.status = kwargs.get('status', None)  # type: Optional[str]
        self.record_type = kwargs.get('record_type', None)  # type: Optional[str]
        self.countries = kwargs.get('countries', None)  # type: Optional[str]
        self.subjects = kwargs.get('subjects', None)  # type: Optional[str]
        self.domains = kwargs.get('domains', None)  # type: Optional[str]
        self.taxonomies = kwargs.get('taxonomies', None)  # type: Optional[str]
        self.user_defined_tags = kwargs.get(
            'user_defined_tags', None
        )  # type: Optional[str]
        self.is_recommended = kwargs.get('is_recommended', None)  # type: Optional[str]
        self.is_approved = kwargs.get('is_approved', None)  # type: Optional[str]
        self.is_maintained = kwargs.get('is_maintained', None)  # type: Optional[str]

    @staticmethod
    def from_params(params: Mapping):
        return SearchQuery(
            query=params.get('q', ''),
            registry=params.get('registry', None),
            status=params.get('status', None),
            record_type=params.get('record_type', None),
            countries=params.get('countries', None),
            subjects=params.get('subjects', None),
            domains=params.get('domains', None),
            taxonomies=params.get('taxonomies', None),
            user_defined_tags=params.get('user_defined_tags', None),
            is_recommended=params.get('is_recommended', None),
            is_approved=params.get('is_approved', None),
            is_maintained=params.get('is_maintained', None),
        )

    @property
    def params(self) -> dict[str, str]:
        params = {
            'fairsharing_registry': self.registry,
            'status': self.status,
            'record_type': self.record_type,
            'domains': self.domains,
            'subjects': self.subjects,
            'countries': self.countries,
            'taxonomies': self.taxonomies,
            'user_defined_tags': self.user_defined_tags,
            'is_recommended': self.is_recommended,
            'is_approved': self.is_approved,
            'is_maintained': self.is_maintained,
        }
        result = dict()
        if len(self.query) > 0:
            result['q'] = self.query
        for key in params.keys():
            if params[key] is not None:
                s = params[key] or ''
                if s.startswith('is_') and s not in ('true', 'false'):
                    continue
                result[key] = s
        return result


class LegacySearchQuery:

    def __init__(self, query: str, **kwargs):
        self.query = query  # type: str
        self.registry = kwargs.get('registry', None)  # type: Optional[str]
        self.domains = kwargs.get('domains', None)  # type: Optional[str]
        self.taxonomies = kwargs.get('taxonomies', None)  # type: Optional[str]
        self.disciplines = kwargs.get('disciplines', None)  # type: Optional[str]
        self.countries = kwargs.get('countries', None)  # type: Optional[str]
        self.tags = kwargs.get('tags', None)  # type: Optional[str]

    @staticmethod
    def from_params(params: Mapping):
        return LegacySearchQuery(
            query=params.get('q', ''),
            registry=params.get('registry', None),
            domains=params.get('domains', None),
            taxonomies=params.get('taxonomies', None),
            disciplines=params.get('disciplines', None),
            tags=params.get('tags', None),
        )

    def to_query(self) -> SearchQuery:
        return SearchQuery(
            query=self.query,
            registry=self.registry,
            domains=self.domains,
            taxonomies=self.taxonomies,
            subjects=self.disciplines,
            countries=self.countries,
            user_defined_tags=self.tags,
        )


class Record:

    def __init__(self, **data: dict):
        self.fairsharing_id = str(data.get('id', ''))  # type: str
        attrs = data.get('attributes', {})  # type: dict
        self.registry = attrs.get('fairsharing-registry', '').lower()  # type: str
        self.record_type = attrs.get('record-type', '').lower()  # type: str
        self.name = attrs.get('name', '')  # type: str
        self.description = attrs.get('description', '')  # type: str
        self.abbreviation = attrs.get('abbreviation', '')  # type: str
        self.doi = attrs.get('doi', None)  # type: Optional[str]
        self.url = attrs.get('url', '')  # type: str
        self.subjects = attrs.get('subjects', [])  # type: list[str]
        self.domains = attrs.get('domains', [])  # type: list[str]
        self.taxonomies = attrs.get('taxonomies', [])  # type: list[str]
        self.user_defined_tags = attrs.get('user-defined-tags', [])  # type: list[str]
        self.countries = attrs.get('countries', [])  # type: list[str]
        self.fairsharing_licence = attrs.get('fairsharing-licence', '')  # type: str
        self.legacy_ids = attrs.get('legacy-ids', [])  # type: list[str]
        self.created_at = attrs.get('created-at', '')  # type: str
        self.updated_at = attrs.get('updated-at', '')  # type: str

    @staticmethod
    def optimize_text(text: str):
        parts = text.split(':', maxsplit=1)
        if len(parts) == 2 and 'FAIRsharing' in parts[0]:
            return parts[1]
        return text

    def rectify(self):
        self.name = self.optimize_text(self.name)
        self.description = self.optimize_text(self.description)

    def is_valid(self) -> bool:
        return self.fairsharing_id != '' and self.name != ''

    def to_legacy_json(self) -> dict:
        record_id = 'unknown'
        if self.url.startswith(URL_PREFIX):
            record_id = self.url[URL_PREFIX_LEN:]
        else:
            for legacy_id in self.legacy_ids:
                if legacy_id.startswith('bsg'):
                    record_id = legacy_id
                    break
        return {
            'record_id': record_id,
            'name': self.name,
            'shortname': self.abbreviation,
            'description': self.description,
            'registry': self.registry,
            'type': self.record_type,
            'subtype': None,
            'doi': self.doi,
            'countries': self.countries,
            'onto_disciplines': self.subjects,
            'onto_domains': self.domains,
            'taxonomies': self.taxonomies,
            'user_defined_tags': self.user_defined_tags,
        }

    def to_json(self) -> dict:
        return {}

    def to_row(self):
        return (
            self.fairsharing_id,
            self.registry,
            self.record_type,
            self.name,
            self.description,
            self.abbreviation,
            self.doi,
            self.url,
            json.dumps({
                'subjects': self.subjects,
                'domains': self.domains,
                'taxonomies': self.taxonomies,
                'user_defined_tags': self.user_defined_tags,
                'countries': self.countries,
                'fairsharing_licence': self.fairsharing_licence,
                'legacy_ids': self.legacy_ids,
            }),
            self.created_at,
            self.updated_at,
        )

    def from_row(self, data: tuple):
        self.fairsharing_id = data[0]
        self.registry = data[1]
        self.record_type = data[2]
        self.name = data[3]
        self.description = data[4]
        self.abbreviation = data[5]
        self.doi = data[6]
        self.url = data[7]
        additional = json.loads(data[8])
        self.subjects = additional.get('subjects', [])
        self.domains = additional.get('domains', [])
        self.taxonomies = additional.get('taxonomies', [])
        self.user_defined_tags = additional.get('user_defined_tags', [])
        self.countries = additional.get('countries', [])
        self.fairsharing_licence = additional.get('fairsharing_licence', [])
        self.legacy_ids = additional.get('legacy_ids', [])
        self.created_at = data[9]
        self.updated_at = data[10]


class RecordSet:

    LICENSE = 'https://creativecommons.org/licenses/by-sa/4.0/. '\
              'Please link to https://fairsharing.org and '\
              'https://fairsharing.org/static/img/home/svg/FAIRsharing-logo.svg '\
              'for attribution.'
    NOTE = 'Proxied for use in Data Stewardship Wizard '\
           '(see https://ds-wizard.org for more)'

    def __init__(self, records: list[Record]):
        self.records = records

    def to_json(self) -> dict:
        return {
            'data': [r.to_json() for r in self.records],
            'links': {
                'self': None,
                'first': None,
                'prev': None,
                'next': None,
                'last': None,
            },
            'note': self.NOTE,
        }

    def to_legacy_json(self) -> dict:
        return {
            'api_version': 'v0.3',
            'licence': self.LICENSE,
            'results': [r.to_legacy_json() for r in self.records],
            'note': self.NOTE,
        }