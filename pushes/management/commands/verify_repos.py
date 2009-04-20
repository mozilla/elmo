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
            ids=repo.push_set.all().values_list('push_id', flat=True)
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
                for cs in p.changesets.iterator():
                    try:
                        ctx = hgrepo.changectx(cs.revision)
                        branch = ctx.branch()
                        if branch != 'default':
                            dbb, created = \
                                Branch.objects.get_or_create(name=branch)
                            if created and not quiet:
                                print "Created branch object for %s" % branch
                            cs.branch = dbb
                            cs.save()
                    except Exception, e:
                        print repo.name, e
