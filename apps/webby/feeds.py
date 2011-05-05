from django.contrib.syndication.views import Feed
from django.core.urlresolvers import reverse

from webby.models import Weblocale

targets = {
    'in_verbatim': 'Verbatim',
    'in_vcs': 'VCS',
    'is_on_stage': 'Stage',
    'is_on_prod': 'Production',
}


class AllOptinsFeed(Feed):
    title = "Webby opt-ins"
    link = "/webby/"
    description = "Webby opt-ins"

    def items(self):
        return Weblocale.objects.order_by('-id')[:10]

    def item_title(self, item):
        return '%s for %s (by %s)' % (item.locale.code,
                                      item.project.name, item.requestee)

    def item_description(self, item):
        elems = []
        for k, v in targets.items():
            if getattr(item, k) is False:
                elems.append(v)
        if elems:
            return 'Missing: %s' % (', '.join(elems))
        else:
            return 'Fully deployed'

    def item_link(self, item):
        return reverse('webby-project', kwargs={'slug': item.project.slug})


class PendingOptinsFeed(AllOptinsFeed):
    title = "Webby pending opt-ins"
    description = "Webby pending opt-ins"

    def items(self):
        return Weblocale.objects.exclude(in_verbatim=True, in_vcs=True). \
                                 order_by('-id')[:10]
