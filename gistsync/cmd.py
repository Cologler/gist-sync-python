# -*- coding: utf-8 -*-
#
# Copyright (c) 2017~2999 - cologler <skyoflw@gmail.com>
# ----------
#
# ----------

CMDMAP = {}

def cmd(*tokens):
    def _(cb):
        CMDMAP[tokens] = cb
        return cb
    return _

def invoke(opt, *args):
    for tokens in CMDMAP:
        assert isinstance(tokens, tuple)
        if all(opt[val] for val in tokens):
            CMDMAP[tokens](*args)
            return True
    return False
