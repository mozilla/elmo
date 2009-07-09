from optparse import make_option
import os.path

from django.core.management.base import BaseCommand, CommandError
from pushes.models import *
from django.conf import settings

from mercurial.hg import repository
from mercurial.ui import ui as _ui

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('-q', '--quiet', dest = 'quiet', action = 'store_true',
                    help = 'Run quietly'),
        )
    help = 'Add all parents to the changsets, needs local clones'
    args = '[repository name]*'

    def handle(self, *args, **options):
        quiet = options.get('quiet', False)
        if args:
            repos = Repository.objects.filter(name__in = args)
        else:
            repos = Repository.objects.all()
        for repo in repos:
            if not repo.changesets.count():
                continue
            if not quiet:
                print "Checking %s" % repo.name
            ui = _ui()
            repopath = os.path.join(settings.REPOSITORY_BASE,
                                    repo.name, '')
            configpath = os.path.join(repopath, '.hg', 'hgrc')
            if not os.path.isfile(configpath):
                print "You need to clone " + repo.name
                for p in repo.changesets.iterator():
                    print repo.name, cs.revision
                continue
            ui.readconfig(configpath)
            hgrepo = repository(ui, repopath)
            for cs in repo.changesets.iterator():
                try:
                    ctx = hgrepo.changectx(cs.revision)
                    parents = map(lambda _cx: _cx.hex(), ctx.parents())
                    p_cs = Changeset.objects.filter(revision__in=parents,
                                                    repository=repo)
                    cs.parents.add(*list(p_cs))
                    cs.save()
                except Exception, e:
                    print repo.name, e
