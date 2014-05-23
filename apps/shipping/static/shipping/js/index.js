/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

$('#trigger').click(function(e) {
    var params = $(':checked').map(function() {
        return this.dataset.key + '=' + this.value;
    });
    e.target.href = e.target.dataset.base + '?' + Array.join(params, '&');
});

$('.clear-selection').click(function(){
    $(this).parents('.dashboard-block')
        .first().find(':checked')
        .each(function() {
            this.checked = false;
        });
    updateDescription();
});

$(".dashboard-container input[type=checkbox]").change(updateDescription);

function updateDescription() {
    var counts = {
        av: 0,
        tree: 0,
        locale: 0
    };
    $('.dashboard-container :checked').each(
        function() {
            counts[this.dataset.key]++;
        }
    );
    if (counts.av + counts.tree) {
        $('.avcount').text(counts.av + counts.tree);
    }
    else {
        $('.avcount').text('all');
    }
    if (counts.locale) {
        $('.loccount').text(counts.locale);
    }
    else {
        $('.loccount').text('all');
    }
}

$('.av-tree input[type=checkbox]').change(function() {
    if (this.disabled) {
        // our sibling is changing us, ignore
        return;
    }
    var siblingmap = {tree: 'av', av: 'tree'};
    // jquery makes this hard, let's use the DOM
    var sibling = this
            .parentNode
            .parentNode
            .querySelector('input[data-key=' +
                           siblingmap[this.dataset.key]+ ']');

    if (this.checked) {
        // disable and uncheck our sibling
        sibling.disabled = true;
        sibling.checked = false;
    }
    else {
        // enable the sibling
        sibling.disabled = false;
    }
});

$(updateDescription);
