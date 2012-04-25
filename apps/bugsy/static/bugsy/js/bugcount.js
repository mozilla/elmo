/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

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
