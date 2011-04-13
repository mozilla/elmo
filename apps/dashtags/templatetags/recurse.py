# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is l10n django site.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

'''Template tags to handle displaying of recursive datastructures.
'''

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
