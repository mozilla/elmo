from datetime import datetime
from optparse import make_option
import os.path
from urllib2 import urlopen, URLError

import simplejson

from django.core.management.base import BaseCommand, CommandError
from pushes.models import *
from django.conf import settings

from mercurial.hg import repository
from mercurial.ui import ui as _ui

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('-f', '--fix', dest = 'fix', action = 'store_true',
                    help = 'Fix db errors'),
        make_option('-r', '--repo', dest = 'repo', action = 'store_true',
                    help = 'test repos, too'),
        make_option('-q', '--quiet', dest = 'quiet', action = 'store_true',
                    help = 'Run quietly'),
        )
    help = 'Verify the pushes database against the local clones'
    args = '[repository name]*'

    def handle(self, *args, **options):
        fix = options.get('fix', False)
        test_repo = options.get('repo', False)
        quiet = options.get('quiet', False)
        if args:
            repos = Repository.objects.filter(name__in = args)
        else:
            repos = Repository.objects.all()
        for repo in repos:
            if not repo.push_set.count():
                if repo.last_known_push != 0:
                    if not quiet:
                        print repo.name + " has bad last_known_push"
                    if fix:
                        repo.last_known_push = 0
                        repo.save()
                        if not quiet:
                            print "  ... fixed"
                continue
            ids=repo.push_set.all().values_list('push_id', flat=True)
            last_good_push = ids[len(ids)-1]
            if ids[0] != 1:
                if not quiet:
                    print repo.name + " has all broken pushes"
                continue
            for i in xrange(len(ids) - 1):
                if ids[i + 1] != ids[i] + 1:
                    last_good_push = ids[i]
                    break
            if last_good_push != repo.last_known_push:
                if not quiet:
                    print repo.name + " should get pushes killed"
            if not test_repo:
                continue
            if not quiet:
                print "Checking %s" % repo.name
            ui = _ui()
            repopath = os.path.join(settings.REPOSITORY_BASE,
                                    repo.name, '')
            configpath = os.path.join(repopath, '.hg', 'hgrc')
            if not os.path.isfile(configpath):
                print "You need to clone " + repo.name
                for p in repo.push_set.iterator():
                    for cs in p.changeset_set.iterator():
                        print repo.name, cs.revision
                continue
            ui.readconfig(configpath)
            hgrepo = repository(ui, repopath)
            for p in repo.push_set.iterator():
                for cs in p.changeset_set.iterator():
                    try:
                        ctx = hgrepo.changectx(cs.revision)
                    except Exception, e:
                        print repo.name, e
