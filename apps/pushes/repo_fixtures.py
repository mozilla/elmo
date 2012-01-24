# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is l10n django site.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#  Axel Hecht <l10n@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

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
