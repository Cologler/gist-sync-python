# -*- coding: utf-8 -*-
#
# Copyright (c) 2017~2999 - cologler <skyoflw@gmail.com>
# ----------
#
# ----------

import os

from click import get_current_context
from fsoopify import DirectoryInfo, NodeType
from anyioc.g import get_namespace_provider

from .consts import GIST_CONFIG_NAME, IoCKeys
from .gist_ops import create_gist, pull_gist, push_gist, check_local_changed, check_changed, Changes

provider = get_namespace_provider()

class GistDir(DirectoryInfo):

    def __init__(self, *args):
        super().__init__(*args)
        self._gist_conf_file = self.get_fileinfo(GIST_CONFIG_NAME)
        self._gist_conf: dict = None

    def get_abs_path(self):
        return os.path.abspath(self.path)

    def is_gist_dir(self):
        return self._gist_conf_file.is_file()

    def _load_gist_conf(self):
        if self._gist_conf is None:
            self._gist_conf = self._gist_conf_file.load()
        return self._gist_conf

    def push_new(self, context, public: bool):
        user = provider[IoCKeys.GITHUB_CLIENT].get_user()
        logger = context.get_logger(None)
        create_gist(user, self, public, logger)

    def push(self, context):
        gist_conf = self._load_gist_conf()
        gist_id = gist_conf['id']
        logger = context.get_logger(gist_id)
        gist = context.get_gist(gist_id)

        push_gist(gist, self, logger)

    def init(self, context, gist_id):
        assert not self.is_gist_dir()

        logger = context.get_logger(gist_id)
        gist = context.get_gist(gist_id)

        pull_gist(gist, self, logger)

    def pull(self, context):
        assert self.is_gist_dir()

        gist_conf = self._load_gist_conf()
        gist_id = gist_conf['id']
        logger = context.get_logger(gist_id)
        gist = context.get_gist(gist_id)

        pull_gist(gist, self, logger)

    def check(self, context):
        gist_conf = self._load_gist_conf()
        gist_id = gist_conf['id']
        logger = context.get_logger(gist_id)
        gist = context.get_gist(gist_id)

        changes = check_changed(gist_conf, gist, self)

        if changes == Changes.both_changed:
            logger.info('both local and remote all already changed.')
        elif changes == Changes.local_changed:
            logger.info('detected local is updated.')
        elif changes == changes.cloud_changed:
            logger.info('detected remote is updated.')
        else:
            logger.info('nothing was changed since last sync.')

    def sync(self, context):
        gist_conf = self._load_gist_conf()
        gist_id = gist_conf['id']
        logger = context.get_logger(gist_id)
        gist = context.get_gist(gist_id)

        changes = check_changed(gist_conf, gist, self)

        if changes == Changes.both_changed:
            logger.info('conflict: local gist and remote gist already changed.')
        elif changes == Changes.local_changed:
            logger.info('detected local is updated, pushing...')
            push_gist(gist, self, logger)
        elif changes == changes.cloud_changed:
            logger.info('detected cloud is updated, pulling...')
            pull_gist(gist, self, logger)
        else:
            logger.info(f'{self.path.name}: nothing was changed since last sync.')

    def get_diff_files(self):
        ''' gets added and deleted file names as list. '''

        added = []
        deled = []
        files_in_disk = set(str(z.path.name) for z in self.list_gist_files())
        files_in_conf = set(z['name'] for z in self._gist_conf['files'])
        added = files_in_disk.difference(files_in_conf)
        deled = files_in_conf.difference(files_in_disk)
        return list(added), list(deled)

    def list_gist_files(self):
        ret = []
        for item in self.list_items():
            if item.node_type == NodeType.file:
                if item.path.name != GIST_CONFIG_NAME:
                    ret.append(item)
        return ret
