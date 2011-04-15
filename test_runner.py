import django_nose

class PatchedNoseTestSuiteRunner(django_nose.NoseTestSuiteRunner):

    def run_tests(self, test_labels, extra_tests=None):
        #print "TEST_LABELS"
        #print test_labels
        django_test_labels = [x.replace('apps/','').replace('/','.')
                              for x in test_labels]
        #print django_test_labels
        #print "\n"

        self.build_suite(tuple(django_test_labels), extra_tests)
        #self.build_suite(None, None)

        # Due to this hack of calling build_suite (which is necessary) what
        # happens is that the related objects for some models are incorrectly
        # installed when tests are run. By invoking
        # *._meta.get_all_related_objects() pre-emptively it makes sure that
        # all related objects caches are set correctly before running tests.
        # Without this, it would not be possible to do:
        #    instance = TestModel.objects.get(...)
        #    instance.delete()
        from apps.mbdb.tests import TestingModel, List
        TestingModel._meta.get_all_related_objects()
        List._meta.get_all_related_objects()

        return super(PatchedNoseTestSuiteRunner, self).run_tests(
           test_labels=test_labels, extra_tests=extra_tests)
