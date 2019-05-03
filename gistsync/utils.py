# -*- coding: utf-8 -*-
#
# Copyright (c) 2019~2999 - Cologler <skyoflw@gmail.com>
# ----------
#
# ----------

def format_gist_updated_at(gist) -> str:
    '''
    format gist update_at as string.
    '''
    return gist.updated_at.isoformat(timespec='seconds')
