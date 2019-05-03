# -*- coding: utf-8 -*-
#
# Copyright (c) 2017~2999 - cologler <skyoflw@gmail.com>
# ----------
#
# ----------

import os

from click import get_current_context

from fsoopify import DirectoryInfo

from gistsync.consts import GIST_CONFIG_NAME
from gistsync.gist_ops import create_gist, pull_gist, push_gist, check_changed

class GistDir(DirectoryInfo):

    def __init__(self, *args):
        super().__init__(*args)
        self._gist_conf_file = self.get_fileinfo(GIST_CONFIG_NAME)
        self._gist_conf = None

    def get_abs_path(self):
        return os.path.abspath(self.path)

    def is_gist_dir(self):
        return self._gist_conf_file.is_file()

    def _load_gist_conf(self):
        if self._gist_conf is None:
            self._gist_conf = self._gist_conf_file.load()
        return self._gist_conf

    def push_new(self, context, public: bool):
        user = context.get_user()
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

        is_local_changed = check_changed(gist_conf, self)
        is_cloud_changed = gist.updated_at.isoformat(timespec='seconds') != gist_conf['updated_at']

        if is_cloud_changed and is_local_changed:
            logger.info('both local and remote all already changed.')
        elif is_local_changed:
            logger.info('detected local is updated.')
        elif is_cloud_changed:
            logger.info('detected remote is updated.')
        else:
            logger.info('nothing was changed since last sync.')

    def sync(self, context):
        gist_conf = self._load_gist_conf()
        gist_id = gist_conf['id']
        logger = context.get_logger(gist_id)
        gist = context.get_gist(gist_id)

        is_local_changed = check_changed(gist_conf, self)
        is_cloud_changed = gist.updated_at.isoformat(timespec='seconds') != gist_conf['updated_at']

        if is_cloud_changed and is_local_changed:
            logger.info('conflict: local gist and remote gist already changed.')
        elif is_local_changed:
            logger.info('detected local is updated, pushing...')
            push_gist(gist, self, logger)
        elif is_cloud_changed:
            logger.info('detected cloud is updated, pulling...')
            pull_gist(gist, self, logger)
        else:
            logger.info(f'{self.path.name}: nothing was changed since last sync.')
