# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys
import site

# to use hglib, we need access to hg, which is in sys.prefix/bin
# in virtualenvs. Prefix our PATH with that.
# Similar to activate_this.py, too.
old_os_path = os.environ.get('PATH', '')
os.environ['PATH'] = os.path.join(sys.prefix, 'bin') + os.pathsep + old_os_path

wsgidir = os.path.dirname(__file__)
path = lambda *a: os.path.join(wsgidir, *a)
prev_sys_path = list(sys.path)

# the elmo root for importing manage
site.addsitedir(path('..'))

# Reorder sys.path so that the new directories are at the front.
#
# The goal of the following reordering is to give the modules in the root
# directory the highest priority, then global python packages.

# reorder sys.path so that the new directories are at the front
new_sys_path = []
for item in sys.path:
    if item not in prev_sys_path:
        new_sys_path.append(item)
        sys.path.remove(item)
sys.path[:0] = new_sys_path

# manage prepends /apps, /vendor and /vendor-local to sys.path on its own
import manage

os.environ['DJANGO_SETTINGS_MODULE'] = 'elmo.settings'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
