
gist-sync-python
================

Just sync gists with cli!

HOW-TO-WORK
-----------


#. Create a token from Github.
#. When you call ``init`` command, ``gist-sync`` will make dirs for each gist.
#. Edit gists as you need.
#. Call ``sync`` command, all changed will update to the cloud.

You can change the dir name, but **DO NOT** edit ``.gist.json`` which in dir.

HOW-TO-USE
----------

.. code-block:: txt

   Usage:
      gistsync register <token>
      gistsync init-all [--token=<token>]
      gistsync init <gist-id> [--token=<token>]
      gistsync sync [--token=<token>]

init gist, edit it, and sync!

*You can register token to avoid input it again over again.*

INSTALL
-------

from pypi.

.. code-block:: py

   pip install gist-sync

😀
