# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

'''URL mappings for the shipping app.
'''

from django.conf.urls import patterns

urlpatterns = patterns('shipping.views',
    (r'^/?$', 'index'),
    (r'^/dashboard/?$', 'dashboard'),
    (r'^/milestones$', 'milestones'),
    (r'^/stones-data$', 'stones_data'),
    (r'^/open-mstone$', 'open_mstone'),
    (r'^/confirm-ship$', 'confirm_ship_mstone'),
    (r'^/confirm-drill$', 'confirm_drill_mstone'),
    (r'^/drill$', 'drill_mstone'),
    (r'^/ship$', 'ship_mstone'),
)

urlpatterns += patterns('shipping.views.status',
    (r'^/l10n-changesets$', 'l10n_changesets'),
    (r'^/shipped-locales$', 'shipped_locales'),
    (r'^/api/status$', 'status_json'),
)

urlpatterns += patterns('shipping.views.outreach',
    (r'^/outreach/$', 'select_apps'),
    (r'^/outreach/data$', 'data'),
)

urlpatterns += patterns('shipping.views.milestone',
    (r'^/about-milestone/(.*)', 'about'),
    (r'^/milestone-statuses/(.*)', 'statuses'),
    (r'^/json-changesets$', 'json_changesets'),
)

urlpatterns += patterns('shipping.views.app',
    (r'^/app/locale-changes/(.*)', 'changes'),
)

urlpatterns += patterns('shipping.views.signoff',
    (r'^/signoffs/(.*)/(.*)/more/$', 'signoff_rows'),
    (r'^/signoffs/(.*)/$', 'signoff_locale'),
    (r'^/signoffs/(.*?)/(.*)', 'signoff'),
    (r'^/signoffs-details/(.*?)/(.*)', 'signoff_details'),
    (r'^/add-signoff/(.*?)/(.*)', 'add_signoff'),  # POST only
    (r'^/review-signoff/(.*?)/(.*)', 'review_signoff'),  # POST only
    (r'^/cancel-signoff/(.*?)/(.*)', 'cancel_signoff'),  # POST only
    (r'^/reopen-signoff/(.*?)/(.*)', 'reopen_signoff'),  # POST only
)

urlpatterns += patterns('shipping.views.release',
    (r'^/release/$', 'select_appversions'),
    (r'^/release/migrate$', 'migrate_appversions'),  # POST only
    (r'^/release/select-milestones/$', 'selectappversions4milestones'),
    (r'^/release/create-milestones/$', 'create_milestones'),  # POST only
)
