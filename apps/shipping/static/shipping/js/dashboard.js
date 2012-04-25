/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

SimileAjax.jQuery(document).ready(function() {
  var fDone = function() {
    var params = SimileAjax.parseURLParameters();
    for (var i in EX_OPTIONS) {
      var option = EX_OPTIONS[i];
      if (option in params) {
        if (params[option]) {
          document.getElementById(option + '-facet')
            .setAttribute('ex:selection', params[option]);
        }
        else {
          document.getElementById(option + '-facet')
            .setAttribute('ex:selectMissing', 'true');
        }
      }
    }

    window.exhibit = Exhibit.create();
    window.exhibit.configureFromDOM();
  };

  window.database = Exhibit.Database.create();
  window.database.loadDataLinks(fDone);
});
