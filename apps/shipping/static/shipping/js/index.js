/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

function clearSelection(e) {
    const block = e.target.closest('.dashboard-block');
    for (const node of block.querySelectorAll(':checked')) {
        node.checked = false;
    }
    updateDescription();
}

function updateDescription() {
    var search = new URLSearchParams();
    var counts = {
        av: 0,
        tree: 0,
        locale: 0
    };
    for (const node of document.querySelectorAll('.dashboard-container :checked')) {
        search.append(node.dataset.key, node.value);
        counts[node.dataset.key]++;
    }
    document.querySelector('.avcount').textContent = (counts.av + counts.tree) || 'all';
    document.querySelector('.loccount').textContent = counts.locale || 'all';
    document.getElementById('trigger').search = search;
}

function ensureTreeOrAppVer(e) {
    if (!e.target.checked) {
        // only ensure that sibling is off if we're on
        return;
    }

    var siblings = e.target
            .closest('tr')
            .querySelectorAll('input');
    for (const sibling of siblings) {
        if (sibling !== e.target && sibling.checked) {
            sibling.checked = false;
            updateDescription();
        }
    }
}

document.querySelector('.av-tree').addEventListener('change', ensureTreeOrAppVer);
for (const clearButton of document.querySelectorAll('.clear-selection')) {
    clearButton.onclick = clearSelection;
}
for (const checkbox of document.querySelectorAll(".dashboard-container input[type=checkbox]")) {
    checkbox.onchange = updateDescription;
}

updateDescription();
