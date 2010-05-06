from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--rebase', action = 'store_true',
                    help = 'Use --rebase for hg pull'),
        make_option('-u', '--update', action = 'store_true',
                    help = 'Use -u for hg pull'),
        make_option('-a', '--all', action = 'store_true',
                    help = 'Refresh all repositories'),
        )
    help = 'Update set of local clones'

    def handle(self, *args, **options):
        rebase = options.get('rebase', False)
        update = options.get('update', False)
        all = options.get('all', False)
        if rebase:
            pull_args = ['--rebase']
        elif update:
            pull_args = ['-u']
        from life.models import Repository, Changeset
        from mercurial.dispatch import dispatch as hgdispatch
        import os.path
        from django.conf import settings

        def resolve(path):
            return os.path.join(settings.REPOSITORY_BASE, *path.split('/'))

        # check for last push helper file
        if not all and os.path.isfile(resolve('.latest_cs')):
            latest_cs = int(open(resolve('.latest_cs')).read())
            repos = Repository.objects.filter(changesets__id__gt=latest_cs).distinct()
        else:
            repos = Repository.objects.all()
        latest_cs = Changeset.objects.order_by('-pk')[0].id

        for name, url in repos.values_list('name','url'):
            repopath = str(resolve(name))
            if not os.path.isdir(os.path.join(repopath, '.hg')):
                # new repo, need to clone
                if os.path.isdir(repopath):
                    print "\n\nCannot clone %s, existing directory in the way\n\n" % name
                    continue
                _parent = os.path.dirname(repopath)
                if not os.path.isdir(_parent):
                    try:
                        os.makedirs(_parent)
                    except Exception, e:
                        print "\n\nFailed to prepare for clone, %s\n\n" % str(e)
                        continue
                hgdispatch(['clone', str(url), repopath])
            else:
                hgdispatch(['pull', '-R', repopath] + pull_args)

        open(resolve('.latest_cs'),'w').write('%i\n' % latest_cs)
