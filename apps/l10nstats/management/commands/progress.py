# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Create background images for progress previews
'''

from collections import defaultdict
from datetime import timedelta
from optparse import make_option
import os.path

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Max

from l10nstats.models import Run, ProgressPosition
from life.models import Locale, Tree

import PIL.Image
import PIL.ImageDraw


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('-q', '--quiet', dest='quiet', action='store_true',
                    help='Run quietly'),
        )
    help = 'Create background images for progress previews'
    width = settings.PROGRESS_IMG_SIZE['x']
    height = settings.PROGRESS_IMG_SIZE['y']
    days = settings.PROGRESS_DAYS
    line_fill = (0, 128, 0)
    area_fill = (0, 128, 0, 20)

    def handle(self, *args, **options):
        runs = Run.objects.exclude(srctime__isnull=True)
        enddate = runs.aggregate(Max('srctime'))['srctime__max']
        startdate = enddate - timedelta(days=self.days)
        scale = 1. * (self.width - 1) / total_seconds(enddate - startdate)
        runs = runs.filter(srctime__gte=startdate,
                           srctime__lte=enddate)
        locales = sorted(runs.values_list('locale__code', flat=True)
                        .distinct())
        trees = sorted(runs.values_list('tree__code', flat=True)
                       .distinct())
        runs = runs.order_by('srctime')
        offloc = dict((loc, (i + 1) * self.height)
                      for i, loc in enumerate(locales))
        offtree = dict((tree, i * self.width)
                       for i, tree in enumerate(trees))
        offtree[trees[0]] = 0
        im = PIL.Image.new("RGBA", (self.width * len(trees),
                                    self.height * len(locales)))
        draw = PIL.ImageDraw.Draw(im, "RGBA")
        tuples = defaultdict(list)
        locales = set()
        trees = set()
        for loc, tree, srctime, completion in runs.values_list('locale__code',
                                                               'tree__code',
                                                               'srctime',
                                                               'completion'):
            tuples[(loc, tree)].append((srctime, completion))
            locales.add(loc)
            trees.add(tree)
        locales = dict((l.code, l)
                       for l in
                       (Locale.objects
                        .filter(code__in=locales)))
        trees = dict((t.code, t)
                     for t in
                     (Tree.objects
                      .filter(code__in=trees)))
        backobjs = []
        for (loc, tree), vals in tuples.iteritems():
            if len(vals) > 1:
                # maybe resize
                vals = self.rescale(vals)
            oldx = oldy = None
            _offy = offloc[loc]
            _offx = offtree[tree]
            for srctime, completion in vals:
                x = _offx + int(total_seconds(srctime - startdate) * scale)
                y = _offy - completion * (self.height - 1) / 100
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

    def rescale(self, vals):
        _min = min(c for _, c in vals)
        _max = max(c for _, c in vals)
        if ((_min <= 25 and _max >= 75) or
            (_min >= _max)):
            # no resize needed or useful
            return vals
        bottom = _min if _min <= 25 else 25
        top = _max if _max >= 75 else 75
        ratio = float(top - bottom) / (_max - _min)
        scale = lambda v: (v - _min) * ratio + bottom
        return [(t, scale(c)) for t, c in vals]

# python 2.6 helper
# XXX remove when we migrate to 2.7
def total_seconds(td):
    if hasattr(timedelta,'total_seconds'):
        return td.total_seconds()
    return ((td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6)
            / 10**6)
