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

function log() {
  if (window.console && window.console.log)
    console.log.apply(console, arguments);
}

var progress = {
  _c: 0,
  load: function() {
    this._c++;
    document.body.style.cursor = 'progress';
  },
  done: function() {
    this._c--;
    if (this._c == 0) {
      document.body.style.cursor = '';
    }
  }
};

$(document).ready(function() {
  var d = $('#searchpane').dialog({
    autoOpen: false,
    modal: true,
    width: 500,
    buttons: {
       Search: function() {
         $(this).children('form').submit();
       }
    }
  });

  $('#search').click(function() {
    d.dialog('open');
  })
    .hover(
      function() {
        $(this).addClass('ui-state-hover');
      }, function() {
        $(this).removeClass('ui-state-hover');
      }
    )
    .focus(function() {
      $(this).addClass('ui-state-focus');
    })
    .blur(function() {
      $(this).removeClass('ui-state-focus');
    });

  function enableField(fieldName) {
    var targetInput = $('#i_' + fieldName)[0];
    return function(e) {
      var cell = $(e.target).parents('tr').children('td:nth-child(2)');
      if (!cell.hasClass('ui-widget')) {
        var date = targetInput.value ? Number(targetInput.value * 1000) : undefined;
        cell.html('').datetime({
           date: date
        })
          .bind('datetimevalue', function(e, v) {
            targetInput.value = Number(v) / 1000;
          });
        $('#i_' + fieldName).attr('name', fieldName);
      } else {
        cell.datetime('destroy').html('&hellip;');
        $('#i_' + fieldName).removeAttr('name');
      }

    }
  };
  $('#b_from').click(enableField('from'));
  if (SEARCH.FROM) {
    $('#b_from').trigger('click');
  }
  $('#b_until').click(enableField('until'));
  if (SEARCH.UNTIL) {
    $('#b_until').trigger('click');
  }
  $('#b_limit').click(function(e) {
    var cell = $(e.target).parents('tr').children('td:nth-child(2)');
    if (!cell.hasClass('ui-widget')) {
      cell.addClass('ui-widget').removeClass('ui-state-disabled');
      cell.find('input').attr('name', 'length');
    } else {
      cell.removeClass('ui-widget').addClass('ui-state-disabled');
      cell.find('input').removeAttr('name');
    }
  });
});

function addSearch(select) {
  if (select.selectedIndex == 0) {
    log('doing nothing, lead selected');
    return;
  }
  var choice = select.options[select.options.selectedIndex];
  log('selected ' + choice);
  switch (choice.id) {
    case 'search_files':
      $('#searchrows').append('<tr><td>Path part</td><td><input name="path" type="text" size="10" maxlength="30"></tr>');
      break;
    case 'search_repos':
      $('#searchrows').append('<tr><td>Repository part</td><td><input name="repo" type="text" size="10" maxlength="30"></tr>');
      break;
  }
}

var diffstuff = false;
function show_to() {
  if (diffstuff) return;
  var styles = document.styleSheets;
  for (var i = 0, ii = styles.length; i < ii; ++i) {
    if (styles[i].title == 'diffstuff') {
      diffstuff = styles[i];
      diffstuff.deleteRule(0);
      return;
    }
  }
}

function show_diffs(reponame, input) {
  show_to();
  var tos = $('.diff_tofrom');
  tos.removeClass('diff_tofrom');
  tos = $('td.diff_active>input[rev=' + input.value + ']');
  tos.addClass('diff_tofrom');
  $('tr[repo]').each(function(i, r) {
    if (r.getAttribute('repo') == reponame) {
      $(r).removeClass('hidediff');
    }
    else {
      $(r).addClass('hidediff');
    }
  });
}

function doDiff(button) {
  var params = {};
  $('input[type=radio]').each(function(i, r) {
    if (r.checked) {
      params.from = r.value;
    }
  });
  params.to = button.getAttribute('rev');
  params.repo = $(button).parents('tr').first().attr('repo');
  window.open(DIFF_APP_URL + '?' + $.param(params, true));
}
