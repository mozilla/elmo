from datetime import datetime, timedelta

from django.http import HttpResponse
from django.template import Context, loader
from django.shortcuts import render_to_response, get_object_or_404
import simplejson as json

from pushes.models import *

def repostatus(request):
    json_template = {'properties': 
                     {'lastpush': {'valueType': 'date'}}
                     }
    admins = [u'axel@mozilla.com', u'gozer@mozillamessaging.com', u'ffxbld',
              u'zbraniecki@mozilla.com']
    ignores = ['l10n-central/' + loc for loc in 
               'en-ZA hy-AM nr nso ss st tn ts ve xh zu x-testing'.split()]
    l10n_repos = Repository.objects.filter(name__contains = 'l10n-central')
    l10n_repos = l10n_repos.exclude(name__in = ignores).order_by('name')
    now = datetime.utcnow()
    items = []
    users = {}
    for name, user in Push.objects.filter(repository__in = l10n_repos).exclude(user__in = admins).values_list('repository__name', 'user').distinct():
        name = name[13:]
        if not name in users:
            users[name] = [user]
        else:
            users[name].append(user)
    for userlist in users.values():
        userlist.sort()
    for r in l10n_repos:
        #users = sorted(r.push_set.exclude(user__in=admins).values_list('user', flat=True).distinct())
        lastpush = None
        if r.push_set.count():
            lastpush = r.push_set.order_by('-pk')[0].push_date
            # lastpush = now - r.push_set.order_by('-pk')[0].push_date
            # lastpush = timedelta(lastpush.days, 
            #                      (lastpush.seconds / 60) * 60)
        name = r.name[13:]
        try:
            userlist = users[name]
        except KeyError:
            userlist = []
        items.append({'label': name, 'users': userlist, 
                           'lastpush': lastpush})
    if 'json' in request.GET:
        for item in items:
            if item['lastpush'] is None:
                item.pop('lastpush')
            else:
                item['lastpush'] = item['lastpush'].isoformat('T') + 'Z'
            if not item['users']:
                item.pop('users')
            item['type'] = 'PushInfo'
        json_template['items'] = items
        return HttpResponse(json.dumps(json_template, indent=2),
                            mimetype="text/plain")
    t = loader.get_template('status/repos.html')
    c = Context({
            'items': items
            })
    return HttpResponse(t.render(c))
