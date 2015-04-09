import re
import os

from django.conf import settings
import elmo.test



class MigrationTests(elmo.test.TestCase):
    """Sanity checks for the SQL migration scripts."""

    @staticmethod
    def _migrations_path(app_path):
        """Return the absolute path to the migration script folder."""
        return os.path.join(app_path, 'migrations')

    @staticmethod
    def _apps_path():
        """Return the absolute path to the apps folder."""
        return os.path.join(settings.ROOT, 'apps')

    def test_uniques(self):
        """Assert that the numeric prefixes of the DB migrations are unique."""
        # list all apps
        # for each app, check if there's a migrations folder
        # then test for uniqueness in that folder
        path = self._apps_path()
        for app in os.listdir(path):
            app_path = os.path.join(path, app)
            migrations_path = self._migrations_path(app_path)
            if os.path.exists(migrations_path):
                self._test_unique(migrations_path)

    def _test_unique(self, path):
        leading_digits = re.compile(r'^\d+')
        seen_numbers = set()
        for filename in os.listdir(path):
            __, ext = os.path.splitext(filename)
            # prevent matching backup files (e.g. 001_foo.sql~)
            if ext not in [".sql", ".py"]: # same as nashvegas
                continue
            match = leading_digits.match(filename)
            if match:
                number = match.group()
                if number in seen_numbers:
                    self.fail('There is more than one migration #%s in %s.' %
                              (number, path))
                seen_numbers.add(number)
