/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is l10n django site.
 *
 * The Initial Developer of the Original Code is
 *   Mozilla Foundation.
 * Portions created by the Initial Developer are Copyright (C) 2010
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *   Axel Hecht <l10n@mozilla.com>
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 *
 * Alternatively, the contents of this file may be used under the terms of
 * the MIT license.
 *
 * ***** END LICENSE BLOCK ***** */

$.aH = $.aH || {};
$.widget('aH.spinner', $.extend({}, $.ui.mouse, {
    _init: function() {
        var that = this;
        this._hovering = false;
        that.element.append($('<table cellspacing="0" cellpadding="0" class="ui-widget ui-widget-content ui-state-default"><tr class="ui-state-hover ui-helper-hidden"></tr><tr><td><span class="ui-icon ui-icon-triangle-1-w">foo</span></td><td><canvas height="10" width="' +
        that.options.width +
        '"></canvas></td><td><span class="ui-icon ui-icon-triangle-1-e">foo</span></td></tr></table>'));
        that.element.children('table')
            .hover(function(){
                $(this).addClass("ui-state-hover");
                this._hovering = true;
            },
            function(){
                $(this).removeClass("ui-state-hover");
                this._hovering = false;
            }
            )
        that._mouseInit();
        that.computeSetup();
        that.value(that.options.value);
    },
    destroy: function() {
        $.widget.prototype.destroy.call(this);
        this._mouseDestroy();
    },
    computeSetup: function() {
        this.canvas = this.element.find('canvas')[0];
        this.ctx = this.canvas.getContext('2d');
        this.r = this.canvas.width/2/Math.sin(this.options.alpha/2/180*Math.PI); //radius
        this.rx = this.r * this.options.alpha * Math.PI / 360 / this.options.n; //px per tick
    },
    updateDisplay: function() {
        var off = 1 - this._value % 1;
        var end = off ? this.options.n - 1 : this.options.n;
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.ctx.beginPath();
        this.ctx.strokeStyle = $('.ui-state-default').css('color');
        for (var i = -this.options.n; i <= end; i += 1) {
            var a = (i + off) * this.rx/this.r;
            var x = this.r * Math.sin(a) + this.canvas.width/2;
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.canvas.height);
        }
        this.ctx.stroke();
    },
    _mouseStart: function(event) {
        this.startValue = this.value();
        this.element.children('table').removeClass('ui-state-hover')
            .addClass('ui-state-active');
        return true;
    },
    _mouseDrag: function(event) {
        var dx = event.clientX - this._mouseDownEvent.clientX;
        var now =  Date.now();
        if (this.previousValue) {
            this.speed = (event.clientX - this.previousValue) /
                (now - this.previousTime);
        }
        this.previousValue = event.clientX;
        this.previousTime = now;
        this.value(this.startValue - dx / this.rx);
    },
    _mouseStop: function(event) {
        this.previousValue = null;
        this.element.children('table').removeClass('ui-state-active');
        if (this._hovering) this.elememnt.children('table').addClass('ui-state-hover');
        if (this.speed && Math.abs(this.speed) >= this.options.fly) {
            function _doStep(now, fx) {
                // this is the element
                if (!now) return;
                $(this).spinner('value', fx.options.value + now)
            }
            this.element.animate({spinnerValue: this.speed/2*200 },
                                {value: this._value,
                                easing:'quadratic',
                                duration: 200,
                                step:_doStep
                                });
        }
    },
    value: function(newValue, dontFire) {
        if (arguments.length) {
            this._value = newValue
            this.updateDisplay();
            if (dontFire === undefined) {
                this.element.triggerHandler(this.widgetName + "value", [newValue]);
            }
        }
        return this._value;
    }
}));
$.extend($.aH.spinner, {
    getter: "value",
    defaults: {
        alpha: 120,
        n: 5,
        value: 0,
        width: 150,
        fly: 1,
        // ui.mouse.defaults
        distance: 1,
        delay: 0,
        cancel: null
    }
});
$.easing.quadratic = function( p, n, firstNum, diff ) {
    return firstNum + diff * p * (2 - p);
};

$.widget(
    'aH.datetime',
    {
        _init: function() {
            var that = this;
            this._dateField = $('<span />')
                .attr({style: 'font-family: monospace'});
            this._monthSpinner = $('<div />').spinner({n:2, width: this.options.width})
                .attr({title:'month'})
                .bind('spinnervalue',
                      function(e, v) {
                        return that._monthBinder(this, e, v);
                      });
            this._daySpinner = $('<div />').spinner({n:3, width: this.options.width})
                .attr({title:'day'});
            this._hourSpinner = $('<div />').spinner({n:3, width: this.options.width})
                .attr({title:'hour'})
                .bind('spinnervalue',
                      function(e, v) {
                        return that._hourBinder(this, e, v);
                      });
            this.element.append(this._dateField)
                .append(this._monthSpinner)
                .append(this._daySpinner)
                .append(this._hourSpinner)
                .addClass('ui-widget');
            this._daySpinner.bind('spinnervalue',
                                  function(e, v) {
                                    return that._dayBinder(this, e, v);
                                  }
                                 )
            this.date((this.options.date === undefined) ? new Date() :
                new Date(this.options.date));
        },
        destroy: function() {
            $.widget.prototype.destroy.call(this);
            this.element.removeClass('ui-widget');
        },
        _days: [31, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31, 31],
        _monthBinder: function(elem, e, v) {
            var slope = this._days[this._date.getUTCMonth() +
                                   ((v < 0) ? 0 : 1)] * (24 * 60 * 60 * 1000)
            var d = new Date(this._date);
            d.setUTCHours(0, 0, 0, 0);
            d.setUTCDate(1);
            d.setUTCMilliseconds(v * slope);
            this.date(d);
        },
        _dayBinder: function(elem, e, v) {
            var d = new Date(v * (24 * 60 * 60 * 1000));
            this.date(d);
        },
        _hourBinder: function(elem, e, v) {
            var d = new Date(v * (60 * 60 * 1000));
            this.date(d);
        },
        date: function(newDate, dontFire) {
            if (arguments.length) {
                this._date = newDate;
                this._dateField.text(this._date.toUTCString());
                var monthStart = new Date(this._date);
                monthStart.setUTCHours(0, 0, 0, 0);
                monthStart.setUTCDate(1);
                var monthOffset = this._date - monthStart;
                monthOffset /= (24 * 60 * 60 * 1000);
                monthOffset /= this._days[monthStart.getUTCMonth() + 1];
                this._monthSpinner.spinner('value', monthOffset,
                                           true);
                var date = Number(this._date) / (24 * 60 * 60 * 1000);
                this._daySpinner.spinner('value', date,
                                         true);
                var hour = Number(this._date) / (60 * 60 * 1000);
                this._hourSpinner.spinner('value', hour,
                                         true);
                if (dontFire === undefined) {
                    this.element.triggerHandler(this.widgetName + "value",
                                                [newDate]);
                }
            }
            return this._date;
        }
    }
);
$.extend($.aH.datetime,
    {
        getter: "date",
        defaults: {
            date: undefined,
            width: 300
        }
    });
