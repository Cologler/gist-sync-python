# -*- coding: utf-8 -*-
#
# Copyright (c) 2019~2999 - Cologler <skyoflw@gmail.com>
# ----------
#
# ----------

import re

def find_gist_id(input_str: str) -> str:
    'try find a gist id from user input string.'

    m = re.match(r'https://gist.github.com/([^/]+)/(?P<gist_id>.+)', input_str, re.I)
    if m:
        return m['gist_id']
    return input_str

def get_gist_version(gist) -> str:
    'get latest gist version'

    return gist.history[0].version
