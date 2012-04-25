/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

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
