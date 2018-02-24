# -*- coding: utf-8 -*-
#
# Copyright (c) 2017~2999 - cologler <skyoflw@gmail.com>
# ----------
#
# ----------

'''
Usage:
   gistsync sync-all [--token=<token>]
   gistsync sync <gist-id> [--token=<token>]
'''

import os
import sys
import traceback
import tempfile

import requests
import docopt
import github
import fsoopify

class Task:
    def __init__(self):
        self.token = None
        self._github_client = None

    @property
    def github_client(self):
        if self._github_client is None:
            assert self.token
            self._github_client = github.Github(self.token)
        return self._github_client

    def _get_abs_path(self, rpath):
        return rpath

    def _ensure_dir(self, rpath):
        if not os.path.isdir(rpath):
            os.mkdir(rpath)


class SyncTask(Task):

    def _download_gist(self, gist):
        dir_info = fsoopify.DirectoryInfo(self._get_abs_path(gist.id))
        dir_info.ensure_created()

        with tempfile.TemporaryDirectory('-gistsync') as tempdir_name:
            tempdir_info = fsoopify.DirectoryInfo(tempdir_name)

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

            for item in tempdir_info.list_items():
                assert isinstance(item, fsoopify.FileInfo)
                item.copy_to(dir_info.get_fileinfo(item.path.name).path)



class SyncSingleTask(SyncTask):
    def __init__(self, gist_id):
        super().__init__()
        self._gist_id = gist_id


class SyncAllTask(SyncTask):
    def execute(self):
        for gist in self.github_client.get_user().get_gists():
            self._download_gist(gist)


def create_task(opt):
    #print(opt)
    if opt['sync-all']:
        task = SyncAllTask()
    if opt['sync']:
        task = SyncSingleTask(opt['<gist-id>'])
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
