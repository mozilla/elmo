# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django.shortcuts import get_object_or_404
from django.shortcuts import render
from webby.models import Project, Weblocale
from django.http import HttpResponseRedirect
from life.models import Locale
from django import forms
from django.contrib.admin.models import LogEntry, ADDITION
from django.contrib.contenttypes.models import ContentType

from itertools import groupby


class AddLocaleForm(forms.Form):
    locale = forms.CharField()


def projects(request):
    projects = Project.objects.active().order_by('name')
    if request.user.has_perm('webby.change_weblocale'):
        weblocales = Weblocale.objects.order_by('project')
        pending_optins = weblocales.filter(requestee__isnull=False,
                                           in_verbatim=False,
                                           in_vcs=False)
        # group pending_optins by the id of the project they're related to
        project_optins = {}
        for pid, p_optins in groupby(pending_optins, lambda x: x.project_id):
            project_optins[pid] = list(p_optins)
        for project in projects:
            try:
                project.pending_count = len(project_optins[project.id])
            except KeyError:
                project.pending_count = 0
    return render(request, 'webby/projects.html', {
                    'projects': projects,
                    'login_form_needs_reload': True,
                  })


def project(request, slug):
    project = get_object_or_404(Project, slug=slug)
    if request.method == 'POST' and not project.is_archived:
        form = AddLocaleForm(request.POST)
        if form.is_valid() and request.user.has_perm('webby.add_weblocale'):
            lcode = form.cleaned_data['locale']
            locale = Locale.objects.get(code=lcode)
            wlobj = Weblocale(locale=locale,
                              project=project,
                              requestee=request.user)
            wlobj.save()
            LogEntry.objects.log_action(
                user_id=request.user.pk,
                content_type_id=ContentType.objects.get_for_model(wlobj).pk,
                object_id=wlobj.pk,
                object_repr=unicode(wlobj),
                action_flag=ADDITION
            )
            return HttpResponseRedirect('')
        else:
            return HttpResponseRedirect('')
    else:
        form = AddLocaleForm()

    locales = Weblocale.objects.filter(project=project) \
                               .order_by('locale__name')
    new_locales = Locale.objects \
                        .exclude(id__in=project.locales.values_list('id')) \
                        .order_by('code') if not project.is_archived else []

    return render(request, 'webby/project.html', {
                    'project': project,
                    'locales': locales,
                    'new_locales': new_locales,
                    'form': form,
                    'login_form_needs_reload': True,
                  })
