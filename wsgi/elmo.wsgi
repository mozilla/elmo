# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is l10n django site.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Stas Malolepszy <stas@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

import os
import sys
import site

wsgidir = os.path.dirname(__file__)
path = lambda *a: os.path.join(wsgidir, *a)
prev_sys_path = list(sys.path)

# the elmo root for importing manage
site.addsitedir(path('..'))
# the parent dir of elmo root, needed to import elmo.urls
site.addsitedir(path('..', '..'))

# Reorder sys.path so that the new directories are at the front.
#
# The goal of the following reordering is to give the modules in the root
# directory the highest priority, then virtualenv, then global python packages.
# Since we're prepending to sys.path, we start with virtualenv, then project's
# root.

# 1. Add virtualenv to sys.path
# =============================

# the packages installed in the virtualenv
site.addsitedir(path('..', 'env', 'lib', 'python' + sys.version[:3],
                     'site-packages'))

# reorder sys.path so that the new directories are at the front
new_sys_path = []
for item in sys.path:
    if item not in prev_sys_path:
        new_sys_path.append(item)
        sys.path.remove(item)
sys.path[:0] = new_sys_path

# 2. Add project's root to sys.path
# =================================

# manage prepends /apps, /lib, and /vendor to sys.path on its own
import manage


import django.core.handlers.wsgi
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
application = django.core.handlers.wsgi.WSGIHandler()
