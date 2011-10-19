#!/usr/bin/env python
import os
import site
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
path = lambda *a: os.path.join(ROOT,*a)


# Adjust the python path and put local packages in front.
prev_sys_path = list(sys.path)

site.addsitedir(path('apps'))
site.addsitedir(path('lib'))

# Local (project) vendor library
site.addsitedir(path('vendor-local'))
site.addsitedir(path('vendor-local/lib/python'))

# Global (upstream) vendor library
site.addsitedir(path('vendor'))
site.addsitedir(path('vendor/lib/python'))


# Move the new items to the front of sys.path. (via virtualenv)
new_sys_path = []
for item in list(sys.path):
    if item not in prev_sys_path:
        new_sys_path.append(item)
        sys.path.remove(item)
sys.path[:0] = new_sys_path

from django.core.management import execute_manager
import settings

if __name__ == "__main__":
    execute_manager(settings)
