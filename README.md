# gist-sync-python

[![Build Status](https://travis-ci.com/Cologler/gist-sync-python.svg?branch=master)](https://travis-ci.com/Cologler/gist-sync-python)

Just sync gists with cli!

## HOW-TO-WORK

1. Create a token from Github.
1. When you call `init` command, `gist-sync` will make dirs for each gist.
1. Edit gists as you need.
1. Call `sync` command, all changed will update to the cloud.

You can change the dir name, but **DO NOT** edit `.gist.json` which in dir.

## HOW-TO-USE

``` txt
Usage:
    gistsync setup token <token>
    gistsync init-all [--token=<token>]
    gistsync init <gist-id> [--token=<token>]
    gistsync sync [--token=<token>]
    gistsync push [--token=<token>]
    gistsync pull [--token=<token>]
    gistsync check [--token=<token>]
```

init gist, edit it, and sync!

*You can register token to avoid input it again over again.*

## INSTALL

from pypi.

``` py
pip install gistsync
```

😀
