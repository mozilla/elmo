/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
/* global URL, fetch, LOCALE_CODE */

var BugPuller = (function(code) {
  var _locale_code = code;
  var parent = document.getElementById('bugzilla');

  function excuse() {
    parent.className = 'failed';
  }


  return {
    render: function(json) {
      if (json === undefined) {
        // network failed before
        return;
      }
      parent.querySelector('.bug-count').textContent = json.bugs.length;

      json.bugs.sort(function(l, r) {
        return l.last_change_time < r.last_change_time ? 1 : -1;
      });

      var tbody = document.createDocumentFragment();
      var template = document.createElement('template');
      template.innerHTML = `<tr class="treesummary">
        <td><a></a></td>
        <td></td>
        <td></td>
        <td class="last-col"></td>
      </tr>`;
      json.bugs.slice(0, 5).forEach(function(bug) {
        let tr = template.content.cloneNode(true);
        let tds = tr.querySelectorAll('td');
        let anchor = tds[0].querySelector('a');
        anchor.href = `https://bugzilla.mozilla.org/show_bug.cgi?id=${bug.id}`;
        anchor.textContent = bug.id;
        tds[1].textContent = bug.summary;
        tds[2].textContent = new Date(bug.last_change_time).toDateString();
        tds[3].textContent = new Date(bug.creation_time).toDateString();

        tbody.append(tr);

      });

      // it's more effient to not attach this to the DOM until it's fully
      // populated
      parent.querySelector('tbody').appendChild(tbody);
      parent.className = 'loaded';
    },
    pull: function() {
      let url = new URL('https://bugzilla.mozilla.org/rest/bug?');
      url.searchParams.set('j_top', 'OR');
      url.searchParams.set('f1', 'component');
      url.searchParams.set('o1', 'regexp');
      url.searchParams.set('v1', '^' + _locale_code + ' / ');
      url.searchParams.set('f2', 'cf_locale');
      url.searchParams.set('o2', 'regexp');
      url.searchParams.set('v2', '^' + _locale_code + ' / ');
      url.searchParams.set('resolution', '---');
      url.searchParams.set('include_fields', 'id,summary,creation_time,last_change_time');
      fetch(url)
        .then(r => r.json(), excuse
        )
        .then(BugPuller.render);
    }
  };
})(LOCALE_CODE);

BugPuller.pull();
