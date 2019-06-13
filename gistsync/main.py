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

provider = get_namespace_provider()

provider.register_singleton(IoCKeys.GLOBAL_SETTINGS, GlobalSettings)


SETTINGS = GlobalSettings()

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
        if self._gists is None:
            self._gists = {}
            for gist in self.github_client.get_user().get_gists():
                self._gists[gist.id] = gist
        return list(self._gists.values())

    def get_gist(self, gist_id, newest=False):
        if self._gists is None or newest:
            try:
                gist = self.github_client.get_gist(gist_id)
            except github.UnknownObjectException:
                return None
        if self._gists is not None and gist is not None:
            self._gists[gist.id] = gist

        return gist

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
        if name == Props.token:
            SETTINGS.token = value

    def init_all(self, token=None):
        context = Context()
        provider.register_value(IoCKeys.ARGS_TOKEN, token)

        for gist in context.get_gists():
            gist_dir = GistDir(gist.id)
            gist_dir.pull(context)

    def init(self, ctx: click.Context, gist_id, token=None, name=None):
        context = Context()
        provider.register_value(IoCKeys.ARGS_TOKEN, token)

        def find_single():
            gist = context.get_gist(gist_id)
            if gist is not None:
                return gist
            gists = [g for g in context.get_gists() if gist_id in g.id]
            if len(gists) == 1:
                return gists[0]
            if gists:
                ctx.fail('match too many gists: \n{}'.format(
                    '\n'.join(g.id for g in gists)
                ))
            else:
                ctx.fail('no match gists found.')

        def resolve(gist):
            logger.info(f'match {gist}')
            gist_dir = GistDir(gist.id)
            gist_dir.init(context, gist.id)

        gist = find_single()
        click.echo(f'match {gist}')
        gist_dir = GistDir(gist.id)
        gist_dir.init(context, gist.id)

    def sync(self, gist_dir=None, token=None):
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
        context = Context()
        provider.register_value(IoCKeys.ARGS_TOKEN, token)

        gist_dir = context.get_gist_dir(gist_dir)
        if gist_dir.is_gist_dir():
            gist_dir.push(context)
        else:
            gist_dir.push_new(context, public)

    def check(self, ctx: click.Context, gist_dir=None, token=None):
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
