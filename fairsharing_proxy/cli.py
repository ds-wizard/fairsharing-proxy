import asyncio
import click

from fairsharing_proxy.cache import RecordsCache
from fairsharing_proxy.config import cfg_parser, ProxyConfig
from fairsharing_proxy.consts import ENV_CONFIG, DEFAULT_ENCODING, DEFAULT_CONFIG


@click.group()
@click.pass_context
@click.option('-c', '--config-file', default=DEFAULT_CONFIG,
              type=click.File(mode='r', encoding=DEFAULT_ENCODING),
              envvar=ENV_CONFIG, help='Configuration file.')
def cli(ctx, config_file):
    cfg = cfg_parser.parse_file(config_file)
    ctx.obj['cfg'] = cfg


@cli.command()
@click.pass_context
def cache_test(ctx):
    cfg = ctx.obj['cfg']  # type: ProxyConfig
    if not cfg.cache.enabled:
        click.echo('Caching is not enabled')
        exit(1)
    cache = RecordsCache(cfg)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(cache.load_records())
    cache.finalize()


def main():
    cli(obj={})
