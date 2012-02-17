#!/usr/bin/env python
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

# Constants

ENV_BRANCH = {
    'dev': 'develop',
    'stage': 'master',
    'prod': 'master',
}

GIT_PULL = "git pull -q origin %(branch)s"
GIT_SUBMODULE = "git submodule update --init --recursive"
NASHVEGAS_LIST = "./manage.py upgradedb --path migrations --list"
NASHVEGAS_EXEC = "./manage.py upgradedb --path migrations --execute"
STATICFILES_COLLECT_EXEC = "./manage.py collectstatic --noinput"
DJANGOCOMPRESSOR_COMPRESS_EXEC = "./manage.py compress"
REFRESH_FEEDS_EXEC = "./manage.py refresh_feeds"

EXEC = 'exec'
CHDIR = 'chdir'
CONFIRM = 'confirm'


def update_site(env, debug):
    """Run through commands to update this site."""
    error_updating = False
    here = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    project_branch = {'branch': ENV_BRANCH[env]}

    commands = [
        (CHDIR, here),
        (EXEC,  GIT_PULL % project_branch),
        (EXEC,  GIT_SUBMODULE),
    ]

    commands += [
        (CHDIR, here),
        (CONFIRM, NASHVEGAS_LIST),
        (EXEC, NASHVEGAS_EXEC),
    ]

    commands += [
        (CHDIR, here),
        (EXEC, STATICFILES_COLLECT_EXEC),
    ]

    commands += [
        (CHDIR, here),
        (EXEC, DJANGOCOMPRESSOR_COMPRESS_EXEC),
    ]

    commands += [
        (CHDIR, here),
        (EXEC, REFRESH_FEEDS_EXEC),
    ]

    for cmd, cmd_args in commands:
        if CHDIR == cmd:
            if debug:
                sys.stdout.write("cd %s\n" % cmd_args)
            os.chdir(cmd_args)
        elif EXEC == cmd:
            if debug:
                sys.stdout.write("%s\n" % cmd_args)
            if not 0 == os.system(cmd_args):
                error_updating = True
                break
        elif CONFIRM == cmd:
            if debug:
                sys.stdout.write("%s\n" % cmd_args)
            if not 0 == os.system(cmd_args):
                error_updating = True
                break
            confirm = raw_input("Does the above look right? [yn] > ")
            if confirm not in ('y', 'yes'):
                sys.stdout.write("You aborted the update.  The lastexecuted "
                                 "command was:\n\t%s\n" % cmd_args)
                break
        else:
            raise Exception("Unknown type of command %s" % cmd)

    if error_updating:
        sys.stderr.write("There was an error while updating. Please try again "
                         "later. Aborting.\n")


def main():
    """ Handels command line args. """
    debug = False
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

    if opts.verbose:
        debug = True
    if opts.environment in ENV_BRANCH.keys():
        update_site(opts.environment, debug)
    else:
        sys.stderr.write("Invalid environment!\n")
        options.print_help(sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
