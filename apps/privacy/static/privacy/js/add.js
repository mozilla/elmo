/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

var _idle = 0, _pending = false;
var _policy, _comment, _submit;
function onPolicyChanged(event) {
  if (!_pending) {
    $('#policy').addClass('pending');
    _pending = true;
  }
  _submit.attr('disabled', true);
  _idle = 0;
}

function onCommentChanged(event) {
  _submit.attr('disabled', true);
  _idle = 0;
}

function onTimer() {
  if (_idle < 1000) {
    _idle += 200;
    return;
  }
  if (_pending) {
    var p = $('#policy');
    p.html(_policy.val());
    p.removeClass('pending');
    _pending = false;
  }
  if (_idle < 2000) {
    // we're just stepping out of idle, check disabled
    _submit.attr('disabled', !_policy.val() || _policy.val() == _policy.text() || !_comment.val());
    _idle = 2000;
  }
}

$(document).ready(function() {
  _policy = $('textarea[name=content]');
  _comment = $('textarea[name=comment]');
  _submit = $('input[type=submit]');
  _policy.keypress(onPolicyChanged);
  _comment.keypress(onCommentChanged);
  $('#policy').html(_policy.text());
  window.setInterval(onTimer, 200);
});
