/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

function hideSiblingNextMarkers() {
    var lastmarker;
    Array.from(
        document.querySelectorAll('.next-marker')
    ).forEach(function(markernode) {
        lastmarker = markernode;
        if (!markernode.previousElementSibling) {
            return;
        }
        if (!markernode.previousElementSibling.previousElementSibling) {
            return;
        }
        var cl;
        if ((cl = markernode.previousElementSibling.previousElementSibling.classList).contains('next-marker')) {
            cl.add('hidden');
        }
    });
    if (lastmarker) {
        // hide last jump marker
        lastmarker.classList.add('hidden');
    }
}

hideSiblingNextMarkers();
