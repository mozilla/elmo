from django import template
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape
from django.core.urlresolvers import reverse

register = template.Library()

templates_stack = []

@register.tag(name="recurse_children")
def do_recurse(parser, token):
    nodelist = parser.create_nodelist()
    templates_stack.append(nodelist)
    nodelist += parser.parse(('endrecurse', ))
    templates_stack.pop()
    node = RecurseNode(nodelist)
    parser.delete_first_token()
    return node

class RecurseNode(template.Node):
    def __init__(self, nodelist):
        self._nodelist = nodelist
    def render(self, context):
        output = self._nodelist.render(context)
        return output

@register.tag(name="recurse")
def do_depth(parser, token):
    tag_name, nodes, _as, varname = token.split_contents()
    return DepthNode(nodes, varname)

class DepthNode(template.Node):
    def __init__(self, nodes, varname):
        self.vals = template.Variable(nodes)
        self.varname = varname
        self._nodelist = templates_stack[-1]
    def render(self, context):
        nodes = self.vals.resolve(context)
        d = context.push()
        d[self.varname] = nodes
        content = self._nodelist.render(context)
        context.pop()
        return content
