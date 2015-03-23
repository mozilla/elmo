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
  -e ENVIRONMENT, --environment=ENVIRONMENT
                        Type of environment. One of (prod|dev|stage) Example:
                        update_site.py -e stage
  -v, --verbose         Echo actions before taking them.
"""

import os
import sys
from textwrap import dedent
from optparse import  OptionParser
import update_commands


ENV_BRANCH = update_commands.SourcePhase.ENV_BRANCH


def update_site(env, verbose):
    """Run through commands to update this site."""
    # do source first
    cmds = update_commands.SourcePhase(
        environment=env,
        verbose=verbose
    )
    cmds.execute()
    # do install, update the commands module first
    reload(update_commands)
    cmds = update_commands.InstallPhase(
        environment=env,
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
    e_help = "Type of environment. One of (%s) Example: update_site.py \
        -e stage" % '|'.join(ENV_BRANCH.keys())
    options.add_option("-e", "--environment", help=e_help)
    options.add_option("-v", "--verbose",
                       help="Echo actions before taking them.",
                       action="store_true", dest="verbose")
    (opts, _) = options.parse_args()

    if opts.environment in ENV_BRANCH.keys():
        update_site(opts.environment, opts.verbose)
    else:
        sys.stderr.write("Invalid environment!\n")
        options.print_help(sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
