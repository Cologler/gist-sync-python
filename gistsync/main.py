# -*- coding: utf-8 -*-
#
# Copyright (c) 2017~2999 - cologler <skyoflw@gmail.com>
# ----------
#
# ----------

#pylint: disable=C0111,C0103

'''
Usage:
    gistsync setup token <token>
    gistsync init-all [--token=<token>]
    gistsync init <gist-id> [--token=<token>]
    gistsync sync [--token=<token>]
    gistsync push [--token=<token>]
    gistsync pull [--token=<token>]
    gistsync check [--token=<token>]
'''

import sys
import traceback
import logging

import docopt
import github
from fsoopify import DirectoryInfo

from gistsync.cmd import cmd, invoke
from gistsync.global_settings import GlobalSettings
from gistsync.gist_dir import GistDir

SETTINGS = GlobalSettings()

class OptionsProxy:
    def __init__(self, opt):
        self._data = opt

    @property
    def token(self):
        return self._data['<token>'] or self._data['--token']

    @property
    def gist_id(self):
        return self._data['<gist-id>']

    def __repr__(self):
        return repr(self._data)


class Context:
    def __init__(self, opt):
        self._opt = opt
        self._github_client = None
        self._gists = None

    @property
    def opt_proxy(self):
        return self._opt

    @property
    def token(self):
        '''get required token.'''
        tk = self._opt.token or SETTINGS.token
        if not tk:
            self.get_logger(None).error('need access token.')
            exit()
        return tk

    @property
    def github_client(self):
        if self._github_client is None:
            assert self.token
            self._github_client = github.Github(self.token)
        return self._github_client

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
            return logging.getLogger(f'gist-sync')
        else:
            return logging.getLogger(f'Gist({gist_id})')

@cmd('setup', 'token')
def register(context: Context):
    SETTINGS.token = context.opt_proxy.token

@cmd('init-all')
def init_all(context: Context):
    for gist in context.get_gists():
        gist_dir = GistDir(gist.id)
        gist_dir.pull(context)

@cmd('init')
def init(context: Context):
    gist_id = context.opt_proxy.gist_id
    logger = context.get_logger(None)

    def resolve(gist):
        logger.info(f'match {gist}')
        gist_dir = GistDir(gist.id)
        gist_dir.pull(context)

    gist = context.get_gist(gist_id)
    if gist is not None:
        return resolve(gist)

    for gist in context.get_gists():
        if gist_id in gist.id:
            return resolve(gist)

    logger.error('no match gists found.')

@cmd('sync')
def sync(context: Context):
    gist_dir = GistDir('.')
    if gist_dir.is_gist_dir():
        gist_dir.sync(context)
    else:
        for item in gist_dir.list_items():
            sub_gist_dir = GistDir(item.path)
            if sub_gist_dir.is_gist_dir():
                sub_gist_dir.sync(context)

@cmd('pull')
def pull(context: Context):
    gist_dir = GistDir('.')
    if gist_dir.is_gist_dir():
        gist_dir.pull(context)
    else:
        logger = context.get_logger(None)
        logger.error(f'{gist_dir.get_abs_path()} is not a gist dir.')

@cmd('push')
def push(context: Context):
    gist_dir = GistDir('.')
    if gist_dir.is_gist_dir():
        gist_dir.push(context)
    else:
        logger = context.get_logger(None)
        logger.error(f'{gist_dir.get_abs_path()} is not a gist dir.')

@cmd('check')
def check(context: Context):
    gist_dir = GistDir('.')
    if gist_dir.is_gist_dir():
        gist_dir.check(context)
    else:
        logger = context.get_logger(None)
        logger.error(f'{gist_dir.get_abs_path()} is not a gist dir.')


def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        logging.basicConfig(level=logging.INFO)
        opt = docopt.docopt(__doc__)
        opt_proxy = OptionsProxy(opt)
        context = Context(opt_proxy)
        assert invoke(opt, context)
    except Exception: # pylint: disable=W0703
        traceback.print_exc()

if __name__ == '__main__':
    main()
