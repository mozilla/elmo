#!/usr/bin/env python
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
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
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

'''Helper script to push to the buildbotcustom test environment.
'''


from optparse import OptionParser
import os
import subprocess


N = {}
def pushTo(dest, leaf):
    if leaf not in N:
        N[leaf] = 0
    N[leaf] += 1
    i = N[leaf]
    base = os.path.join(dest, 'repos')
    browserdir = os.path.join(dest, 'workdir', leaf, 'browser')

    if leaf.startswith('l10n'):
        # create initial content for l10n
        open(os.path.join(browserdir, 'file.properties'),
             'w').write('''k_e_y: %s value %d
''' % (leaf, i))
    else:
        # create initial content for mozilla
        open(os.path.join(browserdir, 'locales', 'en-US', 'file.properties'),
             'w').write('''k_e_y: en-US value %d
''' % i)

    env = dict(os.environ)
    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] += ':%s/hghooks' % os.path.abspath(base)
    else:
        env['PYTHONPATH'] = '%s/hghooks' % os.path.abspath(base)
    rv = subprocess.call(['hg', 'ci', '-mCommit %d for %s' % (i, leaf)],
                         cwd=browserdir)
    if rv:
        raise RuntimeError('failed to check in initian content to %s' %
                           leaf)
    rv = subprocess.call(['hg', 'push'], cwd=browserdir, env=env)
    if rv:
        raise RuntimeError('failed to push to %s' % leaf)


data = (
    (13, 'mozilla'),
    (8, 'l10n/ab'),
    (1, 'mozilla'),
    (23, 'l10n/ab'),
    (5, 'mozilla'),
    (2, 'l10n/de'),
    (3, 'l10n/ab'),
)

if __name__ == "__main__":
    p = OptionParser()
    p.add_option('-v', dest='verbose', action='store_true')
    (options, args) = p.parse_args()

    dest = args[0]
    for n, leaf in data:
        for i in xrange(n):
            pushTo(dest, leaf)
