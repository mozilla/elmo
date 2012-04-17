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

var BugPuller = (function(code) {
  var _locale_code = code;
  var parent = $('#bugzilla');

  function getURL(suffix) {
    return 'https://api-dev.bugzilla.mozilla.org/1.1/' + suffix;
  }

  function getData() {
    return {
      'field0-0-0': 'component',
      'type0-0-0': 'regexp',
      'value0-0-0': '^' + _locale_code + ' / ',
      'resolution': '---',
      'include_fields': 'id,last_change_time'
    };
  }

  function excuse() {
    $('.loading', parent).hide();
    $('.loaded', parent).hide();
    $('.failed', parent).show();
  }


  return {
    render: function(json) {

      json.bugs.sort(function(l, r) {
        return l.last_change_time < r.last_change_time ? 1 : -1;
      });

      function buglink(b, prop) {
        return '<a href="https://bugzilla.mozilla.org/show_bug.cgi?id=' +
          b.id + '">' + b[prop] + '</a>';
      }

      var tbody = $('<tbody>');
      $.each(json.bugs, function(i, bug) {
        var tr = $('<tr>').addClass('treesummary');
        $('<td>')
          .append($(buglink(bug, 'id')))
          .appendTo(tr);

        $('<td>')
          .text(bug.summary)
          .appendTo(tr);

        $('<td>')
          .text(new Date(bug.last_change_time).toDateString())
          .appendTo(tr);

        $('<td>')
          .addClass('last-col')
          .text(new Date(bug.creation_time).toDateString())
          .appendTo(tr);

        tbody.append(tr);

      });

      // it's more effient to not attach this to the DOM until it's fully
      // populated
      tbody.appendTo($('table', parent));
      $('.loading', parent).hide();
      $('.table-pre-header', parent).fadeIn(300);
      $('table.recent-bugs:hidden', parent).fadeIn(300);
    },
    pre_render: function(json) {
      $('.recent-bugs', parent).hide();
      // update the count inline
      $('.bug-count', parent).text(json.bugs.length);
      $('.loaded', parent).fadeIn(300);

      if (json.bugs.length) {
        $('.loading', parent).show();

        json.bugs.sort(function(l, r) {
          return l.last_change_time < r.last_change_time ? 1 : -1;
        });

        var IDs = $.map(json.bugs.slice(0, 5), function(o) {
          return o.id;
        });

        var details = {
          'bug_id': IDs.join(','),
          'include_fields': 'id,summary,creation_time,last_change_time'
        };

        $.ajax({
           url: getURL('bug'),
          data: details,
          dataType: 'json',
          success: BugPuller.render,
          error: function(jqXHR, textStatus, errorThrown) {
            excuse();
          }
        });
      } else {
        // no bugs to fetch more details about
        // Mozilla is using bugs in Bugzilla to track
      }

    },
    pull: function() {
      $.ajax({
         url: getURL('bug'),
        data: getData(),
        dataType: 'json',
        success: BugPuller.pre_render,
        error: function(jqXHR, textStatus, errorThrown) {
          excuse();
        }
      });
    }
  };
})(LOCALE_CODE);

$(function() {
  BugPuller.pull();
});
