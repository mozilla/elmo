#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import

import os.path
import site
import sys


# Hook up elmo specific python locations.
# This used to be funfactory, but that's doing too much
prev_sys_path = list(sys.path)  # to reorder our stuff in front

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT)
site.addsitedir(os.path.join(ROOT, 'vendor'))
site.addsitedir(os.path.join(ROOT, 'vendor-local'))
site.addsitedir(os.path.join(ROOT, 'vendor-local', 'lib', 'python'))
site.addsitedir(os.path.join(ROOT, 'apps'))
sys.path[:] = ([_path for _path in sys.path if _path not in prev_sys_path] +
    prev_sys_path)

# settings still uses a bunch of funfactory, but assumes a different ROOT.
# help it fix that
import funfactory.manage
funfactory.manage.ROOT = ROOT

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elmo.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

