#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Usage: update_site.py [options]
Updates a server's sources, vendor libraries, packages CSS/JS
assets, migrates the database, and other nifty deployment tasks.

Options:
  -h, --help            show this help message and exit
  -v, --verbose         Echo actions before taking them.
"""

import os
import subprocess
import sys
from textwrap import dedent
from optparse import  OptionParser


def update_site(verbose):
    """Run through commands to update this site."""
    basedir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..')
    )
    # do source first
    # fetch first,
    # check for deleted python files,
    # delete their pyc
    # then merge.
    # Thus, we'll remove left-over .pyc and remove module dirs
    if verbose:
        sys.stdout.write("git fetch\n")
    subprocess.check_call(['git', 'fetch'], cwd=basedir)
    logoutput = subprocess.check_output(
        ['git', 'log', '--name-only', '--diff-filter=D', 'HEAD..FETCH_HEAD'],
        cwd=basedir)
    deleted = logoutput.split()
    pydel = [f + 'c' for f in deleted if f.endswith('.py')]
    if verbose and pydel:
        sys.stdout.write("rm %s\n" % ' '.join(pydel))
    for f in pydel:
        try:
            os.remove(os.path.join(basedir, f))
        except OSError:
            pass  # if the file doesn't exist, that's OK
    if verbose:
        sys.stdout.write("git merge --ff-only\n")
    subprocess.check_call(
        ['git', 'merge', '--ff-only', 'FETCH_HEAD'], cwd=basedir)
    if verbose:
        sys.stdout.write("git submodule update --init --recursive\n")
    subprocess.check_call(
        ['git', 'submodule', 'update', '--init', '--recursive'], cwd=basedir)
    # do install, update the commands module first
    import update_commands
    cmds = update_commands.InstallPhase(
        verbose=verbose
    )
    cmds.execute()


def main():
    """ Handles command line args. """
    usage = dedent("""\
        %prog [options]
        Updates a server's sources, vendor libraries, packages CSS/JS
        assets, migrates the database, and other nifty deployment tasks.
        """.rstrip())

    options = OptionParser(usage=usage)
    options.add_option("-v", "--verbose",
                       help="Echo actions before taking them.",
                       action="store_true", dest="verbose")
    (opts, _) = options.parse_args()
    # ensure we're in a virtualenv
    if not hasattr(sys, 'real_prefix'):
        options.error('Activate a virtualenv to install.')

    update_site(opts.verbose)


if __name__ == '__main__':
    main()
