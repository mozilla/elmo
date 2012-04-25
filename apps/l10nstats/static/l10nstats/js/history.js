/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

var timeplot, timeGeometry;

function onLoad() {
  var eventSource = new Timeplot.DefaultEventSource();
  var eventSource2 = new Timeplot.DefaultEventSource();
  timeGeometry = new Timeplot.MagnifyingTimeGeometry({
    gridColor: new Timeplot.Color('#000000'),
    axisLabelsPlacement: 'top'
  });

  var valueGeometry = new Timeplot.DefaultValueGeometry({
    gridColor: '#000000',
    min: 0,
    axisLabelsPlacement: 'left'
  });
  var valueGeometry2 = new Timeplot.DefaultValueGeometry({
    gridColor: '#000000',
    min: 0
  });
  var plotInfo = [
    Timeplot.createPlotInfo({
      id: 'checkins',
      timeGeometry: timeGeometry,
      eventSource: eventSource2,
      lineColor: 'blue'
    }),
    Timeplot.createPlotInfo({
      id: 'unchanged',
      dataSource: new Timeplot.ColumnSource(eventSource, 3),
      valueGeometry: valueGeometry2,
      timeGeometry: timeGeometry,
      lineColor: '#cccccc',
      fillColor: '#cccccc',
      flat: true,
      showValues: true
    }),
    Timeplot.createPlotInfo({
      id: 'obsolete',
      dataSource: new Timeplot.ColumnSource(eventSource, 2),
      valueGeometry: valueGeometry,
      timeGeometry: timeGeometry,
      lineColor: '#000000',
      fillColor: '#808080',
      flat: true,
      showValues: true
    }),
    Timeplot.createPlotInfo({
      id: 'missing',
      dataSource: new Timeplot.ColumnSource(eventSource, 1),
      valueGeometry: valueGeometry,
      timeGeometry: timeGeometry,
      lineColor: '#ff0000',
      fillColor: 'rgba(204, 128, 128, .5)',
      flat: true,
      showValues: true
    })
  ];

  timeplot = Timeplot.create(document.getElementById('my-timeplot'), plotInfo);
  //timeplot.loadText('nl.txt', ',', eventSource);
  eventSource.loadText($('#txtData').text(), ',', String(document.location));
  //timeplot.loadXML('nl-events.xml', eventSource2);
  //eventSource2.loadXML({documentElement:$('#events').children()[0]},
  //                     String(document.location));
  timeplot.repaint();
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

$(function() {
  onLoad();
  $(window).resize(onResize);
});
