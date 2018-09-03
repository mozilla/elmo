# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Create background images for progress previews
'''
from __future__ import absolute_import, division
from __future__ import unicode_literals

from collections import defaultdict
from datetime import timedelta
import os.path

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Max, Q

from l10nstats.models import Run, ProgressPosition
from life.models import Locale, Tree

import PIL.Image
import PIL.ImageDraw
import six


class Command(BaseCommand):
    help = 'Create background images for progress previews'
    width = settings.PROGRESS_IMG_SIZE['x']
    height = settings.PROGRESS_IMG_SIZE['y']
    days = settings.PROGRESS_DAYS
    line_fill = (0, 128, 0)
    area_fill = (0, 128, 0, 20)

    def add_arguments(self, parser):
        parser.add_argument('tree', nargs='*')

    def handle(self, **options):
        q = Q()
        if options['tree']:
            q = Q(tree__code__in=options['tree'])
        runs = Run.objects.exclude(srctime__isnull=True)
        enddate = runs.aggregate(Max('srctime'))['srctime__max']
        if enddate is None:
            return
        startdate = enddate - timedelta(days=self.days)
        scale = 1. * (self.width - 1) / (enddate - startdate).total_seconds()
        runs = runs.filter(q, srctime__gte=startdate,
                           srctime__lte=enddate)
        runs = runs.order_by('srctime')
        tuples = defaultdict(list)
        tree2locs = defaultdict(set)
        locales = set()
        trees = set()
        for loc, tree in (Run.objects
                          .filter(q, active__isnull=False)
                          .values_list('locale__code', 'tree__code')):
            tree2locs[tree].add(loc)
            locales.add(loc)
            trees.add(tree)
        runs = runs.values_list('locale__code',
                                'tree__code',
                                'srctime',
                                'changed',
                                'total')
        for loc, tree, srctime, changed, total in runs:
            tuples[(loc, tree)].append((srctime, changed, total))
            tree2locs[tree].add(loc)
            locales.add(loc)
            trees.add(tree)
        initialCoverage = self.initialCoverage(tree2locs, startdate)
        for (loc, tree), (c, t) in initialCoverage.items():
            tuples[(loc, tree)].insert(0, (startdate, c, t))
        locales = sorted(locales)
        trees = sorted(trees)
        offloc = dict((loc, (i + 1) * self.height)
                      for i, loc in enumerate(locales))
        offtree = dict((tree, i * self.width)
                       for i, tree in enumerate(trees))
        offtree[trees[0]] = 0
        im = PIL.Image.new("RGBA", (self.width * len(trees),
                                    self.height * len(locales)))
        draw = PIL.ImageDraw.Draw(im, "RGBA")
        locales = dict((l.code, l)
                       for l in
                       (Locale.objects
                        .filter(code__in=locales)))
        trees = dict((t.code, t)
                     for t in
                     (Tree.objects
                      .filter(code__in=trees)))
        backobjs = []
        for (loc, tree), vals in six.iteritems(tuples):
            rescale = self.rescale(vals)
            oldx = oldy = None
            _offy = offloc[loc]
            _offx = offtree[tree]
            for srctime, changed, total in vals:
                x = _offx + int((srctime - startdate).total_seconds() * scale)
                y = _offy - rescale(changed) * (self.height - 1)
                if oldx is not None:
                    if x > oldx + 1:
                        draw.rectangle([oldx + 1, oldy, x, _offy],
                                       fill=self.area_fill)
                        draw.line([oldx + 1, oldy, x, oldy],
                                  fill=self.line_fill)
                _y = min(y, oldy) if oldy is not None else y
                (oldx, oldy) = (x, y)
                pnts = [x, _offy, x, _y]
                draw.line(pnts, fill=self.line_fill)
            x = _offx + self.width - 1
            draw.rectangle([oldx + 1, oldy, x, _offy], fill=self.area_fill)
            draw.line([oldx + 1, oldy, x, oldy], fill=self.line_fill)
            offy = self.height - offloc[loc]
            if offy < 0:
                offy -= 1  # skip past the image above for real
            backobjs.append(ProgressPosition(tree=trees[tree],
                                             locale=locales[loc],
                                             x=-offtree[tree],
                                             y=offy))
        pal = im.convert("P", palette="ADAPTIVE")
        pal.save(os.path.join(settings.STATIC_ROOT,
                              settings.PROGRESS_IMG_NAME))
        ProgressPosition.objects.all().delete()
        ProgressPosition.objects.bulk_create(backobjs)

    def rescale(self, vals, span=.75):
        # return a scaling function for change values
        # Make graph at least "span" % high
        # Ensure that upper and lower space have the same
        # proportions as the original graph
        # The scaling function return a value 0 <= v <= 1
        _min = min(c for _, c, __ in vals)
        _max = max(c for _, c, __ in vals)
        total = max(t for _, __, t in vals)
        if (
                (_max - _min) >= total * span or
                (_min >= _max)
        ):
            # no resize needed or useful
            return lambda v: 1.0 * v / total
        ratio = span / (_max - _min)
        offset = (1.0 - span) * _min / (total - _max + _min)
        return lambda v: (v - _min) * ratio + offset

    def initialCoverage(self, tree2locs, startdate):
        rv = {}
        for tree, locales in six.iteritems(tree2locs):
            locs = (
                Locale.objects
                .filter(code__in=locales)
                .filter(run__srctime__lt=startdate, run__tree__code=tree)
                .annotate(mr=Max('run'))
            )
            for l, r in locs.values_list('code', 'mr'):
                rv[(l, tree)] = r
        r2r = {
            id: (c, t)
            for id, c, t in
            Run.objects
            .filter(id__in=rv.values())
            .values_list('id', 'changed', 'total')
        }
        return dict((t, r2r[r]) for t, r in rv.items())
