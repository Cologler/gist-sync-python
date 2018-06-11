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
'''

import sys
import traceback
import logging

import docopt
import github
from fsoopify import DirectoryInfo

from gistsync.cmd import cmd, invoke
from gistsync.global_settings import GlobalSettings
from gistsync.gist_ops import pull_gist, push_gist, check_changed

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

    def get_local_dir(self, gist):
        return DirectoryInfo(gist.id)

    def pull_gist(self, gist, dir_info: DirectoryInfo):
        assert gist and dir_info
        logger = self.get_logger(gist.id)
        pull_gist(gist, dir_info, logger)

    def push_gist(self, gist, dir_info: DirectoryInfo):
        logger = self.get_logger(gist.id)
        push_gist(gist, dir_info, logger)

    def sync_node(self, node_info):
        '''sync dir with cloud.'''

        if not isinstance(node_info, DirectoryInfo):
            return False

        config = node_info.get_fileinfo(GIST_CONFIG_NAME)
        if not config.is_file():
            return False

        gist_conf = config.load()
        gist_id = gist_conf['id']
        logger = self.get_logger(gist_id)
        gist = self.get_gist(gist_id)
        is_local_changed = check_changed(gist_conf, node_info)
        is_cloud_changed = gist.updated_at.isoformat(timespec='seconds') != gist_conf['updated_at']

        if is_cloud_changed and is_local_changed:
            logger.info('conflict: local gist and remote gist already changed.')
        elif is_local_changed:
            logger.info('detected local is updated, pushing...')
            self.push_gist(gist, node_info)
        elif is_cloud_changed:
            logger.info('detected cloud is updated, pulling...')
            self.pull_gist(gist, node_info)
        else:
            logger.info(f'{node_info.path.name}: nothing was changed since last sync.')

        return True

@cmd('setup', 'token')
def register(context: Context):
    SETTINGS.token = context.opt_proxy.token

@cmd('init-all')
def init_all(context: Context):
    for gist in context.get_gists():
        context.pull_gist(gist, context.get_local_dir(gist))

@cmd('init')
def init(context: Context):
    gist_id = context.opt_proxy.gist_id
    logger = context.get_logger(None)

    def on_found(gist):
        logger.info(f'match {gist}')
        context.pull_gist(gist, context.get_local_dir(gist))

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
    work_dir = DirectoryInfo('.')
    if context.sync_node(work_dir):
        return
    for item in work_dir.list_items():
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
