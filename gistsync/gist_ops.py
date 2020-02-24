# -*- coding: utf-8 -*-
#
# Copyright (c) 2017~2999 - cologler <skyoflw@gmail.com>
# ----------
#
# ----------

import os
import tempfile
import hashlib
from enum import IntEnum, auto

import requests
import github
from fsoopify import DirectoryInfo, FileInfo

from gistsync.consts import GIST_CONFIG_NAME
from .utils import format_gist_updated_at, get_gist_version

def hash_sha1(path) -> str:
    m = hashlib.sha1()
    with open(path, 'rb') as fp:
        while True:
            buf = fp.read(4096)
            if not buf:
                break
            m.update(buf)
    return m.hexdigest().upper()


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
            'files': self._files,
            'snapver': get_gist_version(self.gist)
        })

    def add_file(self, file_info: FileInfo):
        self._files.append({
            'name': file_info.path.name,
            'sha1': hash_sha1(file_info.path)
        })

def get_files(dir_info: DirectoryInfo, config_builder: ConfigBuilder, logger):
    '''get the files as a dict which use as argument for github api.'''

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

    type_ = 'public' if public else 'secret'
    logger.info(f'remote created {type_} at {format_gist_updated_at(gist)}')
    logger.info(f'gist id : {gist.id}')
    logger.info(f'gist url: https://gist.github.com/{gist.id}')

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

    added, deled = dir_info.get_diff_files()

    config_builder = ConfigBuilder(gist)
    update_content = get_files(dir_info, config_builder, logger)
    for name in deled:
        update_content[name] = None
    gist.edit(files=update_content)
    config_builder.dump(dir_info)

    logger.info(f'remote updated at {format_gist_updated_at(gist)}')
    if added:
        z = ', '.join(added)
        logger.info(f'remote added files: {z}')
    if deled:
        z = ', '.join(deled)
        logger.info(f'remote deled files: {z}')

class Changes(IntEnum):
    no_changes = auto()
    local_changed = auto()
    cloud_changed = auto()
    both_changed = auto()

def check_local_changed(config: dict, dir_info: DirectoryInfo):
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
        if hash_sha1(file_path) != file['sha1']:
            return True

def check_cloud_changed(gist_conf: dict, gist):
    '''
    check whether the gist cloud is changed.
    return True if changed.
    '''
    version = gist_conf.get('snapver')
    if version is not None:
        return version != get_gist_version(gist)
    # some old gist_conf did not contains snapver:
    return gist.updated_at.isoformat(timespec='seconds') != gist_conf['updated_at']

def check_changed(gist_conf: dict, gist, dir_info: DirectoryInfo) -> Changes:
    is_local_changed = check_local_changed(gist_conf, dir_info)
    is_cloud_changed = check_cloud_changed(gist_conf, gist)

    if is_cloud_changed and is_local_changed:
        return Changes.both_changed
    elif is_cloud_changed:
        return Changes.cloud_changed
    elif is_local_changed:
        return Changes.local_changed
    else:
        return Changes.no_changes
