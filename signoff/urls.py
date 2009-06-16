from django.conf.urls.defaults import *

urlpatterns = patterns('signoff.views',
    (r'^\/?$', 'milestone_list'),
    (r'^\/api\/pushes$', 'get_api_items'),
    (r'^\/milestones\/([^/]+)\/l10n-changesets$', 'l10n_changesets'),
    (r'^\/milestones\/([^/]+)\/shipped-locales$', 'shipped_locales'),
    (r'^\/locales\/?$', 'locale_list'),
    (r'^\/locales\/(?P<loc>[^\/]+)', 'milestone_list'),
    (r'^\/milestones\/?$', 'dashboard'),
    (r'^\/milestones\/(?P<ms>[^/]+)$', 'dashboard'),
    (r'^\/milestones\/([^/]+)/dashboard$', 'dashboard'),
    (r'^\/milestones\/([^/]+)/json$', 'json'),
    (r'^\/(?P<arg>[^\/]+)?\/(?P<arg2>[^\/]+)?$', 'sublist'),
)
