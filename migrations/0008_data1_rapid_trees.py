# Data 1.1 migration, step 4
# Adjust AppVersionTreeThrough for rapid release appversions,
# and hook up fallback avs.
# Also make the building appversion except central accept sign-offs


def migrate():
    from django.db.models import Q
    from collections import defaultdict
    from datetime import datetime
    import re
    from shipping.models import (Application, AppVersion, AppVersionTreeThrough,
                             Signoff)
    from life.models import Tree

    lastdigits = re.compile('\d+$')


    def inc(s):
        return lastdigits.sub(lambda m: str(int(m.group()) + 1), s)

    loads_a_dates = (
        datetime(2011, 3, 3, 20),  # 0: gecko5 on central
        datetime(2011, 4, 12, 14),   # 1: gecko5 on aurora, 6 on central
        datetime(2011, 5, 17, 17),  # 2: gecko5 on beta
        datetime(2011, 5, 24, 18),  # 3: gecko 6 on aurora, 7 on central
        datetime(2011, 6, 15, 22),  # 4: gecko5 shipped (?)(4)
        datetime(2011, 7, 5, 17),   # 5: gecko7 on aurora, 6 on beta, 8 on central
        datetime(2011, 8, 12, 00),  # 6: gecko 6 shipped (?)
        datetime(2011, 8, 16, 17),  # 7: gecko8 on aurora, 7 on beta, 9 on central
        datetime(2011, 9, 27, 20),  # 8: gecko9 on aurora
        datetime(2011, 11, 8, 20),  # 9: gecko10 on aurora
        datetime(2011, 12, 20, 20),  # 10: gecko11 on aurora
        datetime(2012, 01, 31, 13),  # 11: gecko12 on aurora
        datetime(2012, 03, 13, 21),  # 12: gecko13 on aurora
        datetime(2012, 04, 24, 17),  # 13: gecko14 on aurora
        datetime(2012, 06, 04, 20)  # 14: gecko15 on aurora
        )

    max_gecko = len(loads_a_dates) + 1

    periods = {}
    periods[(5, 'central')] = {'start': loads_a_dates[0],
                              'end': loads_a_dates[1]}
    periods[(6, 'central')] = {'start': periods[(5, 'central')]['end'],
                               'end': loads_a_dates[3]}
    periods[(7, 'central')] = {'start': periods[(6, 'central')]['end'],
                               'end': loads_a_dates[5]}
    periods[(8, 'central')] = {'start': periods[(7, 'central')]['end'],
                               'end': loads_a_dates[7]}
    for g in xrange(9, max_gecko):
        periods[(g, 'central')] = {'start': periods[(g - 1, 'central')]['end'],
                                   'end': loads_a_dates[g - 1]}

    g += 1
    periods[(g, 'central')] = {'start': periods[(g - 1, 'central')]['end'],
                               'end': None}

    periods[(5, 'aurora')] = {'start': periods[(5, 'central')]['end'],
                              'end': loads_a_dates[2]}  # no-6-weeks for 5
    for g in xrange(6, max_gecko):
        periods[(g, 'aurora')] = periods[(g + 1, 'central')]

    # shipped datetime(2011, 6, 15, 22)
    periods[(5, 'beta')] = {'start': periods[(5, 'aurora')]['end'],
                            'end': periods[(6, 'aurora')]['end']}
    for g in xrange(6, max_gecko - 1):
        periods[(g, 'beta')] = periods[(g + 2, 'central')]

        trees = dict((tuple(t.code.split('_')), t)
                     for t in Tree.objects.filter(Q(code__endswith='_central') |
                                                  Q(code__endswith='_aurora') |
                                                  Q(code__endswith='_beta')))
        appid4code = dict(Application.objects
                          .filter(code__in=map(lambda t: t[0], trees.keys()))
                          .values_list('code', 'id'))

    def trees4branch(*branches):
        for (_, branch), tree in trees.iteritems():
            if branch in branches:
                yield tree

    geckos = defaultdict(list)
    for av in (AppVersion.objects
               .filter(trees__in=trees4branch('beta'))
               .select_related('app')
               .order_by('pk')):
        geckos[av.app_id].append(av)

    # hook up fallbacks for our rapid release AVs, and create new AVs
    # for aurora and central
    for app_id, avs in geckos.iteritems():
        av = None
        fb = avs[0]
        for av in avs[1:]:
            av.fallback = fb
            av.save()
            fb = av
        # create aurora and central av
        for i in xrange(2):
            fb = (AppVersion.objects
                  .create(app=fb.app,
                          version=inc(fb.version),
                          code=inc(fb.code),
                          fallback=fb))
            avs.append(fb)
    # btw, we didn't do fallback for fennec for a while
    (AppVersion.objects
     .filter(code__in=['fennec11',
                       'fennec12',
                       'fennec13',
                       'fennec14'])
     .update(fallback=None))

    # do something with aurora avs,
    # map their sign-offs to the appversions that will have
    # the right tree at the time.
    auroras = dict((av.app_id, av)
                   for av in (AppVersion.objects
                              .filter(version='Aurora')
                              .select_related('app')))

    # YIKES, let's through some data away.
    # In the time between aurora 5 and 6, there was no AV for aurora.
    # De-facto, this is two rejected sign-offs, so no big loss:
    (Signoff.objects
     .filter(push__push_date__gt=periods[(5, 'aurora')]['end'],
             push__push_date__lt=periods[(6, 'aurora')]['start'],
             appversion__in=auroras.values())
     .delete())

    # migrate sign-offs on pushes on aurora to versioned appversion
    for gecko in xrange(5, max_gecko):
        dates = periods[(gecko, 'aurora')]
        print gecko, dates['end']
        for app, av in auroras.iteritems():
            if gecko - max_gecko - 1 < -len(geckos[app]):
                continue
            target_av = geckos[app][gecko - max_gecko - 1]
            print "doing", av, "to", target_av
            sos = (Signoff.objects.filter(appversion=av,
                                          push__push_date__gte=dates['start']))
            if dates['end'] is not None:
                sos = sos.filter(push__push_date__lte=dates['end'])
            sos.update(appversion=target_av)

    # remove old aurora appversions
    for av in auroras.itervalues():
        av.delete()

    # now adjust all the AppVersion.trees_over_time, collect data first
    avt_dicts = {}
    for (app, branch), tree in trees.iteritems():
        app_id = appid4code[app]
        for gecko in xrange(5, max_gecko + 1):
            if gecko - max_gecko - 1 < -len(geckos[app_id]):
                continue
            if (gecko, branch) not in periods:
                continue
            d = {'tree': tree,
                 'appversion': geckos[app_id][gecko - max_gecko - 1]}
            d.update(periods[(gecko, branch)])
            avt_dicts[(d['appversion'].id, d['tree'].id)] = d

    # now fix up existing avts:
    for avt in AppVersionTreeThrough.objects.all():
        d = avt_dicts.pop((avt.appversion_id, avt.tree_id), None)
        if d:
            avt.start = d['start']
            avt.end = d['end']
            avt.save()

    # now the new old ones:
    for d in avt_dicts.itervalues():
        AppVersionTreeThrough.objects.create(**d)

    # make building appversions except central accept sign-offs
    (AppVersion.objects
     .filter(id__in=AppVersionTreeThrough.objects
             .current()
             .exclude(tree__code__endswith='central')
             .values_list('appversion',flat=True))
     .update(accepts_signoffs=True))
