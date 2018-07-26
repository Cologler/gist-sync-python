# -*- coding: utf-8 -*-
#
# Copyright (c) 2017~2999 - cologler <skyoflw@gmail.com>
# ----------
#
# ----------

import os
import tempfile

import requests
import github
from fsoopify import DirectoryInfo, FileInfo
from jasily.io.hash import Sha1Algorithm

from gistsync.consts import GIST_CONFIG_NAME

class ConfigBuilder:
    def __init__(self, gist=None):
        self.gist = gist
        self._files = []

    def get_updated_at(self):
        return self.gist.updated_at.isoformat(timespec='seconds')

    def dump(self, dir_info: DirectoryInfo):
        file_info = dir_info.get_fileinfo(GIST_CONFIG_NAME)
        file_info.dump({
            'id': self.gist.id,
            'updated_at': self.get_updated_at(),
            'files': self._files
        })

    def add_file(self, file_info: FileInfo):
        self._files.append({
            'name': file_info.path.name,
            'sha1': Sha1Algorithm().calc_file(file_info.path)
        })

def get_files(dir_info: DirectoryInfo, config_builder: ConfigBuilder, logger):
    update_content = {}
    for item in dir_info.list_items():
        if not isinstance(item, FileInfo):
            continue
        if item.path.name == GIST_CONFIG_NAME:
            continue
        if isinstance(item, FileInfo):
            update_content[item.path.name] = github.InputFileContent(item.read_text())
            config_builder.add_file(item)
    return update_content

def create_gist(user, dir_info: DirectoryInfo, public, logger):
    '''push items from dir to new gist.'''
    assert user and dir_info and logger

    config_builder = ConfigBuilder()
    files = get_files(dir_info, config_builder, logger)
    gist = user.create_gist(public, files=files)
    config_builder.gist = gist
    config_builder.dump(dir_info)
    logger.info(f'remote created at {config_builder.get_updated_at()}')

def pull_gist(gist, dir_info: DirectoryInfo, logger):
    '''pull items from gist to dir.'''
    assert gist and dir_info and logger

    with tempfile.TemporaryDirectory('-gistsync') as tempdir_name:
        tempdir_info = DirectoryInfo(tempdir_name)
        config_builder = ConfigBuilder(gist)

        for gist_file in gist.files.values():
            tempfile_info = tempdir_info.get_fileinfo(gist_file.filename)
            response = requests.get(gist_file.raw_url)
            try:
                tempfile_info.write_bytes(response.content)
                config_builder.add_file(tempfile_info)
            except OSError as err:
                # some filename only work on linux.
                logger.error(f'cannot sync gist: {err}')
                return
        config_builder.dump(tempdir_info)

        dir_info.ensure_created()
        for item in dir_info.list_items():
            item.delete()

        for item in tempdir_info.list_items():
            assert isinstance(item, FileInfo)
            file_info = dir_info.get_fileinfo(item.path.name)
            item.copy_to(file_info.path)

        logger.info(f'local updated from remote <{config_builder.get_updated_at()}>')

def push_gist(gist, dir_info: DirectoryInfo, logger):
    '''push items from dir to gist.'''
    assert gist and dir_info and logger

    config_builder = ConfigBuilder(gist)
    update_content = get_files(dir_info, config_builder, logger)
    gist.edit(files=update_content)
    config_builder.dump(dir_info)

    logger.info(f'remote updated at {config_builder.get_updated_at()}')

def check_changed(config: dict, dir_info: DirectoryInfo):
    '''
    check whether the gist dir is changed.
    return True if changed.
    '''
    config_files = config['files']

    files = [z for z in dir_info.list_items() if isinstance(z, FileInfo)] # only files
    if len(files) != len(config_files) + 1:
        # has one file named `.gist.json`
        return True

    for file in config_files:
        file_path = os.path.join(dir_info.path, file['name'])
        if not os.path.isfile(file_path):
            return True
        if Sha1Algorithm().calc_file(file_path) != file['sha1']:
            return True
