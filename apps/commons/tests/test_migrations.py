import re
from os import listdir
from os.path import join, dirname

import test_utils

import manage


class MigrationTests(test_utils.TestCase):
    """Sanity checks for the SQL migration scripts."""

    @staticmethod
    def _migrations_path():
        """Return the absolute path to the migration script folder."""
        return manage.path('migrations')

    def test_unique(self):
        """Assert that the numeric prefixes of the DB migrations are unique."""
        leading_digits = re.compile(r'^\d+')
        seen_numbers = set()
        path = self._migrations_path()
        for filename in listdir(path):
            match = leading_digits.match(filename)
            if match:
                number = match.group()
                if number in seen_numbers:
                    self.fail('There is more than one migration #%s in %s.' %
                              (number, path))
                seen_numbers.add(number)
