import re
import os

from django.conf import settings
import test_utils



class MigrationTests(test_utils.TestCase):
    """Sanity checks for the SQL migration scripts."""

    @staticmethod
    def _migrations_path():
        """Return the absolute path to the migration script folder."""
        return os.path.join(settings.ROOT, 'migrations')

    def test_unique(self):
        """Assert that the numeric prefixes of the DB migrations are unique."""
        leading_digits = re.compile(r'^\d+')
        seen_numbers = set()
        path = self._migrations_path()
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
