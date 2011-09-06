from django.conf.urls.defaults import patterns

urlpatterns = patterns('pushes.views',
                       (r'^pushes/(?P<repo_name>.+)?$', 'pushlog'),
                       (r'^diff$', 'diff'),
)
