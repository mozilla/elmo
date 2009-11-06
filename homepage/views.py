'''Views for the main navigation pages.
'''

from django.shortcuts import render_to_response, redirect
from django.utils.safestring import mark_safe

from life.models import Locale


def index(request):
    from signoff.views import homesnippet as signoff_snippet
    from pushes.views import homesnippet as pushes_snippet
    from l10nstats.views import homesnippet as stats_snippet

    signoff_div = mark_safe(signoff_snippet(request))
    pushes_div = mark_safe(pushes_snippet(request))
    l10nstats_div = mark_safe(stats_snippet(request))

    return render_to_response('homepage/index.html', {
            'signoff': signoff_div,
            'pushes': pushes_div,
            'l10nstats': l10nstats_div,
            })

def teams(request):
    locs = Locale.objects.order_by('code')

    return render_to_response('homepage/teams.html', {
            'locales': locs,
            })

def locale_team(request, code):
    try:
        loc = Locale.objects.get(code=code)
    except Locale.DoesNotExist:
        return redirect('homepage.views.teams')

    from l10nstats.views import teamsnippet as stats_snippet

    l10nstats_div = mark_safe(stats_snippet(request, loc))

    name = loc.name or loc.code

    return render_to_response('homepage/locale-team.html', {
            'locale': loc,
            'name': name,
            'l10nstats': l10nstats_div,
            })
