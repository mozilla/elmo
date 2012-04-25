# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Helpers to create custom repo setups for testing.
'''

import os
import shutil
import sys

from mercurial import commands as hgcommands
from mercurial.hg import repository
from mercurial.ui import ui as hg_ui


class api:
    '''Abstration of mercurial commands used to create fixtures etc'''
    class _ui(hg_ui):
        def write(self, *msg, **opts):
            pass

    @classmethod
    def init(cls, path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        os.mkdir(path)
        ui = cls._ui()
        hgcommands.init(ui, path)
        return repository(ui, path)

    @classmethod
    def file(cls, repo, path, contents):
        p = repo.pathto(path)
        open(p, 'w').write(contents)
        if repo.dirstate[path] not in 'amn':
            hgcommands.add(repo.ui, repo, 'path:' + path)

    @classmethod
    def commit(cls, repo, message, user='Jane Doe'):
        hgcommands.commit(repo.ui, repo, user=user, message=message)
        return repo['tip'].hex()

    @classmethod
    def update(cls, repo, rev):
        hgcommands.update(repo.ui, repo, rev=rev, clean=True)

    @classmethod
    def merge(cls, repo, rev1, rev2):
        hgcommands.update(repo.ui, repo, rev=rev1, clean=True)
        hgcommands.merge(repo.ui, repo, rev=rev2)


def network(base):
    '''Set up repos that are good to do network tests on.
    '''
    one = os.path.join(base, 'one')
    one_repo = api.init(one)
    api.file(one_repo, 'file.txt', 'first\n')
    fork1 = api.commit(one_repo, 'first commit')
    api.file(one_repo, 'file.txt', 'first\nsecond\n')
    mergeparent1 = api.commit(one_repo, 'second commit')
    api.update(one_repo, fork1)
    api.file(one_repo, 'other.txt', 'fork one\n')
    mergeparent2 = fork2 = api.commit(one_repo, 'forking the repo')
    api.merge(one_repo, mergeparent1, mergeparent2)
    head1 = api.commit(one_repo, 'merging the fork')
    api.update(one_repo, fork2)
    api.file(one_repo, 'other.txt', 'fork one\nand two\n')
    head2 = api.commit(one_repo, 'adding a second fork')
    return {
        'repos': {'one': one_repo},
        'heads': [head1, head2],
        'forks': [fork1, fork2]
    }


if __name__ == '__main__':
    b = sys.argv[1]
    network(b)
