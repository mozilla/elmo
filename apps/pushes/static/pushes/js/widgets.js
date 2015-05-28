/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

$.aH = $.aH || {};
$.widget('aH.spinner', $.ui.mouse, {
    options: {
        alpha: 120,
        n: 5,
        value: 0,
        width: 150,
        fly: 1,
        // ui.mouse.defaults
        distance: 1,
        delay: 0,
        cancel: null
    },
    _create: function() {
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
        $.Widget.prototype.destroy.call(this);
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
});
$.easing.quadratic = function( p, n, firstNum, diff ) {
    return firstNum + diff * p * (2 - p);
};

$.widget(
    'aH.datetime',
    {
        options: {
            date: undefined,
            width: 300
        },
        _create: function() {
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
            $.Widget.prototype.destroy.call(this);
            this.element.removeClass('ui-widget');
        },
        _days: (30.5 * 24 * 60 * 60 * 1000),
        _monthBinder: function(elem, e, v) {
            var d = new Date(v * this._days);
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
                var month = Number(this._date) / this._days;
                this._monthSpinner.spinner('value', month,
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
