# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''Views of privacy policies and their history.
'''
from __future__ import absolute_import

from django.core.urlresolvers import reverse
from django.db.models import Count
from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404
from django.http import (HttpResponseRedirect,
                         HttpResponseForbidden, Http404)
from django.utils.encoding import force_unicode
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE
from privacy.models import Policy, Comment

# We're not using the permission decorators from django.contrib.auth here
# because we don't have a login-view for one, and it's not giving
# us the flexibility to not use those.


def show_policy(request, id=None):
    """Display the currently active policy, or, if id is given, the
    specified policy.
    """
    try:
        if id is None:
            p = Policy.objects.get(active=True)
        else:
            p = Policy.objects.get(id=int(id))
    except:
        p = None
    if p is not None and p.active:
        logs = LogEntry.objects.filter(content_type=Policy.contenttype())
        logs = logs.filter(object_id=p.id,
                           action_flag=CHANGE,
                           change_message='activate')
        logs = logs.order_by('-action_time')
        activation = logs.values_list('action_time', flat=True)[0]
    else:
        activation = None
    c = {"policy": p, "activation": activation}
    return render(request, 'privacy/show-policy.html', c)


def versions(request):
    """Show all policies including their active times.

    If the user has permissions, offers to activate a policy, comment, or
    create a new policy.
    """
    policies = Policy.objects.order_by('-pk')
    policies = policies.annotate(noc=Count('comments'))
    policies = policies.prefetch_related('comments')
    los = LogEntry.objects.filter(content_type=Policy.contenttype())
    details = {}
    for lo in los.order_by('action_time'):
        if lo.object_id not in details:
            detail = {}
            details[lo.object_id] = detail
        else:
            detail = details[lo.object_id]
        if lo.action_flag == ADDITION:
            detail['created'] = lo.action_time
        elif lo.action_flag == CHANGE:
            if lo.change_message not in ('deactivate', 'activate'):
                continue
            if 'active_time' not in detail:
                detail['active_time'] = []
            if lo.change_message == 'activate':
                detail['active_time'].append([lo.action_time])
            else:
                detail['active_time'][-1].append(lo.action_time)

    def do_policies(_pols, _details):
        for _p in _pols:
            _d = _p.__dict__.copy()
            _d.update(_details[str(_p.id)])
            _d['comments'] = _p.comments.all()
            yield _d
    c = {"policies": do_policies(policies, details)}
    return render(request, 'privacy/versions.html', c)


def add_policy(request):
    """Add a new policy.

    This handles GET and POST, POST defers to post_policy for the
    actual creation handling.
    """
    if request.method == "POST":
        return post_policy(request)
    try:
        current = Policy.objects.get(active=True).text
    except:
        current = ''
    return render(request, 'privacy/add.html', {'current': current})


def post_policy(request):
    if not (request.user.has_perm('privacy.add_policy')
            and request.user.has_perm('privacy.add_comment')):
        return HttpResponseForbidden("not sufficient permissions")
    p = Policy.objects.create(text=request.POST['content'])
    c = Comment.objects.create(text=request.POST['comment'],
                               policy=p,
                               who=request.user)
    LogEntry.objects.log_action(request.user.id,
                                Policy.contenttype().id, p.id,
                                force_unicode(p), ADDITION)
    LogEntry.objects.log_action(request.user.id,
                                Comment.contenttype().id, c.id,
                                force_unicode(c), ADDITION)

    return redirect(reverse('privacy.views.show_policy',
                            kwargs={'id': p.id}))


def activate_policy(request):
    """Activate a selected policy, requires privacy.activate_policy
    priviledges.
    """
    if not request.user.has_perm('privacy.activate_policy'):
        return HttpResponseRedirect(reverse('privacy.views.versions'))
    if request.method == "POST":
        try:
            policy = get_object_or_404(Policy, id=request.POST['active'])
        except ValueError:
            # not a valid ID
            raise Http404
        if not policy.active:
            # need to change active policy, first, deactivate existing
            # actives, then set the new one active. And create LogEntries.
            qa = Policy.objects.filter(active=True)
            for _p in qa:
                LogEntry.objects.log_action(request.user.id,
                                            Policy.contenttype().id, _p.id,
                                            force_unicode(_p), CHANGE,
                                            change_message="deactivate")
            qa.update(active=False)
            LogEntry.objects.log_action(request.user.id,
                                        Policy.contenttype().id, policy.id,
                                        force_unicode(policy), CHANGE,
                                        change_message="activate")
            policy.active = True
            policy.save()
    return HttpResponseRedirect(reverse('privacy.views.versions'))


def add_comment(request):
    """Add a comment to a policy, requires privacy.add_comment
    priviledges.
    """
    if not request.user.has_perm('privacy.add_comment'):
        return HttpResponseForbidden("not sufficient permissions")
    if request.method == "POST":
        try:
            p = get_object_or_404(Policy, id=request.POST['policy'])
        except ValueError:
            raise Http404
        c = Comment.objects.create(text=request.POST['comment'],
                                   policy=p,
                                   who=request.user)
        LogEntry.objects.log_action(request.user.id,
                                    Comment.contenttype().id, c.id,
                                    force_unicode(c), ADDITION)
    return redirect(reverse('privacy.views.versions'))
