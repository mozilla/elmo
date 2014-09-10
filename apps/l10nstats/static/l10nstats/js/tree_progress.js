/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

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
  data: function(date) {
    var v = 0, rv = {}, _d = this._data;
    if (date) rv.date = date;
    if (this.stacked) {
      $.each(this.stacked, function(i, n) {
        v += _d[n];
        rv[n] = v;
      });
    }
    if (this.nonstacked) {
      $.each(this.nonstacked, function(i, n) {
        rv[n] = _d[n];
      });
    }
    return rv;
  }
};

var showBad = SHOW_BAD;
var bound = BOUND;
var params = {
  bound: bound,
  showBad: showBad
};

var data, state, data0, X;
var loc_data = LOCALE_DATA;
var locales = [];

var dashboardHistoryUrl = window.DASHBOARD_HISTORY_URL + "&starttime=" + formatRoundedDate(startdate) + "&endtime=" + formatRoundedDate(enddate) + "&locale="

function renderPlot() {
  var _p = {};
  if (!params.showBad) _p.hideBad = true;
  if (params.bound) _p.bound = params.bound;
  var tp = timeplot("#my-timeplot",
                    fullrange,
                    [startdate, enddate],
                    _p);
  var svg = tp.svg;
  X = tp.x;

  var tooltipElt = $('#locales-tooltip');
  var goodLocalesElt = $('.good', tooltipElt);
  var shadyLocalesElt = $('.shady', tooltipElt);
  var badLocalesElt = $('.bad', tooltipElt);

  var i = 0, loc;
  state = new Data(null, ['good', 'shady', 'bad']);
  var latest = {};
  var _data = {};
  data = [];
  function _getState(_count) {
    if (_count === 0) return 'good';
    if (_count > params.bound) return 'bad';
    return 'shady';
  }
  for (loc in loc_data[i].locales) {
    locales.push(loc);
    latest[loc] = _getState(loc_data[i].locales[loc]);
    _data[loc] = loc_data[i].locales[loc];
    // no breaks on purpose, to stack data
    state.update(undefined, latest[loc]);
  }
  data.push(state.data(loc_data[i].time));
  var changeEvents = [];
  for (i = 1; i < loc_data.length; ++i) {
    for (loc in loc_data[i].locales) {
      _data[loc] = loc_data[i].locales[loc];
      isGood = _getState(loc_data[i].locales[loc]);
      if (isGood != latest[loc]) {
        state.update(latest[loc], isGood);
        latest[loc] = isGood;
      }
    }
    data.push(state.data(loc_data[i].time));
  }
  data.push(state.data(enddate));
  var layers = ['good', 'shady'];
  if (params.showBad) {
    layers.push('bad');
  }
  data0 = d3.layout.stack()(layers.map(function(k){
    return data.map(function(d){
      return {
        x: d.date,
        y: d[k]
      };
    });
  }));
  var area = d3.svg.area()
    .interpolate("step-after")
    .x(function(d) {
      return tp.x(d.x);
    })
    .y0(function(d) { return tp.y(d.y0); })
    .y1(function(d) { return tp.y(d.y + d.y0); });
  tp.yDomain([0, d3.max(data.map(function(d) { return d.good + d.shady + (params.showBad ? d.bad : 0); })) + 10]);
  svg.selectAll("path.progress")
     .data(data0)
     .enter()
     .append("path")
     .attr("class", "progress")
     .style("stroke", "black")
     .style("fill", function (d, i) {
        return ['#339900', 'grey', '#990000'][i];
      })
     .attr("d", area);

  // --> Changing locales logic <-- //

  // Utility function to add a list of locales to a DOM element.
  function showLocalesInElement(locales, element) {
    var ln = locales.length;

    // Maximum number of elements that will be shown in the reduced tooltip.
    var clipTreshold = 4;

    if (ln === 0) {
      element.text("-");
      return;
    }

    element.empty();

    var clippedElt = $("<span>", { "class": "clipped" });
    var addTo = element;

    for (var i = 0; i < ln; i++) {
      var locale = locales[i];

      var linkElt = $("<a>", { href: dashboardHistoryUrl + locale });
      linkElt.text(locale);

      if (i >= clipTreshold) {
        addTo = clippedElt;
      }

      if (i > 0) {
        addTo.append(', ');
      }
      addTo.append(linkElt);
    }

    element.append(clippedElt);

    if (ln > clipTreshold) {
      element.append($("<span>", { "class": "hellip" }).html("&hellip;"));
    }
  }

  // Create the transparent white box that follows the mouse and shows the
  // considered time range.
  var whiteBoxWidth = 20; // pixels
  var whiteBoxOffset = whiteBoxWidth / 2;
  var whiteBox = svg.append("g").append("rect");
  whiteBox.attr("x", -9999)
    .attr("y", tp.y(0) - tp.height - 1)
    .attr("width", whiteBoxWidth)
    .attr("height", tp.height)
    .style("fill", "white")
    .style("stroke", "white")
    .style("opacity", "0.2");

  // Return the latest state of each locale that changed in a time window.
  function findChanges(startTime, endTime) {
    var loc;
    var results = {};
    var lastKnownState = {};
    for (var i = 0, ln = loc_data.length; i < ln; i++) {
      var ldata = loc_data[i];
      if (ldata.time > endTime) {
        break;
      }

      for (loc in ldata.locales) {
        var locState = _getState(ldata.locales[loc]);

        if (ldata.time >= startTime) {
          if (lastKnownState[loc] != locState) {
            results[loc] = locState;
          }
          lastKnownState[loc] = locState;
        }
        else {
          lastKnownState[loc] = locState;
        }
      }
    }

    var triagedLocales = {
      good: [],
      bad: [],
      shady: []
    };
    for (var l in results) {
      triagedLocales[results[l]].push(l);
    }

    return triagedLocales;
  }

  function showTooltip() {
    whiteBox.style("opacity", 0.2);
    tooltipElt.show();
  }

  function hideTooltip() {
    whiteBox.style("opacity", 0);
    tooltipElt.hide();
  }

  function showLocalesTooltip() {
    // First update the position of the white box.
    var mouseX = d3.mouse(this)[0];
    whiteBox.attr("x", mouseX - whiteBoxOffset);

    // Then compute the list of changing locales in this range.
    var triagedLocales = findChanges(
      tp.x.invert(mouseX - whiteBoxOffset),
      tp.x.invert(mouseX + whiteBoxOffset)
    );

    // Finaly show those locales in the tooltip box.
    if (triagedLocales) {
      showLocalesInElement(triagedLocales.good, goodLocalesElt);
      showLocalesInElement(triagedLocales.bad, badLocalesElt);
      showLocalesInElement(triagedLocales.shady, shadyLocalesElt);
    }

    if (mouseX > tp.width / 2) {
      tooltipElt.css("right", (tp.width - mouseX) + "px");
      tooltipElt.css("left", "auto");
    }
    else {
      tooltipElt.css("left", mouseX + "px");
      tooltipElt.css("right", "auto");
    }

    showTooltip();
  }

  // Define a new element that is the size of the graph, and that is used to
  // detect the mouse movements. As this element is on top in the DOM, this
  // ensures all mouse events will be caught.
  var graphZone = svg.append("g").append("rect");
  graphZone.attr("x", 0)
    .attr("y", tp.y(0) - tp.height - 1)
    .attr("width", tp.width)
    .attr("height", tp.height)
    .style("opacity", 0);

  // Hide and show the tooltip and the white box.
  graphZone.on("mousemove", showLocalesTooltip)
           .on("mouseout", hideTooltip);

  tooltipElt.on("mouseover", showTooltip)
            .on("mouseout", hideTooltip);

  // <-- Changing locales logic --> //

  paintHistogram(_data);
  $('#my-timeplot').click(onClickPlot);
  $('#boundField').attr('value', params.bound);
  if (params.showBad)
    $('#showBadField').attr('checked', 'checked');
  else
    $('#showBadField').removeAttr('checked');
}

function update(args) {
  $.extend(params, args);
  renderPlot();
}

function onClickPlot(evt) {
  var x = evt.pageX-$("g.x.axis").offset().left;
  var t = X.invert(x);
  var d = {};
  for (var i = 0; i < loc_data.length && loc_data[i].time < t; ++i) {
    for (var loc in loc_data[i].locales) {
      d[loc] = loc_data[i].locales[loc];
    }
  }
  paintHistogram(d);
}

function paintHistogram(d) {
  var data = [], loc, i;
  for (loc in d) {
    data.push(d[loc]);
  }
  function numerical(a, b) {return a-b;}
  data.sort(numerical);
  var smooth = Math.sqrt;
  var clusterer = new Clusterer(data, smooth);
  var ranges = clusterer.get_ranges(4); // TODO find something better
  var hists = new Array(ranges.length);
  for (i = 0; i < hists.length; ++i) hists[i] = [];
  var maxcount = 1;
  for (loc in d) {
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
  var hist_block = $('<div>').addClass('hist_block');
  var graphs_row = $('<tr>').addClass("hist graph")
      .append($('<td>').addClass("axis")
              .append(hist_block));
  var descs_row = $('<tr>').addClass("hist desc").append('<td>');
  $('#histogram').empty().append($('<table>').append(graphs_row).append(descs_row));
  var atitle = $('<span>').text(maxcount);
  atitle.css('position', 'absolute').css('top', '0px');
  hist_block.append(atitle);
  hist_block.css('width', atitle.css('width'));
  hist_block.css('padding-left', '1px').css('padding-right', '1px');
  // create display of histogram
  var barwidth = 10;
  var chart_height = Number(hist_block.css('height').replace('px',''));
  var display_f = function(_v) {
    return Math.pow(_v, 3 / 4);
  };
  var scale = chart_height * 1.0 / display_f(maxcount);
  var hist, range, td, values, previous_j, _left, v, height;
  function valuesForHist(h) {
    function m(v, i) {
      return v ? i : undefined;
    }
    function f(v) {return v!== undefined;}
    return h.map(m).filter(f);
  }
  for (i in hists) {
    hist = hists[i];
    range = ranges[i];
    td = $('<td>').appendTo(descs_row);
    if (range.min == range.max) {
      td.append(range.min);
    } else {
      td.append(range.min + ' - ' + range.max);
    }
    td = $('<td>').attr('title', range.count).appendTo(graphs_row);
    hist_block = $("<div>").addClass("hist_block").appendTo(td);
    values = valuesForHist(hist);
    values.sort(numerical);
    previous_j = null;
    _left = 0;
    for (var k in values) {
      j = values[k];
      v = hist[j];
      v.sort();
      height = display_f(v.length) * scale;
      if (previous_j !== null) {
        _left += (smooth(j - 1) - smooth(previous_j)) * barwidth;
      }
      $('<div>')
          .addClass('bar')
          .attr('title', j + ': ' + v.join(' ') + ' (' + v.length + ')')
          .css({
            top: chart_height - height + 'px',
            width: barwidth - 2 + 'px',
            height: height - 1 + 'px',
            left: Number(_left).toFixed(1) + 'px'
          })
          .appendTo(hist_block);
      previous_j = j;
      _left += barwidth;
    }
    hist_block.css("width", Number(_left).toFixed(1) + 'px');
  }
}

$(renderPlot);
