from zope.interface import implements

from twisted.python import usage, log
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.application import internet
from twisted.web.client import getPage, HTTPClientFactory

from datetime import datetime
import re
import os
from urlparse import urljoin

class Options(usage.Options):
    optParameters = [["settings", "s", None, "Django settings module."],
                     ["time", "t", "1", "Poll every n seconds."],
                     ]
    optFlags = [
        ["noup", "n", "No updates of repos"],
        ]

def getPoller(options):
    if options["settings"] is None:
            raise usage.UsageError("specify a settings module")
    os.environ["DJANGO_SETTINGS_MODULE"] = options["settings"]
    from pushes.models import Repository, Forest
    from pushes.utils import getURL, handlePushes

    class PushPoller(object):
        def __init__(self, opts):
            self.timeout = 2 * float(options['time'])
            self.limit = int(opts.get('limit', 200))
            self.runnings = 0
            self.parallels = 2
            self.repos = []
            self.start_cycle = None
            self.do_update = not options['noup']
            pass
        def poll(self):
            if self.runnings >= self.parallels:
                repomsg = ''
                if self.repos:
                    repomsg = ' for %s' % self.repos[-1].name
                log.msg("skipping a cycle%s, I'm too busy (%d >= %d)" % 
                        (repomsg, self.runnings, self.parallels))
                return
            if not self.repos:
                n = datetime.now()
                if self.start_cycle is not None:
                    lag = n - self.start_cycle
                    log.msg("Cycle took %d seconds" % lag.seconds)
                self.start_cycle = n
                self.repos = list(Repository.objects.filter(forest__isnull = 
                                                            True))
                self.parallels = 1 # make sure to have all forests
                for forest in Forest.objects.all():
                    url = str(forest.url + '?style=raw')
                    d = getPage(url, timeout = self.timeout)
                    d.addCallback(self.gotForest, forest)
                    d.addErrback(self.failedForest, forest)
                    self.runnings += 1
                return
            repo = self.repos.pop()

            jsonurl = getURL(repo, self.limit)
            d = getPage(str(jsonurl), timeout = self.timeout)
            d.addCallback(handlePushes, repo, self.do_update)
            d.addErrback(self.jsonErr, repo)
            def decreaseRunning(ignored):
                self.runnings -= 1
            d.addBoth(decreaseRunning)
            self.runnings += 1
            

        def gotForest(self, page, forest):
            self.runnings -= 1
            if self.runnings == 0:
                # done with forests, reset our parallels back to max parallels
                self.parellels = 2
            links = filter(None, re.split(r'\s+', page))
            urls = map(lambda link: urljoin(forest.url, link), links)
            q = Repository.objects.filter(url__in = urls)
            self.repos += list(q)
            known_urls = q.values_list('url', flat=True)
            for i in xrange(len(urls)):
                if urls[i] in known_urls:
                    continue
                name = links[i].strip('/')
                if not False:
                    log.msg("adding %s: %s" % (name, urls[i]))
                r = Repository.objects.create(name = name, url = urls[i],
                                              forest = forest)
                self.repos.append(r)

        def failedForest(self, failure, forest):
            log.err(failure, "failed to load %s" % forest.name)
            self.runnings -= 1
        def jsonErr(self, failure, repo):
            log.err(failure, "failed to load json for %s" % repo.name)

    pp = PushPoller(options)
    return pp.poll

class MyServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "get-pushes"
    description = "Gotcha grabbin' repos."
    options = Options

    def makeService(self, options):
        """
        Construct a TCPServer from a factory defined in myproject.
        """
        HTTPClientFactory.noisy = False
        poller = getPoller(options)
        timer = float(options['time'])
        return internet.TimerService(timer, poller)


# Now construct an object which *provides* the relevant interfaces
# The name of this variable is irrelevant, as long as there is *some*
# name bound to a provider of IPlugin and IServiceMaker.

serviceMaker = MyServiceMaker()
