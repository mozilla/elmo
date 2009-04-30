#!/usr/bin/env python

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
