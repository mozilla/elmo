from optparse import make_option
from urllib2 import urlopen, URLError
from urlparse import urljoin

from django.core.management.base import BaseCommand, CommandError
from pushes.models import *

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('-q', '--quiet', dest = 'quiet', action = 'store_true',
                    help = 'Run quietly'),
        )
    help = 'Update the repository list in the db from a given url'
    args = 'repository-url'

    def handle(self, *args, **options):
        if not args:
            raise CommandError('url required')
        quiet = options.get('quiet', False)
        url =  args[0] + "?style=raw"
        try:
            f = urlopen(url)
        except URLError, e:
            raise CommandError("Couldn't load %s\n  %s" % (args[0], e.args[0][1]))
        links = filter(None, [link.strip() for link in f])
        urls = map(lambda link: urljoin(url, link), links)
        q = Repository.objects.filter(url__in = urls)
        known_urls = q.values_list('url', flat=True)
        if not quiet:
            print '%d repos exist' % len(known_urls)
        if len(known_urls) == len(urls):
            if not quiet:
                print "all urls in the db"
            return
        for i in xrange(len(urls)):
            if urls[i] in known_urls:
                continue
            name = links[i].strip('/')
            if not quiet:
                print "adding %s: %s" % (name, urls[i])
            Repository.objects.create(name = name, url = urls[i])
