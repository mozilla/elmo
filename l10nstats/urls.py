from django.conf.urls.defaults import *

urlpatterns = patterns('l10nstats.views',
    (r'^$', 'index'),
    (r'^l10n_status.json$','status_json'),
    (r'__history__.html$', 'exhibit_empty_iframe'),
    (r'^history$', 'history_plot'),
    (r'^tree-status/([^/]+)$', 'tree_progress'),
)
