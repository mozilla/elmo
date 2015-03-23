#!/usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys
import subprocess

# Constants

GIT_PULL = "git pull -q origin %(branch)s"
GIT_SUBMODULE = "git submodule update --init --recursive"

# Phases
class BasePhase(object):
    commandlist = []
    
    def __init__(self, verbose=False, environment=None):
        assert(environment is not None)
        self.verbose = verbose
        self.environment = environment
        self.basedir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..')
        )


    def execute(self):
        for cmd in self.commandlist:
            if self.verbose:
                sys.stdout.write("%s\n" % ' '.join(cmd))
            subprocess.check_call(cmd, shell=True, cwd=self.basedir)


class SourcePhase(BasePhase):
    ENV_BRANCH = {
        'dev': 'develop',
        'stage': 'master',
        'prod': 'master',
    }
    
    def __init__(self, environment=None, **kwargs):
        super(SourcePhase, self).__init__(environment=environment, **kwargs)
        project_branch = {'branch': self.ENV_BRANCH[environment]}
        self.commandlist += [
            [GIT_PULL % project_branch],
            [GIT_SUBMODULE]
        ]

class InstallPhase(BasePhase):
    VENDOR_DIR = './vendor'
    TMP_VENDOR_DIR = './vendor-tmp'
    # TODO: Add caching once peep starts supporting it.
    # See bug 1121459.
    PEEP_INSTALL_PROD = (
        "./vendor-local/lib/python/peep.py install "
        "-r requirements/compiled.txt "
        "-r requirements/prod.txt "
        "--target=%s" % TMP_VENDOR_DIR
    )
    PEEP_REPLACE_VENDOR = [
    ]
    PEEP_CLEANUP = "rm -rf %s" % TMP_VENDOR_DIR
    
    SOUTH_EXEC = "./manage.py migrate"
    STATICFILES_COLLECT_EXEC = "./manage.py collectstatic --noinput"
    GIT_REVISION = "git rev-parse HEAD > collected/static/revision"
    DJANGOCOMPRESSOR_COMPRESS_EXEC = "./manage.py compress"
    REFRESH_FEEDS_EXEC = "./manage.py refresh_feeds"
    def __init__(self, environment=None, **kwargs):
        super(InstallPhase, self).__init__(environment=environment, **kwargs)
        self.commandlist += [
            [self.PEEP_CLEANUP],
            [self.PEEP_INSTALL_PROD],
            ["rm -rf %s" % self.VENDOR_DIR],
            ["mv %s %s" % (self.TMP_VENDOR_DIR, self.VENDOR_DIR)]
        ]
    
        self.commandlist += [
            [self.SOUTH_EXEC],
        ]
    
        self.commandlist += [
            [self.STATICFILES_COLLECT_EXEC],
            [self.GIT_REVISION],
        ]
    
        self.commandlist += [
            [self.DJANGOCOMPRESSOR_COMPRESS_EXEC],
        ]
    
        self.commandlist += [
            [self.REFRESH_FEEDS_EXEC],
        ]
