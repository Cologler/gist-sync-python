# -*- coding: utf-8 -*-
#
# Copyright (c) 2017~2999 - cologler <skyoflw@gmail.com>
# ----------
#
# ----------

#pylint: disable=C0111,C0103

'''
Usage:
   gistsync register <token>
   gistsync init-all [--token=<token>]
   gistsync init <gist-id> [--token=<token>]
   gistsync sync [--token=<token>]
'''

import os
import sys
import traceback
import logging

import docopt
import github
from fsoopify import DirectoryInfo, FileInfo
from jasily.io.hash import Sha1Algorithm

from gistsync.cmd import cmd, invoke
from gistsync.global_settings import GlobalSettings
from gistsync.gist_ops import pull_gist, push_gist

SETTINGS = GlobalSettings()

GIST_CONFIG_NAME = '.gist.json'

class OptionsProxy:
    def __init__(self, opt):
        self._data = opt

    @property
    def token(self):
        return self._data['<token>'] or self._data['--token']

    @property
    def gist_id(self):
        return self._data['<gist-id>']


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

    def _get_abs_path(self, rpath):
        return rpath

    def pull_gist(self, gist, dir_info: DirectoryInfo=None):
        if dir_info is None:
            dir_info = DirectoryInfo(self._get_abs_path(gist.id))
        logger = self.get_logger(gist.id)
        pull_gist(gist, dir_info, logger)

    def _push_gist(self, gist, dir_info: DirectoryInfo):
        logger = self.get_logger(gist.id)
        push_gist(gist, dir_info, logger)

    def _is_changed(self, config, dir_info: DirectoryInfo):
        config_files = config['files']
        if len(os.listdir(dir_info.path)) != len(config_files) + 1:
            return True
        for f in config_files:
            file_path = os.path.join(dir_info.path, f['name'])
            if not os.path.isfile(file_path):
                return True
            if Sha1Algorithm().calc_file(file_path) != f['sha1']:
                return True

    def sync_node(self, node_info):
        if isinstance(node_info, DirectoryInfo):
            config = node_info.get_fileinfo(GIST_CONFIG_NAME)
            if not config.is_file():
                return
            d = config.load()
            gist_id = d['id']
            logger = self.get_logger(gist_id)
            gist = self.get_gist(gist_id)
            is_changed = self._is_changed(d, node_info)
            if gist.updated_at.isoformat(timespec='seconds') == d['updated_at']:
                if is_changed:
                    return self._push_gist(gist, node_info)
                else:
                    logger.info(f'{node_info.path.name}: nothing was changed since last sync.')
                    return
            elif is_changed:
                logger.info('conflict: local gist and remote gist already changed.')
                return
            else:
                return self.pull_gist(gist, node_info)

@cmd('register')
def register(context: Context):
    SETTINGS.token = context.opt_proxy.token

@cmd('init-all')
def init_all(context: Context):
    for gist in context.get_gists():
        context.pull_gist(gist)

@cmd('init')
def init(context: Context):
    gist_id = context.opt_proxy.gist_id
    logger = context.get_logger(None)

    def on_found(gist):
        logger.info(f'match {gist}')
        context.pull_gist(gist)

    gist = context.get_gist(gist_id)
    if gist is not None:
        on_found(gist)
        return

    found = False
    for gist in context.get_gists():
        if gist_id in gist.id:
            on_found(gist)
            found = True
    if not found:
        logger.error('no match gists found.')

@cmd('sync')
def sync(context: Context):
    for item in DirectoryInfo('.').list_items():
        context.sync_node(item)

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
