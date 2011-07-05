# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is l10n django site.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

'''Views for managing sign-offs and shipping metrics.
'''

from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string
from django.http import (HttpResponseRedirect, HttpResponse, Http404,
                         HttpResponseNotAllowed)
from life.models import Repository, Locale, Push, Changeset, Tree
from shipping.models import (Milestone, Signoff, Snapshot, AppVersion, Action,
                             SignoffForm, ActionForm)
from l10nstats.models import Run, Run_Revisions
from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse
from django.views.decorators.cache import cache_control
from django.utils import simplejson
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from django.core import serializers
from django.db import connection
from django.db.models import Max

from collections import defaultdict
from ConfigParser import ConfigParser
import datetime
from difflib import SequenceMatcher
import re
import urllib

from Mozilla.Parser import getParser, Junk
from Mozilla.CompareLocales import AddRemove, Tree as DataTree


def index(request):
    locales = Locale.objects.all().order_by('code')
    avs = AppVersion.objects.all().order_by('code')

    for i in avs:
        statuses = Milestone.objects.filter(appver=i.id).values_list('status', flat=True).distinct()
        if 1 in statuses:
            i.status = 'open'
        elif 0 in statuses:
            i.status = 'upcoming'
        elif 2 in statuses:
            i.status = 'shipped'
        else:
            i.status = 'unknown'

    return render_to_response('shipping/index.html', {
        'locales': locales,
        'avs': avs,
    })

def homesnippet(request):
    q = AppVersion.objects.filter(milestone__status=1).select_related('app')
    q = q.order_by('app__name','-version')
    return render_to_string('shipping/snippet.html', {
            'appvers': q,
            })


def teamsnippet(request, loc):
    return render_to_string('shipping/team-snippet.html', {
            'locale': loc,
            })


def __universal_le(content):
    "CompareLocales reads files with universal line endings, fake that"
    return content.replace('\r\n','\n').replace('\r','\n')

def diff_app(request):
    # XXX TODO: error handling
    reponame = request.GET['repo']
    repopath = settings.REPOSITORY_BASE + '/' + reponame
    repo_url = Repository.objects.filter(name=reponame).values_list('url', flat=True)[0]
    from mercurial.ui import ui as _ui
    from mercurial.hg import repository
    ui = _ui()
    repo = repository(ui, repopath)
    ctx1 = repo.changectx(request.GET['from'])
    ctx2 = repo.changectx(request.GET['to'])
    match = None # maybe get something from l10n.ini and cmdutil
    changed, added, removed = repo.status(ctx1, ctx2, match=match)[:3]
    diffs = DataTree(dict)
    for path in added:
        diffs[path].update({'path': path,
                            'isFile': True,
                            'rev': request.GET['to'],
                            'desc': ' (File added)',
                            'class': 'added'})
    for path in removed:
        diffs[path].update({'path': path,
                            'isFile': True,
                            'rev': request.GET['from'],
                            'desc': ' (File removed)',
                            'class': 'removed'})
    for path in changed:
        lines = []
        try:
            p = getParser(path)
        except UserWarning:
            diffs[path].update({'path': path,
                                'lines': [{'class': 'issue',
                                           'oldval': '',
                                           'newval': '',
                                           'entity': 'cannot parse ' + path}]})
            continue
        data1 = ctx1.filectx(path).data()
        data2 = ctx2.filectx(path).data()
        try:
            # parsing errors or such can break this, catch those and fail
            # gracefully
            # fake reading with universal line endings, too
            p.readContents(__universal_le(data1))
            a_entities, a_map = p.parse()
            p.readContents(__universal_le(data2))
            c_entities, c_map = p.parse()
            del p
        except:
            diffs[path].update({'path': path,
                                'lines': [{'class': 'issue',
                                           'oldval': '',
                                           'newval': '',
                                           'entity': 'cannot parse ' + path}]})
            continue
        a_list = sorted(a_map.keys())
        c_list = sorted(c_map.keys())
        ar = AddRemove()
        ar.set_left(a_list)
        ar.set_right(c_list)
        for action, item_or_pair in ar:
            if action == 'delete':
                lines.append({'class': 'removed',
                              'oldval': [{'value':a_entities[a_map[item_or_pair]].val}],
                              'newval': '',
                              'entity': item_or_pair})
            elif action == 'add':
                lines.append({'class': 'added',
                              'oldval': '',
                              'newval':[{'value': c_entities[c_map[item_or_pair]].val}],
                              'entity': item_or_pair})
            else:
                oldval = a_entities[a_map[item_or_pair[0]]].val
                newval = c_entities[c_map[item_or_pair[1]]].val
                if oldval == newval:
                    continue
                sm = SequenceMatcher(None, oldval, newval)
                oldhtml = []
                newhtml = []
                for op, o1, o2, n1, n2 in sm.get_opcodes():
                    if o1 != o2:
                        oldhtml.append({'class':op, 'value':oldval[o1:o2]})
                    if n1 != n2:
                        newhtml.append({'class':op, 'value':newval[n1:n2]})
                lines.append({'class':'changed',
                              'oldval': oldhtml,
                              'newval': newhtml,
                              'entity': item_or_pair[0]})
        container_class = lines and 'file' or 'empty-diff'
        diffs[path].update({'path': path,
                            'class': container_class,
                            'lines': lines})
    diffs = diffs.toJSON().get('children', [])
    return render_to_response('shipping/diff.html',
                              {'given_title': request.GET.get('title', None),
                               'repo': reponame,
                               'repo_url': repo_url,
                               'old_rev': request.GET['from'],
                               'new_rev': request.GET['to'],
                               'diffs': diffs})


def dashboard(request):
    args = [] # params to pass to l10nstats json
    query = [] # params to pass to shipping json
    subtitles = []
    if 'ms' in request.GET:
        mstone = get_object_or_404(Milestone, code=request.GET['ms'])
        args.append(('tree', mstone.appver.tree.code))
        subtitles.append(str(mstone))
        query.append(('ms', mstone.code))
    elif 'av' in request.GET:
        appver = get_object_or_404(AppVersion, code=request.GET['av'])
        args.append(('tree', (appver.tree is not None and appver.tree.code)
                     or appver.lasttree.code))
        subtitles.append(str(appver))
        query.append(('av', appver.code))

    # sanitize the list of locales to those that are actually on the dashboard
    locales = Locale.objects.filter(code__in=request.GET.getlist('locale'))
    locales = locales.values_list('code', flat=True)
    args += [("locale", loc) for loc in locales]
    query += [("locale", loc) for loc in locales]
    subtitles += list(locales)

    return render_to_response('shipping/dashboard.html', {
            'subtitles': subtitles,
            'query': mark_safe(urlencode(query)),
            'args': mark_safe(urlencode(args)),
            }, context_instance=RequestContext(request))

@cache_control(max_age=60)
def l10n_changesets(request):
    if request.GET.has_key('ms'):
        av_or_m = get_object_or_404(Milestone, code=request.GET['ms'])
    elif request.GET.has_key('av'):
        av_or_m = get_object_or_404(AppVersion, code=request.GET['av'])
    else:
        return HttpResponse('No milestone or appversion given')

    sos = _signoffs(av_or_m).annotate(tip=Max('push__changesets__id'))
    tips = dict(sos.values_list('locale__code', 'tip'))
    revmap = dict(Changeset.objects.filter(id__in=tips.values()).values_list('id', 'revision'))
    r = HttpResponse(('%s %s\n' % (l, revmap[tips[l]][:12])
                      for l in sorted(tips.keys())),
                     content_type='text/plain; charset=utf-8')
    r['Content-Disposition'] = 'inline; filename=l10n-changesets'
    return r

@cache_control(max_age=60)
def shipped_locales(request):
    if request.GET.has_key('ms'):
        av_or_m = get_object_or_404(Milestone, code=request.GET['ms'])
    elif request.GET.has_key('av'):
        av_or_m = get_object_or_404(AppVersion, code=request.GET['av'])
    else:
        return HttpResponse('No milestone or appversion given')

    sos = _signoffs(av_or_m).values_list('locale__code', flat=True)
    locales = list(sos) + ['en-US']
    def withPlatforms(loc):
        if loc == 'ja':
            return 'ja linux win32\n'
        if loc == 'ja-JP-mac':
            return 'ja-JP-mac osx\n'
        return loc + '\n'

    r = HttpResponse(map(withPlatforms, sorted(locales)),
                      content_type='text/plain; charset=utf-8')
    r['Content-Disposition'] = 'inline; filename=shipped-locales'
    return r

@cache_control(max_age=60)
def signoff_json(request):
    appvers = AppVersion.objects
    if request.GET.has_key('ms'):
        av_or_m = get_object_or_404(Milestone, code=request.GET['ms'])
        appvers = appvers.filter(app=av_or_m.appver.app)
        given_app = av_or_m.appver.app.code
    elif request.GET.has_key('av'):
        av_or_m = get_object_or_404(AppVersion, code=request.GET['av'])
        appvers = appvers.filter(app=av_or_m.app)
        given_app = av_or_m.app.code
    else:
        av_or_m = given_app = None
        appvers = appvers.exclude(tree__isnull=True)
    tree2av = dict(AppVersion.objects.values_list("tree__code","code"))
    tree2app = dict(AppVersion.objects.values_list("tree__code", "app__code"))
    locale = request.GET.get('locale', None)
    lsd = _signoffs(av_or_m, getlist=True, locale=locale)
    items = defaultdict(list)
    values = dict(Action._meta.get_field('flag').flatchoices)
    for k, sol in lsd.iteritems():
        items[k] = [values[so] for so in sol]
    # get shipped-in data, latest milestone of all appversions for now
    shipped_in = defaultdict(list)
    for _av in appvers:
        try:
            _ms = _av.milestone_set.filter(status=2).order_by('-pk')[0]
        except IndexError:
            continue
        app = _av.app.code
        _sos = _ms.signoffs
        if locale is not None:
            _sos = _sos.filter(locale__code=locale)
        for loc in _sos.values_list('locale__code', flat=True):
            shipped_in[(app, loc)].append(_av.code)
    # make a list now
    items = [{"type": "SignOff",
              "label": "%s/%s" % (tree,locale),
              "tree": tree,
              "apploc" : ("%s::%s" % (given_app or tree2app[tree], locale)),
              "signoff": list(values)}
             for (tree, locale), values in items.iteritems()]
    items += [{"type": "Shippings",
               "label": "%s::%s" % (av,locale),
               "shipped": stones}
              for (av, locale), stones in shipped_in.iteritems()]
    items += [{"type": "AppVer4Tree",
               "label": tree,
               "appversion": av}
              for tree, av in tree2av.iteritems()]
    return HttpResponse(simplejson.dumps({'items': items}, indent=2),
                        mimetype="text/plain")


def milestones(request):
    """Administrate milestones.

    Opens an exhibit that offers the actions below depending on
    milestone status and user permissions.
    """
    # we need to use {% url %} with an exhibit {{.foo}} as param,
    # fake { and } to be safe in urllib.quote, which is what reverse
    # calls down the line.
    if '{' not in urllib.always_safe:
        always_safe = urllib.always_safe
        urllib.always_safe = always_safe + '{}'
    else:
        always_safe = None
    r =  render_to_response('shipping/milestones.html',
                            {'login_form_needs_reload': True,
                             'request': request,
                             },
                            context_instance=RequestContext(request))
    if always_safe is not None:
        urllib.always_safe = always_safe
    return r

@cache_control(max_age=60)
def stones_data(request):
    """JSON data to be used by milestones
    """
    latest = defaultdict(int)
    items = []
    stones = Milestone.objects.order_by('-pk').select_related('appver__app')
    maxage = 5
    for stone in stones:
        age = latest[stone.appver.id]
        if age >= maxage:
            continue
        latest[stone.appver.id] += 1
        items.append({'label': str(stone),
                      'appver': str(stone.appver),
                      'status': stone.status,
                      'code': stone.code,
                      'age': age})

    return HttpResponse(simplejson.dumps({'items': items}, indent=2))

def open_mstone(request):
    """Open a milestone.

    Only available to POST, and requires signoff.can_open permissions.
    Redirects to milestones().
    """
    if (request.method == "POST" and
        'ms' in request.POST and
        request.user.has_perm('shipping.can_open')):
        try:
            mstone = Milestone.objects.get(code=request.POST['ms'])
            mstone.status = 1
            # XXX create event
            mstone.save()
        except:
            pass
    return HttpResponseRedirect(reverse('shipping.views.milestones'))

def clear_mstone(request):
    """Clear a milestone, reset all sign-offs.

    Only available to POST, and requires signoff.can_open permissions.
    Redirects to dasboard() for the milestone.
    """
    if (request.method == "POST" and
        'ms' in request.POST and
        request.user.has_perm('shipping.can_open')):
        try:
            mstone = Milestone.objects.get(code=request.POST['ms'])
            if mstone.status is 2:
                return HttpResponseRedirect(reverse('shipping.views.milestones'))
            # get all signoffs, independent of state, and file an obsolete
            # action
            for so in _signoffs(mstone, status=None):
                so.action_set.create(flag=4, author=request.user)
            return HttpResponseRedirect(reverse('shipping.views.dashboard')
                                        + "?ms=" + mstone.code)
        except:
            pass
    return HttpResponseRedirect(reverse('shipping.views.milestones'))


def _propose_mstone(mstone):
    """Propose a new milestone based on an existing one.

    Tries to find the last integer in name and version, increment that
    and create a new milestone.
    """
    last_int = re.compile('(\d+)$')
    name_m = last_int.search(mstone.name)
    if name_m is None:
        return None
    code_m = last_int.search(mstone.code)
    if code_m is None:
        return None
    name_int = int(name_m.group())
    code_int = int(code_m.group())
    if name_int != code_int:
        return None
    new_rev = str(name_int + 1)
    return dict(code=last_int.sub(new_rev, mstone.code),
                name=last_int.sub(new_rev, mstone.name),
                appver=mstone.appver.code)


def confirm_ship_mstone(request):
    """Intermediate page when shipping a milestone.

    Gathers all data to verify when shipping.
    Ends up in ship_mstone if everything is fine.
    Redirects to milestones() in case of trouble.
    """
    if not ("ms" in request.GET):
        return HttpResponseRedirect(reverse('shipping.views.milestones'))
    try:
        mstone = Milestone.objects.get(code=request.GET['ms'])
    except Milestone.DoesNotExist:
        raise Http404("milestone does not exist")
    except:
        return HttpResponseRedirect(reverse('shipping.views.milestones'))
    if mstone.status != 1:
        return HttpResponseRedirect(reverse('shipping.views.milestones'))
    statuses = _signoffs(mstone, getlist=True)
    pending_locs = []
    good = 0
    for (tree, loc), flags in statuses.iteritems():
        if 0 in flags:
            # pending
            pending_locs.append(loc)
        if 1 in flags:
            # good
            good += 1
    pending_locs.sort()
    return render_to_response('shipping/confirm-ship.html',
                              {'mstone': mstone,
                               'pending_locs': pending_locs,
                               'good': good,
                               'login_form_needs_reload': True,
                               'request': request,
                             },
                              context_instance=RequestContext(request))

def ship_mstone(request):
    """The actual worker method to ship a milestone.

    Redirects to milestones().
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not request.user.has_perm('shipping.can_ship'):
        # XXX: personally I'd prefer if this was a raised 4xx error (peter)
        # then I can guarantee better test coverage
        return HttpResponseRedirect(reverse('shipping.views.milestones'))

    mstone = get_object_or_404(Milestone, code=request.POST['ms'])
    # get current signoffs
    cs = _signoffs(mstone).values_list('id', flat=True)
    mstone.signoffs.add(*list(cs))  # add them
    mstone.status = 2
    # XXX create event
    mstone.save()

    return HttpResponseRedirect(reverse('shipping.views.milestones'))


def confirm_drill_mstone(request):
    """Intermediate page when fire-drilling a milestone.

    Gathers all data to verify when shipping.
    Ends up in drill_mstone if everything is fine.
    Redirects to milestones() in case of trouble.
    """
    if not ("ms" in request.GET and
            request.user.has_perm('shipping.can_ship')):
        return HttpResponseRedirect(reverse('shipping.views.milestones'))
    try:
        mstone = Milestone.objects.get(code=request.GET['ms'])
    except:
        return HttpResponseRedirect(reverse('shipping.views.milestones'))
    if mstone.status != 1:
        return HttpResponseRedirect(reverse('shipping.views.milestones'))

    drill_base = Milestone.objects.filter(appver=mstone.appver,status=2).order_by('-pk').select_related()
    proposed = _propose_mstone(mstone)

    return render_to_response('shipping/confirm-drill.html',
                              {'mstone': mstone,
                               'older': drill_base[:3],
                               'proposed': proposed,
                               'login_form_needs_reload': True,
                               'request': request,
                               },
                              context_instance=RequestContext(request))

def drill_mstone(request):
    """The actual worker method to ship a milestone.

    Only avaible to POST.
    Redirects to milestones().
    """
    if (request.method == "POST" and
        'ms' in request.POST and
        'base' in request.POST and
        request.user.has_perm('shipping.can_ship')):
        try:
            mstone = Milestone.objects.get(code=request.POST['ms'])
            base = Milestone.objects.get(code=request.POST['base'])
            so_ids = list(base.signoffs.values_list('id', flat=True))
            mstone.signoffs = so_ids  # add signoffs of base ms
            mstone.status = 2
            # XXX create event
            mstone.save()
        except Exception, e:
            pass
    return HttpResponseRedirect(reverse('shipping.views.milestones'))


def _signoffs(appver_or_ms=None, status=1, getlist=False, locale=None):
    '''Get the signoffs for a milestone, or for the appversion as
    queryset (or manager).
    By default, returns the accepted ones, which can be overwritten to
    get any (status=None) or a particular status.

    If the locale argument is given, return the latest signoff with the
    requested status, or None. Requires appver_or_ms to be given.

    If getlist=True is specified, returns a dictionary mapping
    tree-locale typles to a list of statuses, all that are newer than the
    latest obsolete action or accepted signoff (the latter is included).
    '''
    if isinstance(appver_or_ms, Milestone):
        ms = appver_or_ms
        if ms.status==2:
            assert not getlist
            if locale is not None:
                try:
                    return ms.signoffs.get(locale__code=locale)
                except Signoff.DoesNotExist:
                    return None
            return ms.signoffs
        appver = ms.appver
    else:
        appver = appver_or_ms

    sos = Signoff.objects
    if appver is not None:
        sos = sos.filter(appversion=appver)
    if locale is not None:
        sos = sos.filter(locale__code=locale)
    sos = sos.annotate(latest_action=Max('action__id'))
    sos_vals = list(sos.values('locale__code','id','latest_action', 'appversion__tree__code'))
    actions = Action.objects
    actionflags=dict(actions.filter(id__in=map(lambda d: d['latest_action'],
                                               sos_vals)).values_list('id','flag'))
    actionflags[0] = 0 # migrated pending signoffs lack any action :-(
    if getlist:
        lf = defaultdict(list)
    else:
        lf = dict()
    for d in sos_vals:
        loc = d['locale__code']
        tree = d['appversion__tree__code']
        flag = actionflags[d['latest_action'] or 0]
        if flag == 4 and status != 4:
            # obsoleted, drop previous signoffs
            lf.pop((tree,loc), None)
        else:
            if getlist:
                if flag == 1:
                    # approved, forget previous
                    lf[(tree,loc)] = [flag]
                else:
                    lf[(tree,loc)].append(flag)
            else:
                if status is not None:
                    if flag == status:
                        lf[(tree,loc)] = d['id']
                else:
                    lf[(tree,loc)] = d['id']

    if getlist:
        if locale is not None:
            for tree, loc in lf.iterkeys():
                if loc != locale:
                    lf.pop((tree,loc))
        return lf
    if locale is not None:
        assert appver
        try:
            return sos.get(id=lf[(appver.tree.code,locale)])
        except KeyError:
            return None
    return sos.filter(id__in=lf.values())
