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
from click_anno import click_app
from click_anno.types import flag

from gistsync.cmd import cmd, invoke
from gistsync.global_settings import GlobalSettings
from gistsync.gist_dir import GistDir

SETTINGS = GlobalSettings()

logger = logging.getLogger(f'gist-sync')


class Context:
    def __init__(self):
        self._github_client = None
        self._gists = None
        self._token = None

    def get_gist_dir(self, gist_dir: str):
        return GistDir(gist_dir or '.')

    @property
    def token(self):
        '''get required token.'''
        token = self._token or SETTINGS.token
        if not token:
            self.get_logger(None).error('need access token.')
            exit()
        return token

    @token.setter
    def token(self, value):
        self._token = value

    @property
    def github_client(self):
        if self._github_client is None:
            assert self.token
            self._github_client = github.Github(self.token)
        return self._github_client

    def get_user(self):
        return self.github_client.get_user()

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
        context.token = token

        for gist in context.get_gists():
            gist_dir = GistDir(gist.id)
            gist_dir.pull(context)

    def init(self, gist_id, token=None, name=None):
        context = Context()
        context.token = token

        logger = context.get_logger(None)

        def resolve(gist):
            logger.info(f'match {gist}')
            gist_dir = GistDir(gist.id)
            gist_dir.init(context, gist.id)

        gist = context.get_gist(gist_id)
        if gist is not None:
            return resolve(gist)

        for gist in context.get_gists():
            if gist_id in gist.id:
                return resolve(gist)

        logger.error('no match gists found.')

    def sync(self, gist_dir=None, token=None):
        context = Context()
        context.token = token

        gist_dir = context.get_gist_dir(gist_dir)
        if gist_dir.is_gist_dir():
            gist_dir.sync(context)
        else:
            for item in gist_dir.list_items():
                sub_gist_dir = GistDir(item.path)
                if sub_gist_dir.is_gist_dir():
                    sub_gist_dir.sync(context)

    def pull(self, gist_dir=None, token=None):
        context = Context()
        context.token = token

        gist_dir = context.get_gist_dir(gist_dir)
        if gist_dir.is_gist_dir():
            gist_dir.pull(context)
        else:
            logger = context.get_logger(None)
            logger.error(f'<{gist_dir.get_abs_path()}> is not a gist dir.')

    def push(self, gist_dir=None, public: flag=False, token=None):
        context = Context()
        context.token = token

        gist_dir = context.get_gist_dir(gist_dir)
        if gist_dir.is_gist_dir():
            gist_dir.push(context)
        else:
            gist_dir.push_new(context)

    def check(self, gist_dir=None, token=None):
        context = Context()
        context.token = token

        gist_dir = context.get_gist_dir(gist_dir)
        if gist_dir.is_gist_dir():
            gist_dir.check(context)
        else:
            logger = context.get_logger(None)
            logger.error(f'<{gist_dir.get_abs_path()}> is not a gist dir.')


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
