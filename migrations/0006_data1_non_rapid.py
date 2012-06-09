# Data 1.1 migration, step 2, data adjustments for non-rapid trees
# and appversions
# For Trees that are
#   * not on the rapid cycle,
#   * not building anymore,
# set the AppVersionTreeThrough to the earliest and latest Run.srctime
# also set `fallsback` to false for non-rapid appversions


def migrate():
    from django.db.models import Min, Max
    from shipping.models import AppVersionTreeThrough
    from life.models import Tree
    trees = dict((t.id, t) for t in
                 Tree.objects
        .filter(appvers_over_time__end__isnull=False)
        .exclude(l10n__name__startswith='releases/l10n/')
        .annotate(mindate=Min('run__srctime'), maxdate=Max('run__srctime')))
    for avt in AppVersionTreeThrough.objects.filter(tree__in=trees.keys()):
        t = trees[avt.tree_id]
        avt.start = t.mindate
        avt.end = t.maxdate
        avt.save()
