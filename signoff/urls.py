from django.conf.urls.defaults import *

urlpatterns = patterns('signoff.views',
    (r'^\/?$', 'index'),
    (r'^\/pushes\/?$', 'pushes'),
    (r'^\/dashboard\/?$', 'dashboard'),
    (r'^\/milestones\/([^/]+)\/l10n-changesets$', 'l10n_changesets'),
    (r'^\/milestones\/([^/]+)\/shipped-locales$', 'shipped_locales'),
    (r'^\/api\/pushes$', 'pushes_json'),
    (r'^\/api\/signoffs$', 'signoff_json'),
    (r'^\/diff$', 'diff_app'),
)
