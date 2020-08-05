# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import
from __future__ import unicode_literals

from unittest.mock import patch

from elmo.test import TestCase
from django.contrib.auth.models import Group
from django.conf import settings

from .backends import ElmoOIDCBackend


class OIDCBackendTestCase(TestCase):
    @patch.object(
        ElmoOIDCBackend, 'update_user',
        side_effect=lambda user, claims: user
    )
    def test_create(self, update_user):
        backend = ElmoOIDCBackend()
        claims = {
            'given_name': 'Axel',
            'family_name': 'Hecht',
            'email': 'axel@example.com'
        }
        user = backend.create_user(claims)
        update_user.assert_called_once_with(user, claims)

    @patch.object(
        ElmoOIDCBackend, 'update_groups',
        side_effect=lambda user, claims: None
    )
    def test_no_update(self, update_groups):
        backend = ElmoOIDCBackend()
        claims = {
            'given_name': 'Axel',
            'family_name': 'Hecht',
            'email': 'axel@example.com'
        }
        user = backend.UserModel.objects.create_user(
            backend.get_username(claims),
            claims['email'],
            first_name=claims['given_name'],
            last_name=claims['family_name'],
        )
        with patch.object(user, 'save') as user_save:
            returned_user = backend.update_user(user, claims)
            self.assertEqual(user, returned_user)
            update_groups.assert_called_once_with(user, claims)
            user_save.assert_not_called()

    @patch.object(
        ElmoOIDCBackend, 'update_groups',
        side_effect=lambda user, claims: None
    )
    def test_update_first_name(self, update_groups):
        backend = ElmoOIDCBackend()
        claims = {
            'given_name': 'Axel',
            'family_name': 'Hecht',
            'email': 'axel@example.com'
        }
        user = backend.UserModel.objects.create_user(
            backend.get_username(claims),
            claims['email'],
            first_name=claims['given_name'] + 'do not keep',
            last_name=claims['family_name'],
        )
        with patch.object(user, 'save', return_value=None) as user_save:
            returned_user = backend.update_user(user, claims)
            self.assertEqual(user, returned_user)
            user_save.assert_called_once_with(
                update_fields=['first_name']
            )
        update_groups.assert_called_once_with(user, claims)

    def test_update_groups(self):
        db_group = Group.objects.create(name="just_db")
        l10n_group = Group.objects.get(name="Localizers")
        backend = ElmoOIDCBackend()
        claims = {
            'email': 'axel@example.com'
        }
        user = backend.UserModel.objects.create_user(
            backend.get_username(claims),
            claims['email']
        )
        user.groups.set([db_group, l10n_group])
        # remove group, as we lack claims
        backend.update_groups(user, claims)
        self.assertEqual(
            list(user.groups.values_list('name', flat=True)),
            [db_group.name]
        )
        # no modification needed
        with patch.object(user.groups, 'set') as patched_set:
            backend.update_groups(user, claims)
            patched_set.assert_not_called()
        claims[settings.SSO_GROUPS] = [
            'something_unrelated'
        ]
        user.groups.add(l10n_group)
        backend.update_groups(user, claims)
        self.assertEqual(
            list(user.groups.values_list('name', flat=True)),
            [db_group.name]
        )
        # no modification needed
        with patch.object(user.groups, 'set') as patched_set:
            backend.update_groups(user, claims)
            patched_set.assert_not_called()
        claims[settings.SSO_GROUPS].append(
            'active_scm_l10n'
        )
        # add group
        backend.update_groups(user, claims)
        self.assertEqual(
            list(user.groups.order_by('name').values_list('name', flat=True)),
            [db_group.name, l10n_group.name]
        )
        # no modification needed
        with patch.object(user.groups, 'set') as patched_set:
            backend.update_groups(user, claims)
            patched_set.assert_not_called()
