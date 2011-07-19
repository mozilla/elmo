#!/usr/bin/env python
"""
Usage: licence_check.py [directory]
Finds all checked in files that suspiciously lack a MPL licensing header.

Options:
  -h, --help            show this help message and exit

(c) peterbe@mozilla.com, June 2011
"""

import subprocess
from collections import defaultdict


def check(filename):
    content = open(filename).read()
    if 'MPL 1.1' not in content:
        if content.strip():
            if len(content.splitlines()) > 1:
                return True


def search(dir):
    command = "git ls-files %s | grep -E '\.(js|css|py|html)$'" % dir
    out, err = subprocess.Popen(command, shell=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE
                                ).communicate()
    for filename in out.splitlines():
        if check(filename):
            yield filename


def main(*args):
    if '-h' in args or '--help' in args:
        print __doc__
        return 1
    groups = defaultdict(list)
    if not args:
        args = ('apps',)
    for arg in args:
        for filename in search(arg):
            groups[filename.split('.')[-1]].append(filename)

    print sum(len(x) for x in groups.values()), "suspicious files found"
    for ext in sorted(groups):
        print ext.upper()
        for name in groups[ext]:
            print name
        print

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main(*sys.argv[1:]))
