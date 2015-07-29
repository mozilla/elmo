/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
/* global Exhibit */

jQuery(document).one("scriptsLoaded.exhibit", function(evt) {
    var EX_OPTIONS = ["result", "shipping", "signoff"];
    var params = Exhibit.parseURLParameters();
    for (var i in EX_OPTIONS) {
        var option = EX_OPTIONS[i];
        if (option in params) {
            if (params[option]) {
                document.getElementById(option + '-facet')
                    .setAttribute('data-ex-selection', params[option]);
            }
            else {
                document.getElementById(option + '-facet')
                    .setAttribute('data-ex-select-missing', 'true');
            }
        }
    }
});
jQuery(document).one("exhibitConfigured.exhibit", function(evt) {
    $('table.exhibit-tabularView-body').thead();
});
