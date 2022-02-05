import datetime
import httpx
import sqlite3

from fairsharing_proxy.api_client import FAIRSharingClient
from fairsharing_proxy.config import ProxyConfig
from fairsharing_proxy.logger import LOG
from fairsharing_proxy.model import Record


_QUERY_CREATE_TABLE_RECORDS = '''
    CREATE TABLE IF NOT EXISTS records (
      fairsharing_id TEXT,
      registry       TEXT,
      record_type    TEXT,
      record_name    TEXT,
      description    TEXT,
      abbreviation   TEXT,
      doi            TEXT,
      url            TEXT,
      additional     TEXT,
      created_at     TEXT,
      updated_at     TEXT
    );
'''


_QUERY_CREATE_TABLE_META = '''
    CREATE TABLE IF NOT EXISTS meta (
      version       INTEGER,
      created_at    TEXT
    );
'''

_QUERY_CREATE_TABLE_RUNS = '''
    CREATE TABLE IF NOT EXISTS runs (
      created_at    TEXT,
      started_at    TEXT,
      finished_at   TEXT,
      records       INTEGER,
      message       TEXT
    );
'''


class RecordsCache:

    CURRENT_META = 1

    def __init__(self, cfg: ProxyConfig):
        self.config = cfg
        self.records = []  # type: list[Record]
        self.connection = sqlite3.connect(
            database=self.config.cache.filename,
        )

    def prepare(self):
        # TODO: check content, clear if needed
        ...

    def finalize(self):
        self.connection.close()
        self.connection = None

    def _init_tables(self):
        cur = self.connection.cursor()
        cur.execute(_QUERY_CREATE_TABLE_META)
        cur.execute(_QUERY_CREATE_TABLE_RUNS)
        cur.execute(_QUERY_CREATE_TABLE_RECORDS)
        now = datetime.datetime.utcnow()
        cur.execute('''
            INSERT INTO meta VALUES (?, ?);
        ''', (self.CURRENT_META, now.isoformat()))
        cur.close()
        self.connection.commit()

    async def load_records(self):
        start_time = datetime.datetime.utcnow()
        LOG.info('[CACHE] Caching started')
        api_client = FAIRSharingClient(self.config)
        async with httpx.AsyncClient() as client:
            LOG.debug('[CACHE] Login in progress')
            token = await api_client.client_login(
                client=client,
                username=self.config.cache.username,
                password=self.config.cache.password,
            )
            if not token.ok:
                LOG.error('[CACHE] Login failed')
            LOG.debug('[CACHE] Login OK')
            LOG.debug('[CACHE] Requesting all records')
            self.records = await api_client.client_list_records_all(
                client=client,
                token=token,
                page_size=self.config.cache.page_size,
                page_delay=self.config.cache.page_delay,
                timeout=self.config.cache.page_timeout,
            )
        finish_time = datetime.datetime.utcnow()
        LOG.info(f'[CACHE] Fetched {len(self.records)} records')
        LOG.info(f'[CACHE] - Start = {start_time}')
        LOG.info(f'[CACHE] - Finish = {finish_time}')
        LOG.info(f'[CACHE] - Elapsed = {finish_time - start_time}')
        cur = self.connection.cursor()
        for record in self.records:
            cur.execute('''
                INSERT INTO records
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            ''', record.to_row())
        now = datetime.datetime.utcnow()
        cur.execute('''
            INSERT INTO runs VALUES (?, ?, ?, ?, ?);
        ''', (
            now.isoformat(),
            start_time.isoformat(),
            finish_time.isoformat(),
            len(self.records),
            'Seems like all is OK',
        ))
        cur.close()
        self.connection.commit()
        LOG.info('[CACHE] Caching done')

        def query_records(query: str) -> list[Record]:
            # TODO fts?
            ...
