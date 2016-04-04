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
import sys
from textwrap import dedent
from optparse import  OptionParser
import update_commands


def update_site(verbose, vendor):
    """Run through commands to update this site."""
    # do source first
    cmds = update_commands.SourcePhase(
        verbose=verbose
    )
    cmds.execute()
    # do install, update the commands module first
    reload(update_commands)
    cmds = update_commands.InstallPhase(
        verbose=verbose,
        vendor=vendor
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
    options.add_option("--vendor",
                       help="Install into vendor instead of virtualenv",
                       action="store_true", dest="vendor")
    (opts, _) = options.parse_args()
    if not opts.vendor:
        # ensure we're in a virtualenv
        if not hasattr(sys, 'real_prefix'):
            options.error('Activate a virtualenv to install.')

    update_site(opts.verbose, opts.vendor)


if __name__ == '__main__':
    main()
