/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is l10n django site.
 *
 * The Initial Developer of the Original Code is
 *   Mozilla Foundation.
 * Portions created by the Initial Developer are Copyright (C) 2010
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *   Peter Bengtsson <peterbe@mozilla.com>
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 *
 * ***** END LICENSE BLOCK ***** */

/* This code depends on two global variables being defined:
   * LOCALE_CODE
   * WEBDASHBOARD_URL
 */

var WebdashboardRSSPuller = (function(code, webdashboard_url) {
  var URL = webdashboard_url + '?rss=1&locale=' + code;
  var parent = $('#webdashboard');

  function render(response) {
    $('.failed:visible', parent).hide();
    $('table:visible', parent).hide();

    var tbody = $('<tbody>');
    $.each(response.getElementsByTagName('item'), function() {
      var tr = $('<tr>').addClass('treesummary');
      var item = $(this);
      var title = $('title', item).text();
      var description = $('description', item).text();
      var link = $('link', item).text();
      $('<a>')
        .attr('href', link)
        .attr('title', description)
        .text(title)
        .appendTo($('<td>').appendTo(tr));

      tbody.append(tr);

    });
    tbody.appendTo($('table', parent));
    $('.loading:visible', parent).hide();
    $('table:hidden', parent).fadeIn(400);

  }

  return {
     pull: function() {
      $.ajax({
        url: URL,
        success: render,
        error: function(jqXHR, textStatus, errorThrown) {
          excuse();
        }
      });
     },
     excuse: function() {
       $('.loading', parent).hide();
       $('table', parent).hide();
       $('.failed', parent).show();
     }
  };

})(LOCALE_CODE, WEBDASHBOARD_URL);


$(function() {
  WebdashboardRSSPuller.pull();
});
