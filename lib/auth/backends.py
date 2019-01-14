# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import absolute_import
from __future__ import unicode_literals

from django.contrib.auth.models import Group
from django.conf import settings

from mozilla_django_oidc.auth import OIDCAuthenticationBackend


MAPPING = {
    'active_scm_l10n': 'Localizers'
}
MAPPED_GROUPS = set(MAPPING.values())


class ElmoOIDCBackend(OIDCAuthenticationBackend):
    def create_user(self, claims):
        user = super(ElmoOIDCBackend, self).create_user(claims)
        return self.update_user(user, claims)

    def update_user(self, user, claims):
        update_fields = []
        if 'family_name' in claims and user.last_name != claims['family_name']:
            update_fields.append('last_name')
            user.last_name = claims['family_name']
        if 'given_name' in claims and user.first_name != claims['given_name']:
            update_fields.append('first_name')
            user.first_name = claims['given_name']
        if update_fields:
            user.save(update_fields=update_fields)
        self.update_groups(user, claims)
        return user

    def update_groups(self, user, claims):
        claimed_group_names = set()
        for c_group in claims.get(settings.SSO_GROUPS, []):
            if c_group in MAPPING:
                claimed_group_names.add(MAPPING[c_group])
        db_groups = set(user.groups.values_list('name', flat=True))
        if (db_groups & MAPPED_GROUPS) == claimed_group_names:
            # we're good, no groups to change
            return
        # keep db-only groups
        group_names = db_groups - MAPPED_GROUPS
        # add dino-park groups
        group_names |= claimed_group_names
        user.groups.set(
            Group.objects.filter(name__in=group_names)
        )
