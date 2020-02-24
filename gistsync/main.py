# -*- coding: utf-8 -*-
#
# Copyright (c) 2017~2999 - cologler <skyoflw@gmail.com>
# ----------
#
# ----------

#pylint: disable=C0111,C0103

import sys
import traceback
import logging
import enum

import github
import click
from click_anno import click_app
from click_anno.types import flag
from anyioc.g import get_namespace_provider

from .global_settings import GlobalSettings
from .gist_dir import GistDir
from .consts import IoCKeys
from .utils import find_gist_id

provider = get_namespace_provider()

provider.register_singleton(IoCKeys.GLOBAL_SETTINGS, GlobalSettings)


SETTINGS = GlobalSettings()

logging.basicConfig()
logger = logging.getLogger(f'gist-sync')

@provider.builder.transient(IoCKeys.TOKEN)
def _get_token(ioc):
    token = ioc.get(IoCKeys.ARGS_TOKEN) or ioc[IoCKeys.GLOBAL_SETTINGS].token
    if not token:
        return click.get_current_context().fail(
            'need access token.'
        )
    return token

@provider.builder.singleton(IoCKeys.GITHUB_CLIENT)
def _get_github_client(ioc):
    token = ioc[IoCKeys.TOKEN]
    assert token
    return github.Github(token)


class Context:
    def __init__(self):
        self._github_client = None
        self._gists = None

    def get_gist_dir(self, gist_dir: str):
        return GistDir(gist_dir or '.')

    @property
    def github_client(self) -> github.Github:
        return provider[IoCKeys.GITHUB_CLIENT]

    def get_gists(self):
        return self.github_client.get_user().get_gists()

    def get_gist(self, gist_id, newest=False):
        try:
            return self.github_client.get_gist(gist_id)
        except github.UnknownObjectException:
            return None

    def get_logger(self, gist_id):
        if gist_id is None:
            return logger
        else:
            return logger.getChild(f'Gist({gist_id})')


class Props(enum.IntEnum):
    token = enum.auto()

@click_app
class App:
    def _get_context(self, token):
        return Context()

    def setup(self, name: Props, value):
        'setup name value pair'
        if name == Props.token:
            SETTINGS.token = value

    def init_all(self, token=None):
        'init all gists in current directory'
        context = Context()
        provider.register_value(IoCKeys.ARGS_TOKEN, token)

        for gist in context.get_gists():
            gist_dir = GistDir(gist.id)
            gist_dir.pull(context)

    def init(self, ctx: click.Context, gist_id, token=None, name=None):
        'init the gist in current directory'
        context = Context()
        provider.register_value(IoCKeys.ARGS_TOKEN, token)

        gist_id = find_gist_id(gist_id)

        def try_match(gist):
            if gist_id in gist.id:
                logger.info(f'id of {gist} contains "{gist_id}".')
                return True
            if gist_id in gist.files:
                logger.info(f'{gist} contains file "{gist_id}".')
                return True

        def find_single():
            gist = context.get_gist(gist_id)
            if gist is not None:
                return gist
            else:
                logger.info(f'"https://gist.github.com/{gist_id}" does not exists, try find from keywords...')

            gists = [g for g in context.get_gists() if try_match(g)]
            if len(gists) == 1:
                return gists[0]

            if gists:
                ctx.fail('match too many gists: \n{}'.format(
                    '\n'.join(g.id for g in gists)
                ))
            else:
                ctx.fail('no match gists found.')

        gist = find_single()
        logger.info(f'matched {gist}')
        gist_dir = GistDir(name or gist.id)
        gist_dir.init(context, gist.id)

    def sync(self, gist_dir=None, token=None):
        'sync current directory as a gist'
        context = Context()
        provider.register_value(IoCKeys.ARGS_TOKEN, token)

        gist_dir = context.get_gist_dir(gist_dir)
        if gist_dir.is_gist_dir():
            gist_dir.sync(context)
        else:
            for item in gist_dir.list_items():
                sub_gist_dir = GistDir(item.path)
                if sub_gist_dir.is_gist_dir():
                    sub_gist_dir.sync(context)

    def pull(self, ctx: click.Context, gist_dir=None, token=None):
        'pull gist from cloud to local (which must be initialized first).'
        context = Context()
        provider.register_value(IoCKeys.ARGS_TOKEN, token)

        gist_dir = context.get_gist_dir(gist_dir)
        if gist_dir.is_gist_dir():
            gist_dir.pull(context)
        else:
            ctx.fail('{path} is not a gist dir.'.format(
                path=click.style(str(gist_dir.path), fg='green')
            ))

    def push(self, ctx: click.Context, gist_dir=None, public: flag=False, token=None):
        'push current directory as a gist'
        context = Context()
        provider.register_value(IoCKeys.ARGS_TOKEN, token)

        gist_dir = context.get_gist_dir(gist_dir)
        if gist_dir.is_gist_dir():
            gist_dir.push(context)
        else:
            gist_dir.push_new(context, public)

    def check(self, ctx: click.Context, gist_dir=None, token=None):
        'check the status of current directory'
        context = Context()
        provider.register_value(IoCKeys.ARGS_TOKEN, token)

        gist_dir = context.get_gist_dir(gist_dir)
        if gist_dir.is_gist_dir():
            gist_dir.check(context)
        else:
            ctx.fail('{path} is not a gist dir.'.format(
                path=click.style(str(gist_dir.path), fg='green')
            ))


def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        logger.setLevel(level=logging.INFO)
        App()
    except Exception: # pylint: disable=W0703
        traceback.print_exc()

if __name__ == '__main__':
    main()
