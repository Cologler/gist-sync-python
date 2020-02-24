# -*- coding: utf-8 -*-
#
# Copyright (c) 2020~2999 - Cologler <skyoflw@gmail.com>
# ----------
#
# ----------

def test_find_gist_id():
    from gistsync.utils import find_gist_id
    assert '8b5d44890d95c58ab41b0fb85cb05dce' == find_gist_id('8b5d44890d95c58ab41b0fb85cb05dce')
    assert '8b5d44890d95c58ab41b0fb85cb05dce' == find_gist_id('https://gist.github.com/Cologler/8b5d44890d95c58ab41b0fb85cb05dce')
