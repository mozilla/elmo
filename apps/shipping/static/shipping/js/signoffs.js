/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

var dropMode = null;
function dropDiff(event, ui) {
  $(this).append(ui.draggable);
  ui.draggable.css('top', 0);
}

$(document).ready(function() {
  $('.diffanchor').draggable({
     appendTo: 'body',
    axis: 'y',
    revert: true,
    start: function(event, ui) {
      if (dropMode != 'diff') {
        $('.ui-droppable').droppable('destroy');
        $('.diff').droppable({
           drop: dropDiff
        });
        dropMode = 'diff';
      }
    }
  });

  $('.diff').click(function(event) {
    event.stopPropagation();
    var dfs = $('.diffanchor').parent().prev().find('.shortrev');
    if (dfs.length < 2 || dfs[0].textContent == dfs[1].textContent) return;
    var params = {
      from: dfs[1].textContent,
      to: dfs[0].textContent,
      repo: diffData.repo
    };
    params = $.param(params);
    window.open(diffData.url + "?" + params);
  });

  function hoverSO(showOrHide) {
    return function() {
      var q = $('#so_' + this.getAttribute('data-push'))
        .not('.suggested')
          .not('.clicked');
      if (showOrHide === 'hide') {
        q.addClass('hidden');
      } else {
        q.removeClass('hidden');
      }
    }
  }

  $('.pushrow').hover(hoverSO('show'), hoverSO('hide'))
    .click(function() {
      var self = $(this);
      var so = $('#so_' + this.getAttribute('data-push'))
        .not('.suggested');
      if (! so.length) { return; }
      var wasClicked = so.hasClass('clicked');
      so.toggleClass('clicked');
      // XXXX, guess what touch would do
      if (wasClicked != so.hasClass('hidden')) {
        so.toggleClass('hidden');
      }
    });

  if (permissions && permissions.canAddSignoff) {
    $('input.do_signoff').click(doSignoff);
    $('#add_signoff').dialog({
      autoOpen: false,
      width: 600,
      minWidth: 300,
      title: 'Sign-off'
    });
  }
  if (permissions && permissions.canReviewSignoff) {
    $('#review_signoff').dialog({
      autoOpen: false,
      width: 600,
      minWidth: 300,
      title: 'Review'
    });
    $('.review_action').click(function(event) {
      var signoff_id = event.target.getAttribute('data-signoff');
      var rs = $('#review_signoff');
      rs.children('form')[0].signoff_id.value = signoff_id;
      rs.dialog('open');
    });
  }
});

var Review = {
   accept: function(event) {
     var frm = event.target.form;
     frm.querySelector('[type=submit]').disabled = false;
     frm.comment.disabled = true;
     frm.clear_old.disabled = true;
   },
  reject: function(event) {
    var frm = event.target.form;
    frm.querySelector('[type=submit]').disabled = false;
    frm.comment.disabled = false;
    frm.clear_old.disabled = false;
    frm.comment.focus();
  }
};

function showSignoff(details_content) {
  $('#signoff_desc').html(details_content);
  $('#add_signoff').dialog('open');
}

function doSignoff(event) {
  event.stopPropagation();
  var t = $(event.target);
  var rev = event.target.id.substr(3);
  var sf = $('#signoff_form');
  sf.children('[name=revision]').val(rev);
  var run = t.attr('data-run');
  sf.children('[name=run]').val(run);
  $.get(signoffDetailsURL, {rev: rev, run: run}, showSignoff, 'html');
}
