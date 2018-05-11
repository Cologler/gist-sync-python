# -*- coding: utf-8 -*-
#
# Copyright (c) 2017~2999 - cologler <skyoflw@gmail.com>
# ----------
#
# ----------

CMDMAP = {}

def cmd(name):
    def _(cb):
        CMDMAP[name] = cb
        return cb
    return _

def invoke(opt, *args):
    for name in CMDMAP:
        if opt[name]:
            CMDMAP[name](*args)
            return True
    return False
