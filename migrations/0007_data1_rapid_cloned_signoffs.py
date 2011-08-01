# Data 1.1 migration, step 3
# Remove cloned sign-offs on rapid release AppVersions
# Make sure that they're having the same amount of actions
# in case a new sign-off got OBSOLETED going forward, for example.


def migrate():
    from shipping.models import (Signoff, Action, AppVersion,
                                 Milestone_Signoffs)
    from life.models import Tree
    from collections import defaultdict
    from django.db.models import Count

    rapid_trees = list(Tree.objects
                       .filter(l10n__name__startswith='releases/l10n/')
                       .values_list('id', flat=True))
    rapid_avs = list(AppVersion.objects
                     .filter(trees_over_time__tree__in=rapid_trees)
                     .values_list('id', flat=True))
    app4av = dict(AppVersion.objects
                  .filter(id__in=rapid_avs)
                  .values_list('id', 'app_id'))

    sos = (Signoff.objects
           .filter(appversion__in=rapid_avs)
           .annotate(ac=Count('action'))
           .order_by('-when', 'appversion'))

    cut = sos.values_list('when', flat=True)[0]
    while cut is not None:
        try:
            next_cut = (sos.filter(when__lt=cut)
                        .values_list('when', flat=True)[500])
        except IndexError:
            next_cut = None
        slice = sos.filter(when__lte=cut)
        if next_cut is not None:
            slice = slice.filter(when__gte=next_cut)
        # find dupes in the slice, same app, and otherwise same signoff.
        # ignore locale, as that's part of the push implicitly, too
        c = defaultdict(list)
        for so in slice:
            c[(so.when,
               so.author_id,
                so.push_id,
                so.ac,
                app4av[so.appversion_id])].append(so.id)
        dupes = dict(filter(lambda t: len(t[1]) > 1, c.iteritems()))
        obsolete = []
        obsdict = {}
        for so_ids in dupes.itervalues():
            obsolete += so_ids[1:]
            obsdict[so_ids[0]] = set(so_ids[1:])
        removed_shippin = set(Signoff.objects
                              .filter(id__in=obsolete,
                                      shipped_in__isnull=False)
                              .values_list('id',flat=True).distinct())
        # map removed to non-remoted Milestone_Signoffs
        for target, olds in obsdict.iteritems():
            tomap = olds & removed_shippin
            if tomap:
                (Milestone_Signoffs.objects
                 .filter(signoff__in=tomap)
                 .update(signoff=target))
        a_len = Action.objects.count()
        Signoff.objects.filter(id__in=obsolete).delete()
        a_len -= Action.objects.count()
        print "deleted %d signoffs and %d actions between:" % (len(obsolete), a_len), cut, next_cut
        print
        cut = next_cut
