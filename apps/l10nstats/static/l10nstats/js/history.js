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
 *   Peter Bengtsson <peterbe@mozilla.com>
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
 * ***** END LICENSE BLOCK ***** */

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
