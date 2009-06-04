from zope.interface import implements

from twisted.python import usage, log
from twisted.plugin import IPlugin
from twisted.application.service import IServiceMaker
from twisted.application import internet
from twisted.internet import task, defer, error, reactor
from twisted.web.client import getPage, HTTPClientFactory

from datetime import datetime
import re
import os
from urlparse import urljoin
try:
    import json
except ImportError:
    import simplejson as json

class Options(usage.Options):
    optParameters = [["settings", "s", None, "Django settings module."],
                     ["time", "t", "1", "Poll every n seconds."],
                     ["limit", "l", "200", "Limit pushes to n at a time."]
                     ]
    optFlags = [
        ["noup", "n", "No updates of repos"],
        ]


class pushback_iter(object):
  '''Utility iterator that can deal with pushed back elements.

  This behaves like a regular iterable, just that you can call
    iter.pushback(item)
  to get the givem item as next item in the iteration.
  '''
  def __init__(self, iterable):
    self.it = iter(iterable)
    self.pushed_back = []

  def __iter__(self):
    return self

  def __nonzero__(self):
    if self.pushed_back:
      return True

    try:
      self.pushed_back.insert(0, self.it.next())
    except StopIteration:
      return False
    else:
      return True

  def next(self):
    if self.pushed_back:
      return self.pushed_back.pop()
    return self.it.next()

  def pushback(self, item):
    self.pushed_back.append(item)



def getPoller(options):
    if options["settings"] is None:
            raise usage.UsageError("specify a settings module")
    os.environ["DJANGO_SETTINGS_MODULE"] = options["settings"]
    from pushes.models import Repository, Forest, Locale
    from pushes.utils import getURL, handlePushes, PushJS

    class PushPoller(object):
        '''PushPoller stores the state of our coopertive iterator.

        The actual worker is poll().
        '''

        debug = False

        def __init__(self, opts):
            self.limit = int(opts.get('limit', 200))
            self.timeout = 5
            self.repos = []
            self.cache = {}
            self.moredata = {}
            self.start_cycle = None
            self.do_update = not options['noup']
            pass

        def poll(self):
            '''poll iterates over the repos and updates the local database.

            The actual updates are done in processPushes.

            The iterator stores the latest json from the upstream repos,
            and submits those on the next round. That way, we can add
            all pushes in that timewindow in order, which helps when
            actually polling the db to get the changes in 
            chronological order.

            For repos that have more pushes than the current limit, we
            poll them again immediately to get further data.

            This iterator doesn't terminate, but gets killed together
            with the service.
            '''
            while True:
                n = datetime.now()
                if self.start_cycle is not None:
                    lag = n - self.start_cycle
                    log.msg("Cycle took %d seconds" % lag.seconds)
                self.start_cycle = n
                repos = list(Repository.objects.filter(forest__isnull = 
                                                       True))
                self.forests = pushback_iter(Forest.objects.all())
                for forest in self.forests:
                    url = str(forest.url + '?style=raw')
                    d = getPage(url, timeout = self.timeout)
                    d.addCallback(self.gotForest, forest, repos)
                    d.addErrback(self.failedForest, forest)
                    yield d
                self.repos = pushback_iter(repos)
                for repo in self.repos:
                    d = None
                    if repo.id in self.cache and self.cache[repo.id]:
                        pushes = self.cache.pop(repo.id)
                        self.processPushes(pushes, repo)
                        if pushes:
                            if self.debug:
                                log.msg("Still have %s left for %s" %
                                        (", ".join(map(str, pushes)),
                                         repo.name))
                            self.cache[repo.id] = pushes
                            d = defer.succeed(None)
                    if d is None:
                        jsonurl = getURL(repo, self.limit)
                        if self.debug:
                            log.msg(jsonurl)
                        d = getPage(str(jsonurl), timeout = self.timeout)
                        d.addCallback(self.loadJSON, repo)
                        d.addErrback(self.jsonErr, repo)
                    yield d

        def loadJSON(self, page, repo):
            pushes = json.loads(page)
            if not pushes:
                return
            log.msg("%s got %d pushes" % (repo.name, len(pushes)))
            # convert pushes to sorted list
            if repo.id not in self.cache:
                self.cache[repo.id] = []
            self.cache[repo.id] += sorted((PushJS(k, v)
                                           for k, v in pushes.iteritems()),
                                          key = lambda p: p.id)
            # signal to load more data if this push hit the limits
            if len(pushes) == self.limit:
                self.moredata[repo.id] = True

        def processPushes(self, pushes, repo):
            '''process the pushes for the given repository.

            This code also adds all pushes that are older than the
            newest push on this repo, in order. If the amount of pushes
            exceeds the limit, pushback the current repo to get more changes.
            If we're emptying another's repo push cache, re-poll???.
            '''
            if len(pushes) == self.limit:
                self.repos.pushback(repo)
            if self.debug:
                log.msg("submitting %s to %s" % (', '.join(map(str, pushes)),
                                                 repo.name))
            def get_date(p, op):
                return op(map(lambda d: d['date'], p.itervalues()))
            maxdate = pushes[-1].date
            tips = sorted(((id, p[0].date)
                           for id, p in self.cache.iteritems() if p),
                          key = lambda t: t[1])
            while pushes:
                if tips and pushes[0].date > tips[0][1]:
                    # other repos come first, get them done
                    other = self.cache[tips[0][0]]
                    if len(tips) > 1:
                        stopdate = min(pushes[0].date,
                                       self.cache[tips[1][0]][0].date)
                    else:
                        stopdate = pushes[0].date
                    i = 0
                    while i < len(other) and \
                            other[i].date <= stopdate:
                        i += 1
                    submits = other[:i]
                    if self.debug:
                        log.msg("pushing %s to %d" % 
                                (", ".join(map(str, submits)), 
                                 tips[0][0]))
                    handlePushes(tips[0][0], submits, self.do_update)
                    del other[:i]
                    if not other:
                        # other repo is empty, let's see if we need to load more
                        if tips[0][0] in self.moredata:
                            self.moredata.pop(tips[0][0])
                            other_repo = Repository.objects.get(id=tips[0][0])
                            self.repos.pushback(other_repo)
                            return
                    tips = sorted(((id, p[0].date)
                                   for id, p in self.cache.iteritems() if p),
                                  key = lambda t: t[1])
                else:
                    i = 0
                    if tips:
                        stopdate = self.cache[tips[0][0]][0].date
                        while i < len(pushes) and \
                                pushes[i].date <= stopdate:
                            i += 1
                    else:
                        i = len(pushes)
                    submits = pushes[:i]
                    if self.debug:
                        log.msg("pushing %s to %d" % 
                                (", ".join(map(str, submits)), 
                                 repo.id))
                    handlePushes(repo.id, submits, self.do_update)
                    del pushes[:i]

        def gotForest(self, page, forest, repos):
            links = filter(None, re.split(r'\s+', page))
            urls = map(lambda link: urljoin(forest.url, link), links)
            q = Repository.objects.filter(url__in = urls)
            repos += list(q)
            known_urls = q.values_list('url', flat=True)
            for i in xrange(len(urls)):
                if urls[i] in known_urls:
                    continue
                name = links[i].strip('/')
                if self.debug:
                    log.msg("adding %s: %s" % (name, urls[i]))
                # Forests are holding l10n repos, set locale
                locale, create = \
                    Locale.objects.get_or_create(code=name.rsplit('/',1)[1])
                r = Repository.objects.create(name = name, url = urls[i],
                                              forest = forest)
                repos.append(r)

        def failedForest(self, failure, forest):
            log.err(failure, "failed to load %s" % forest.name)
            failure.trap(defer.TimeoutError)
            self.forests.pushback(forest)
        def jsonErr(self, failure, repo):
            # catch errors on killing the service
            failure.trap(task.SchedulerStopped, error.ConnectionLost,
                         defer.TimeoutError)
            log.err(failure, "failed to load json for %s, adding back" % repo.name)
            self.repos.pushback(repo)

    pp = PushPoller(options)
    return pp.poll()


class PacedCooperator(internet.CooperatorService):
    def __init__(self, wait):
        self.wait = wait
        self.coop = task.Cooperator(started=False,
                                    scheduler = self.sched)
    def sched(self, x):
        return reactor.callLater(self.wait, x)


class MyServiceMaker(object):
    implements(IServiceMaker, IPlugin)
    tapname = "get-pushes"
    description = "Gotcha grabbin' repos."
    options = Options

    def makeService(self, options):
        """
        Construct a TCPServer from a factory defined in myproject.
        """
        # set umask back to public reading against twistd daemonize
        os.umask(18)
        HTTPClientFactory.noisy = False
        poller = getPoller(options)
        timer = float(options['time'])
        s = PacedCooperator(timer)
        s.coiterate(poller)
        return s


# Now construct an object which *provides* the relevant interfaces
# The name of this variable is irrelevant, as long as there is *some*
# name bound to a provider of IPlugin and IServiceMaker.

serviceMaker = MyServiceMaker()
