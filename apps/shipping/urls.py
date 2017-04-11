# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''URL mappings for the shipping app.
'''
from __future__ import absolute_import

from django.conf.urls import url

from . import views
from .views import status, app, signoff, release

urlpatterns = [
    url(r'^/?$', views.index, name='select-dashboard'),
    url(r'^/drivers$', views.Drivers.as_view(), name='shipping-drivers'),
    url(r'^/dashboard/?$', views.dashboard),
]

urlpatterns += [
    url(r'^/l10n-changesets$', status.Changesets.as_view(),
        name='shipping-l10n_changesets'),
    url(r'^/json-changesets$', status.JSONChangesets.as_view(),
        name='shipping-json_changesets'),
    url(r'^/shipped-locales$', status.ShippedLocales.as_view(),
        name='shipping-shipped_locales'),
    url(r'^/api/status$', status.StatusJSON.as_view(),
        name='shipping-status_json'),
]

urlpatterns += [
    url(r'^/app/locale-changes/(.*)', app.changes,
        name='shipping-appversion-history'),
]

urlpatterns += [
    url(r'^/signoffs/(.*)/(.*)/more/$', signoff.SignoffRowsView.as_view(),
        name='shipping-signoff-rows'),
    url(r'^/signoffs/(.*)/$', signoff.signoff_locale),
    url(r'^/signoffs/(.*?)/(.*)', signoff.SignoffView.as_view(),
        name='shipping-signoff'),
    url(r'^/signoffs-details/(.*?)/(.*)', signoff.signoff_details,
        name='shipping-signoff_details'),
    url(r'^/add-signoff/(.*?)/(.*)', signoff.add_signoff),  # POST only
    url(r'^/review-signoff/(.*?)/(.*)', signoff.review_signoff),  # POST only
    url(r'^/cancel-signoff/(.*?)/(.*)', signoff.cancel_signoff),  # POST only
    url(r'^/reopen-signoff/(.*?)/(.*)', signoff.reopen_signoff),  # POST only
]

urlpatterns += [
    url(r'^/release/$', release.select_appversions),
    url(r'^/release/migrate$', release.MigrateAppversions.as_view(),
        name='shipping-release-migrate'),  # POST only
]
