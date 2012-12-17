/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

function getBugURL(params) {
  var ps = [];
  for (var k in params) {
    if (k != 'title') {
      ps.push(k + '=' + encodeURIComponent(params[k]));
    }
  }
  var url = 'https://bugzilla.mozilla.org/enter_bug.cgi?';
  url += ps.join('&');
  return url;
}

function doBugs() {
  var params = {};
  function addParam() {
    params[this.name] = this.value;
  }
  $.each(document.forms.bugdata.elements, addParam);
  // generate edit_bugs links right away,
  // and the buglinks once we have them formatted
  var editout = $('#users').html('');
  $.each(document.forms.bugdata.bugmail.value.split(/\s*,\s*/),
         function (_, email) {
          var link = 'https://bugzilla.mozilla.org/editusers.cgi?' +
            'action=list&matchvalue=login_name&matchtype=substr&matchstr=';
          link += encodeURIComponent(email);
          var child = $('<a>').text(email);
          child.attr({href: link, target: '_blank'});
          editout.append(child).append(' ');
         });
  function handleLinkJSON(data, result) {
    var out = $('#links');
    if (result != 'success') {
      out.html('Failed to create bug links');
      return;
    }
    out.html('');
    $.each(data, function() {
      var child = $('<a>').text(this.title);
      child.attr('href', getBugURL(this));
      child.attr('target', '_blank');
      out.append(child);
      out.append(' ');
    });
  }
  $.getJSON(NEW_LOCALE_URL, params, handleLinkJSON);
}
