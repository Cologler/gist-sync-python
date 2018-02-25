# -*- coding: utf-8 -*-
#
# Copyright (c) 2017~2999 - cologler <skyoflw@gmail.com>
# ----------
#
# ----------

'''
Usage:
   gistsync init-all [--token=<token>]
   gistsync init <gist-id> [--token=<token>]
   gistsync sync [--token=<token>]
'''

import os
import sys
import traceback
import tempfile
from abc import abstractmethod

import requests
import docopt
import github
import fsoopify
from fsoopify import DirectoryInfo, FileInfo
from jasily.io.hash import Sha1Algorithm

CONFIG_NAME = '.gist.json'

class ConfigBuilder:
    def __init__(self, gist):
        self._gist = gist
        self._files = []

    def dump(self, dir_info: DirectoryInfo):
        file_info = dir_info.get_fileinfo(CONFIG_NAME)
        file_info.dump({
            'id': self._gist.id,
            'updated_at': self._gist.updated_at.isoformat(timespec='seconds'),
            'files': self._files
        })

    def add_file(self, file_info: FileInfo):
        self._files.append({
            'name': file_info.path.name,
            'sha1': Sha1Algorithm().calc_file(file_info.path)
        })


class Task:
    def __init__(self):
        self.token = None
        self._github_client = None
        self._gists = None

    @abstractmethod
    def execute(self):
        raise NotImplementedError

    @property
    def github_client(self):
        if self._github_client is None:
            assert self.token
            self._github_client = github.Github(self.token)
        return self._github_client

    def _get_gists(self):
        if self._gists is None:
            self._gists = {}
            for gist in self.github_client.get_user().get_gists():
                self._gists[gist.id] = gist
        return list(self._gists.values())

    def _get_gist(self, gist_id, newest=False):
        if self._gists is None or newest:
            gist = self.github_client.get_gist(gist_id)
        if self._gists is not None and gist is not None:
            self._gists[gist.id] = gist
        return gist

    def _get_abs_path(self, rpath):
        return rpath

    def _ensure_dir(self, rpath):
        if not os.path.isdir(rpath):
            os.mkdir(rpath)

    def _save_config(self, gist, dir_info: DirectoryInfo):
        ConfigBuilder(gist).dump(dir_info)

    def _pull_gist(self, gist, dir_info: DirectoryInfo=None):
        with tempfile.TemporaryDirectory('-gistsync') as tempdir_name:
            tempdir_info = DirectoryInfo(tempdir_name)
            config_builder = ConfigBuilder(gist)

            for gist_file in gist.files.values():
                tempfile_info = tempdir_info.get_fileinfo(gist_file.filename)
                response = requests.get(gist_file.raw_url)
                try:
                    tempfile_info.write_bytes(response.content)
                except OSError as err:
                    # some filename only work on linux.
                    print(err)
                    print(f'cannot sync gist: {gist.id}')
                    return

            if dir_info is None:
                dir_info = DirectoryInfo(self._get_abs_path(gist.id))
            dir_info.ensure_created()
            for item in dir_info.list_items():
                item.delete()

            for item in tempdir_info.list_items():
                assert isinstance(item, fsoopify.FileInfo)
                file_info = dir_info.get_fileinfo(item.path.name)
                if file_info.is_file():
                    file_info.delete()
                item.copy_to(file_info.path)

            config_builder.dump(tempdir_info)

    def _push_gist(self, gist, dir_info: DirectoryInfo):
        config_builder = ConfigBuilder(gist)
        update_content = {}
        for item in dir_info.list_items():
            if item.path.name == CONFIG_NAME:
                continue
            if isinstance(item, FileInfo):
                update_content[item.path.name] = github.InputFileContent(item.read_text())
                config_builder.add_file(item)
        gist.edit(files=update_content)
        config_builder.dump(dir_info)

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

    def _sync_node(self, node_info):
        if isinstance(node_info, DirectoryInfo):
            config = node_info.get_fileinfo(CONFIG_NAME)
            if not config.is_file():
                return
            d = config.load()
            gist = self._get_gist(d['id'])
            if gist.updated_at.isoformat(timespec='seconds') == d['updated_at']:
                if self._is_changed(config, node_info):
                    return self._push_gist(gist, node_info)
                else:
                    print(f'{node_info.path.name}: nothing was changed after last sync.')
                    return
            else:
                return self._pull_gist(gist, node_info)


class SyncTask(Task):
    def execute(self):
        for item in DirectoryInfo('.').list_items():
            self._sync_node(item)


class InitTask(Task):
    def __init__(self, gist_id):
        super().__init__()
        self._gist_id = gist_id

    def execute(self):
        for gist in self._get_gists():
            if self._gist_id in gist.id:
                print(f'match {gist}')
                self._pull_gist(gist)


class InitAllTask(Task):
    def execute(self):
        for gist in self._get_gists():
            self._pull_gist(gist)


def create_task(opt):
    #print(opt)
    if opt['init-all']:
        task = InitAllTask()
    if opt['init']:
        task = InitTask(opt['<gist-id>'])
    if opt['sync']:
        task = SyncTask()
    task.token = opt['--token']
    return task

def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        opt = docopt.docopt(__doc__)
        task = create_task(opt)
        task.execute()
    except Exception: # pylint: disable=W0703
        traceback.print_exc()

if __name__ == '__main__':
    main()
