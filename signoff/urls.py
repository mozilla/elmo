from django.conf.urls.defaults import *

urlpatterns = patterns('signoff.views',
    (r'^\/?$', 'index'),
    (r'^\/test$', 'dstest'),
    (r'^\/milestones\/([^/]+)\/l10n-changesets$', 'l10n_changesets'),
    (r'^\/milestones\/([^/]+)\/shipped-locales$', 'shipped_locales'),
    (r'^\/locales\/?$', 'locale_list'),
    (r'^\/locales\/(?P<loc>[^\/]+)', 'milestone_list'),
    (r'^\/milestones\/?$', 'milestone_list'),
    (r'^\/milestones\/(?P<ms>[^/]+)$', 'locale_list'),
    (r'^\/milestones\/([^/]+)/dashboard$', 'dashboard'),
    (r'^\/milestones\/([^/]+)/json$', 'json'),
    (r'^\/(?P<arg>[^\/]+)?\/(?P<arg2>[^\/]+)?$', 'sublist'),
)
