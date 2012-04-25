/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/* Special Source to work on dicts */
Timeplot.DictSource = function(eventSource, leaf) {
  Timeplot.ColumnSource.apply(this, [eventSource, 1]);
  this.leaf = leaf;
};
Object.extend(Timeplot.DictSource.prototype, Timeplot.ColumnSource.prototype);

Timeplot.DictSource.prototype._getValue = function(event) {
  return parseFloat(event.getValues()[this.leaf]);
};

function Data(stacked, nonstacked) {
  this.stacked = stacked;
  this.nonstacked = nonstacked;
  this._data = {};
  var _d = this._data;
  if (this.stacked) {
    $.each(this.stacked, function(i, n) {
      _d[n] = 0;
    });
  }
  if (this.nonstacked) {
    $.each(this.nonstacked, function(i, n) {
      _d[n] = 0;
    });
  }
}

Data.prototype = {
   update: function(from, to) {
     if (from) {
       this._data[from] -= 1;
     }
     this._data[to] += 1;
   },
  data: function() {
    var v = 0, rv = {}, _d = this._data;
    if (this.stacked) {
      $.each(this.stacked, function(i, n) {
        v += _d[n];
        rv[n] = v;
      });
    }
    if (this.unstacked) {
      $.each(this.unstacked, function(i, n) {
        rv = _d[n];
      });
    }
    return rv;
  }
};

var showBad = SHOW_BAD;
var bound = BOUND;
var params = {
  bound: bound,
  showBad: showBad,
  clone: function() {
    var rv = {bound: this.bound, showBad: this.showBad, clone: this.clone};
    if ('earliestDate' in this) rv.earliestDate = this.earliestDate;
    if ('latestDate' in this) rv.latestDate = this.latestDate;
    return rv;
  }
};
if (EARLIEST_DATE) {
  params.earliestDate = EARLIEST_DATE;
}
if (LATEST_DATE) {
  params.latestDate = LATEST_DATE;
}

function paramToSearch(p) {
  var _p = [];
  if (p.bound) _p.push('bound=' + p.bound);
  if (!p.showBad) _p.push('hideBad');
  if ('earliestDate' in p) _p.push('starttime=' + p.earliestDate.getTime() / 1000);
  if ('latestDate' in p) _p.push('endtime=' + p.latestDate.getTime() / 1000);
  if (_p.length) {
    return '?' + _p.join('&');
  }
  return '';
}

var timeplot, timeGeometry;
var loc_data = LOCALE_DATA;
var dataRange = [new Date(START_TIME), new Date(END_TIME)];
var locales = [];
var localesSource, changesSource;
var checkinPlot, badPlot, shadyPlot, goodPlot;
function onLoad() {
  var theme = Timeline.ClassicTheme.create();
  theme.event.bubble.width = 50;
  theme.event.bubble.height = 50;
  localesSource = new Timeplot.DefaultEventSource();
  changesSource = new Timeplot.DefaultEventSource();
  var tgParams = {
    gridColor: new Timeplot.Color('#000000'),
    axisLabelsPlacement: 'top'
  };
  if ('earliestDate' in params) tgParams.min = params.earliestDate;
  if ('latestDate' in params) tgParams.min = params.latestDate;
  timeGeometry = new Timeplot.MagnifyingTimeGeometry(tgParams);

  var valueGeometry = new Timeplot.DefaultValueGeometry({
    gridColor: '#000000',
    min: 0
  });
  var plotInfo = [];
  var checkinPlot = Timeplot.createPlotInfo({
    id: 'checkins',
    timeGeometry: timeGeometry,
    eventSource: changesSource,
    lineColor: 'blue',
    bubbleWidth: 250,
    bubbleHeight: 100,
    theme: theme
  });
  goodPlot = Timeplot.createPlotInfo({
    id: 'good',
    dataSource: new Timeplot.DictSource(localesSource, 'good'),
    valueGeometry: valueGeometry,
    timeGeometry: timeGeometry,
    lineColor: '#000000',
    fillColor: '#339900',
    fillGradient: false,
    flat: true,
    showValues: true
  });
  shadyPlot = Timeplot.createPlotInfo({
    id: 'shady',
    dataSource: new Timeplot.DictSource(localesSource, 'shady'),
    valueGeometry: valueGeometry,
    timeGeometry: timeGeometry,
    lineColor: '#000000',
    fillColor: '#666666',
    //fillGradient: false,
    flat: true,
    showValues: true
  });
  badPlot = Timeplot.createPlotInfo({
    id: 'bad',
    dataSource: new Timeplot.DictSource(localesSource, 'bad'),
    valueGeometry: valueGeometry,
    timeGeometry: timeGeometry,
    lineColor: '#ff0000',
    fillColor: 'rgba(153,0,0,.8)', //'#990000'
    fillGradient: false,
    flat: true,
    showValues: true
  });
  if (params.showBad)
    plotInfo.push(badPlot);
  if (params.bound)
    plotInfo.push(shadyPlot);
  plotInfo.push(goodPlot);
  plotInfo.push(checkinPlot);

  timeplot = Timeplot.create(document.getElementById('my-timeplot'), plotInfo);
  var i = 0;
  var state = new Data(['good', 'shady', 'bad']);
  var latest = {};
  var _data = {};
  function _getState(_count) {
    if (_count == 0) return 'good';
    if (_count > params.bound) return 'bad';
    return 'shady';
  }
  for (var loc in loc_data[i].locales) {
    locales.push(loc);
    latest[loc] = _getState(loc_data[i].locales[loc]);
    _data[loc] = loc_data[i].locales[loc];
    // no breaks on purpose, to stack data
    state.update(undefined, latest[loc]);
  }
  var NE = Timeplot.DefaultEventSource.NumericEvent;
  var E = Timeline.DefaultEventSource.Event;
  var locEvents = [new NE(loc_data[i].time, state.data())];
  var changeEvents = [];
  for (var i = 1; i < loc_data.length; ++i) {
    var loclist = [];
    for (var loc in loc_data[i].locales) {
      _data[loc] = loc_data[i].locales[loc];
      isGood = _getState(loc_data[i].locales[loc]);
      if (isGood != latest[loc]) {
        state.update(latest[loc], isGood);
        loclist.push(loc);
        latest[loc] = isGood;
      }
    }
    if (loclist.length) {
      loclist.sort();
      changeEvents.push(new E({
        start: loc_data[i].time,
        description: loclist.join(' '),
        instant: false}));
    }
    locEvents.push(new NE(loc_data[i].time, state.data()));
  }
  locEvents.push(new NE(
    SimileAjax.DateTime.parseIso8601DateTime(END_TIME),
    state.data())
  );
  localesSource.addMany(locEvents);
  changesSource.addMany(changeEvents);
  timeplot.repaint();
  paintHistogram(_data);
  $('#my-timeplot').click(onClickPlot).dblclick(onDblClickPlot);
  $('#boundField').attr('value', params.bound);
  if (params.showBad)
    $('#showBadField').attr('checked', 'checked');
  else
    $('#showBadField').removeAttr('checked');
  /* this doesn't work yet, it triggers change events on the slider
  var _d;
  _d = ('earliestDate' in params) ? params.earliestDate : dataRange[1];
  $('#time-slider').slider('values', 0, _d.getTime());
  _d = ('latestDate' in params) ? params.latestDate : dataRange[0];
  $('#time-slider').slider('values', 1, _d.getTime());
  */
}

function update(args) {
  var oldP = params, nextP = params.clone();
  $.each(args, function(k, v) {
    nextP[k] = v;
  });
  SimileAjax.History.addLengthyAction(
    function() {
      params = nextP;
      onLoad();
    },
    function() {
      params = oldP;
      onLoad();
    },
    '');
}
var resizeTimerID = null;
function onResize() {
  if (resizeTimerID == null) {
    resizeTimerID = window.setTimeout(function() {
      resizeTimerID = null;
      timeplot.repaint();
    }, 100);
  }
}

function onDblClickPlot(evt) {
  var target = evt.currentTarget;
  var elem = $(target).find('.timeplot-canvas')[0];
  var offsetX = elem.offsetLeft;
  while (elem.offsetParent) {
    elem = elem.offsetParent;
    if (elem.offsetLeft) {
      offsetX += elem.offsetLeft;
    }
  }
  var t = timeGeometry.fromScreen(evt.pageX - offsetX);
  var time_window = timeGeometry.getPeriod() / 8;
  var latestDate = new Date(t + time_window);
  // check for end-of-query, no explicit endDate, and end>dataRange
  if (latestDate > dataRange[1] && !('latestDate' in params)) {
    var earliestDate = new Date(dataRange[1].getTime() - time_window);
    update({earliestDate: earliestDate});
    return;
  }
  var earliestDate = new Date(t - time_window);
  update({earliestDate: earliestDate, latestDate: latestDate});
}

function onClickPlot(evt) {
  var target = evt.currentTarget;
  var elem = $(target).find('.timeplot-canvas')[0];
  var offsetX = elem.offsetLeft;
  while (elem.offsetParent) {
    elem = elem.offsetParent;
    if (elem.offsetLeft) {
      offsetX += elem.offsetLeft;
    }
  }
  var t = new Date(timeGeometry.fromScreen(evt.pageX - offsetX));
  var d = {};
  for (var i = 0; i < loc_data.length && loc_data[i].time < t; ++i) {
    for (var loc in loc_data[i].locales) {
      d[loc] = loc_data[i].locales[loc];
    }
  }
  paintHistogram(d);
}

function paintHistogram(d) {
  var data = [];
  for (var loc in d) {
    data.push(d[loc]);
  }
  data.sort();
  var smooth = Math.sqrt;
  var clusterer = new Clusterer(data, smooth);
  var ranges = clusterer.get_ranges(4); // TODO find something better
  var hists = new Array(ranges.length);
  for (var i = 0; i < hists.length; ++i) hists[i] = [];
  var maxcount = 1;
  for (var loc in d) {
    var val = d[loc];
    for (i = 0; i < ranges.length && val > ranges[i].max; ++i) {
    }
    if (hists[i][val]) {
      hists[i][val].push(loc);
      if (hists[i][val].length > maxcount) {
        maxcount = hists[i][val].length;
      }
    } else {
      hists[i][val] = [loc];
    }
  }

  // histogram
  var hist_div = document.getElementById('histogram');
  hist_div.innerHTML = '<table cellpadding="1"><tr class="hg"><td  class="axis"><div class="hist_block"></div></td></tr><tr class="hd"><td></td></tr></table>';
  var graphs_row = hist_div.children[0].rows[0];
  var descs_row = hist_div.children[0].rows[1];
  var axis_div = $(graphs_row.children[0].children[0]);
  var atitle = $('<span>' + maxcount + '</span>');
  atitle.css('position', 'absolute').css('top', '0px');
  axis_div.append(atitle);
  axis_div.css('width', atitle.css('width'));
  axis_div.css('padding-left', '1px').css('padding-right', '1px');
  // create display of histogram
  var jmin = 0;
  var barwidth = 10;
  var chart_height = 100; // XXX get from computed style of hist_div
  var display_f = function(_v) {
    return Math.pow(_v, 3 / 4);
  };
  var scale = chart_height * 1.0 / display_f(maxcount);
  for (var i in hists) {
    var hist = hists[i];
    var range = ranges[i];
    var jmin = undefined;
    var td = $('<td></td>');
    $(descs_row).append(td);
    if (range.min == range.max) {
      td.append(range.min);
    } else {
      td.append(range.min + ' - ' + range.max);
    }
    var td = $('<td><div class="hist_block"></div></td>');
    td.attr('title', range.count);
    hist_div = td.children()[0];
    $(graphs_row).append(td);
    var values = [];
    $.each(hist, function(i, j) {
      if (j !== undefined) values.push(i);
    });
    values.sort(function(a, b) {
      return a - b;
    });
    var _j = undefined;
    var _left = 0;
    for (var k in values) {
      j = values[k];
      if (jmin === undefined) {
        jmin = j;
      }
      var v = hist[j];
      v.sort();
      var height = display_f(v.length) * scale;
      var top = chart_height - height;
      var width = barwidth;
      var d = document.createElement('div');
      hist_div.appendChild(d);
      d.style.top = top + 'px';
      d.style.width = width - 2 + 'px';
      d.style.height = height - 1 + 'px';
      if (_j !== undefined) {
        _left += (smooth(j - 1) - smooth(_j)) * barwidth;
      }
      _j = j;
      d.style.left = Number(_left).toFixed(1) + 'px';
      _left += barwidth;
      d.setAttribute('class', 'bar ui-widget-header');
      d.setAttribute('title', j + ': ' + v.join(' ') + ' (' + v.length + ')');
    }
    hist_div.style.width = Number(_left).toFixed(1) + 'px';
  }
}

$(document).ready(onLoad);
$(window).resize(onResize);
$(function() {
  $('#time-slider').slider({
    range: true,
    min: ALL_START_U,
    max: ALL_END_U,
    values: [START_TIME_U, END_TIME_U],
    slide: function(event, ui) {
      1 + 1;
    },
    change: function(event, ui) {
      var v = ui.value, key = 'latestDate', vd = new Date(v * 1000);
      if (v == ui.values[0]) key = 'earliestDate';
      if (vd >= dataRange[0] && vd <= dataRange[1]) {
        var ud = {}; ud[key] = vd;
        update(ud);
        return;
      }
      params[key] = vd;
      document.location.search = paramToSearch(params);
    }
    });
});
