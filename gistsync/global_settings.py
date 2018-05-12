# -*- coding: utf-8 -*-
#
# Copyright (c) 2017~2999 - cologler <skyoflw@gmail.com>
# ----------
#
# ----------

import os
from pathlib import Path

from fsoopify import FileInfo

SYNC_CONFIG_NAME = '.gistsync.json'

class GlobalSettings:
    def __init__(self):
        home = str(Path.home())
        self._fileinfo = FileInfo(os.path.join(home, SYNC_CONFIG_NAME))
        self._data = self._fileinfo.load() if self._fileinfo.is_exists() else {}

    def _save(self):
        self._fileinfo.dump(self._data)

    @property
    def token(self):
        return self._data.get('token')

    @token.setter
    def token(self, value):
        self._data['token'] = value
        self._save()
