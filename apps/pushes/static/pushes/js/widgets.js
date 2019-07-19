/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

$.aH = $.aH || {};

$.widget(
    'aH.datetime',
    {
        options: {
            date: undefined,
            width: 300
        },
        _create: function() {
            var that = this;
            this._dateField = $('<input type="date" />')[0];
            this._timeField = $('<input type="time" step="1" />')[0];
            this.element.append(this._dateField)
                .append(this._timeField)
                .addClass('ui-widget');
            this._dateField.onchange = () => this.date();
            this._timeField.onchange = () => this.date();
            this.date((this.options.date === undefined) ? new Date() :
                new Date(this.options.date));
        },
        destroy: function() {
            $.Widget.prototype.destroy.call(this);
            this.element.removeClass('ui-widget');
        },
        _days: (30.5 * 24 * 60 * 60 * 1000),
        date: function(newDate, dontFire) {
            if (arguments.length) {
                newDate.setMilliseconds(0);
                this._date = newDate;
                this._dateField.valueAsDate = this._date;
                this._timeField.valueAsDate = this._date;
            }
            else {
              this._date = new Date(
                this._dateField.valueAsNumber + this._timeField.valueAsNumber
              );
            }
            if (dontFire === undefined) {
                this.element.triggerHandler(this.widgetName + "value",
                                            [this._date]);
            }
            return this._date;
        }
    }
);
