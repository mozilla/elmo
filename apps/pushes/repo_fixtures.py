# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Helpers to create custom repo setups for testing.
'''
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import shutil

import hglib


class api:
    '''Abstration of mercurial commands used to create fixtures etc'''

    @classmethod
    def init(cls, path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        os.mkdir(path)
        return hglib.init(path).open()

    @classmethod
    def file(cls, repo, path, contents):
        path = repo.pathto(path)
        open(path, 'w').write(contents)

    @classmethod
    def commit(cls, repo, message, user='Jane Doe'):
        repo.commit(user=user, message=message, addremove=True)
        return repo.log('.')[0].node

    @classmethod
    def update(cls, repo, rev):
        repo.update(rev=rev, clean=True)

    @classmethod
    def merge(cls, repo, rev1, rev2):
        repo.update(rev=rev1, clean=True)
        repo.merge(rev=rev2)


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
