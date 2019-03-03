/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
/* global URL, fetch */

function getBugURL(params) {
  const url = new URL('https://bugzilla.mozilla.org/enter_bug.cgi?');
  for (var k in params) {
    if (k != 'title') {
      url.searchParams.set(k, params[k]);
    }
  }
  return url;
}

function doBugs() {
  const url = new URL(document.head.querySelector('[rel=new-locale-bugs]').href);
  Array.from(document.forms.bugdata.elements).forEach(
    input => url.searchParams.set(input.name, input.value)
  );
  // generate edit_bugs links right away,
  // and the buglinks once we have them formatted
  const editout = document.getElementById('users');
  editout.innerHTML = '';
  const link_template = document.createElement('a');
  link_template.href =
    'https://bugzilla.mozilla.org/editusers.cgi?' +
    'action=list&matchvalue=login_name&matchtype=substr&matchstr=';
  link_template.target = '_blank';
  document.forms.bugdata.bugmail.value.split(/\s*,\s*/).forEach(
         function (email) {
          let link = link_template.cloneNode(true);
          link.href += encodeURIComponent(email);
          link.textContent = email;
          editout.appendChild(link);
          editout.appendChild(document.createTextNode(' '));
         });
  function handleLinkJSON(data) {
    if (data === undefined) {
      return;
    }
    var out = document.getElementById('links');
    out.innerHTML = '';
    data.forEach(function(bug) {
      var child = document.createElement('a');
      child.textContent = bug.title;
      child.href = getBugURL(bug);
      child.target = '_blank';
      out.appendChild(child);
      out.appendChild(document.createTextNode(' '));
    });
  }
  function handleLinkFailure() {
    document.getElementById('links').textContent = 'Failed to create bug links';
  }

  fetch(url).then(r => r.json()).then(handleLinkJSON, handleLinkFailure);
}
