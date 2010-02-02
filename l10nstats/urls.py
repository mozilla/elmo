from django.conf.urls.defaults import *

urlpatterns = patterns('l10nstats.views',
    (r'^$', 'index'),
    (r'^l10n_status.json$','status_json'),
    (r'^history$', 'history_plot'),
    (r'^compare$', 'compare', {}, 'compare_locales'),
    (r'^tree-status/([^/]+)$', 'tree_progress'),
    (r'^grid$', 'grid'), # experimental, might not stay
)
