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
from mercurial.commands import pull, update, clone

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--limit', dest='limit', default = 100,
                    action = 'store', type = 'int',
                    help = 'pull N pushes at once'),
        make_option('-U', '--no-update', dest = 'noupdate',
                    action = 'store_true',
                    help = 'Update the repositories if pushes found'),
        make_option('-q', '--quiet', dest = 'quiet', action = 'store_true',
                    help = 'Run quietly')
        )
    help = 'Update the pushes database from hg pushlog json-pushes hook'

    def handle(self, *args, **options):
        limit = options.get('limit')
        quiet = options.get('quiet', False)
        noupdate = options.get('noupdate', False)
        updates = []
        if args:
            repos = Repository.objects.filter(name__in = args)
        else:
            repos = Repository.objects.all()
        for repo in repos:
            url = '%sjson-pushes?startID=%d&endID=%d' % (
                repo.url,
                repo.last_known_push,
                repo.last_known_push + limit)
            if not quiet:
                print url
            try:
                pushes = simplejson.load(urlopen(url))
            except URLError, e:
                if not quiet:
                    print "%s failed: %s" % (repo.name, e)
                continue
            print len(pushes)
            if not pushes:
                continue
            hgrepo = None
            if noupdate:
                updates.append(repo.name)
            else:
                ui = _ui()
                repopath = os.path.join(settings.REPOSITORY_BASE,
                                        repo.name, '')
                configpath = os.path.join(repopath, '.hg', 'hgrc')
                if not os.path.isfile(configpath):
                    clone(ui, str(repo.url), str(repopath),
                          pull=False, uncompressed=False, rev=[],
                          noupdate=False)
                    cfg = open(configpath, 'a')
                    cfg.write('default-push = ssh%s\n' % str(repo.url)[4:])
                    cfg.close()
                    ui.readconfig(configpath)
                    hgrepo = repository(ui, repopath)
                else:
                    ui.readconfig(configpath)
                    hgrepo = repository(ui, repopath)
                    pull(ui, hgrepo, force=False, update=False, rev=['tip'])
                    update(ui, hgrepo)
            id = repo.last_known_push
            ids = pushes.keys()
            ids.sort(lambda l,r: cmp(int(l), int(r)))
            for id in ids:
                data = pushes[id]
                p = Push(push_id = int(id),
                         user = data['user'],
                         repository = repo,
                         push_date = datetime.utcfromtimestamp(data['date']))
                p.save()
                for revision in data['changesets']:
                    cs = Changeset(push = p, revision = revision)
                    cs.save()
            repo.last_known_push = int(id)
            repo.save()
        if updates and not quiet:
            print "Updates needed for " + " ".join(updates)
