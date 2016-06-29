/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

function renderPlot() {
  var tp = timeplot("#my-timeplot",
                    fullrange,
                    [startdate, enddate],
                    {tree: tree, locale: locale});
  var svg = tp.svg;
  var defs = svg.append("defs");

  function genGradient(id, data) {
    return defs.append("linearGradient")
    .attr("id", id)
    .attr("x2", "0")
    .attr("y2", "100%")
    .selectAll("stop")
    .data(data)
    .enter()
    .append("stop")
    .attr("offset", function (d) {return d.offset;})
    .attr("stop-color", function (d) {return d.color;})
    .attr("stop-opacity", function (d) {return d.opacity;});
  }

  mg = genGradient("missingGradient", [
      {offset: "5%", color: "rgb(204, 128, 128)", opacity: ".8"},
      {offset: "95%", color:"rgb(204, 128, 128)", opacity: ".2"}
           ]);
  og = genGradient("obsoleteGradient", [
      {offset: "5%", color: "#808080", opacity: ".8"},
      {offset: "95%", color:"#808080", opacity: ".2"}
           ]);
  ug = genGradient("unchangedGradient", [
      {offset: "5%", color: "#cccccc", opacity: ".8"},
      {offset: "65%", color:"#cccccc", opacity: ".1"}
           ]);
  var missingArea = d3.svg.area()
    .interpolate("step-after")
    .x(function(d) { return tp.x(d.date); })
    .y0(tp.height)
    .y1(function(d) { return tp.y(d.missing); });
  var obsoleteArea = d3.svg.area()
    .interpolate("step-after")
    .x(function(d) { return tp.x(d.date); })
    .y0(tp.height)
    .y1(function(d) { return tp.y(d.obsolete); });
  var unchangedArea = d3.svg.area()
    .interpolate("step-after")
    .x(function(d) { return tp.x(d.date); })
    .y0(tp.height)
    .y1(function(d) { return tp.y2(d.unchanged); });

  function processRow(row, i) {
    return {
      date: d3.time.format.iso.parse(row[0]),
      run: +row[1],
      missing: +row[2],
      obsolete: +row[3],
      unchanged: +row[4]
    };
  }
  data = d3.csv.parseRows($("#txtData").text().trim(), processRow);
  tp.yDomain([0, d3.max(data.map(function(d) { return d3.max([d.missing, d.obsolete]); }))]);
  tp.y2Domain([0, d3.max(data.map(function(d) { return d.unchanged; }))]);
  svg.selectAll("rect.high")
    .data(Array.from(document.querySelectorAll('.highlight')))
    .enter()
    .append('rect')
    .attr('class', 'high')
    .attr("x", function(e){
      return tp.x(d3.time.format.iso.parse(e.dataset.start));
    })
    .attr("y", 0)
    .attr("height", tp.height)
    .attr("width", function(e) {
      return tp.x(d3.time.format.iso.parse(e.dataset.end)) - tp.x(d3.time.format.iso.parse(e.dataset.start))
    })
    .attr("stroke", "none").attr("fill", function(e) {
      return '#' + e.dataset.color;
    });
  svg.append("path")
    .data([data])
    .attr("d", unchangedArea)
    .attr("class", "unchanged-graph")
    .attr("stroke", "#cccccc")
    .attr("fill", "url(#unchangedGradient)");
  svg.append("path")
    .data([data])
    .attr("d", obsoleteArea)
    .attr("class", "obsolete-graph")
    .attr("stroke", "#808080")
    .attr("fill", "url(#obsoleteGradient)");
  svg.append("path")
    .data([data])
    .attr("d", missingArea)
    .attr("class", "missing-graph")
    .attr("stroke", "red")
    .attr("fill", "url(#missingGradient)");
  var markers = svg.selectAll('a.marker')
    .data(data.slice(0, -1))
    .enter()
    .append('svg:a')
    .attr('class','marker missing')
    .attr('xlink:href', function(d) {return compare_link + '?run=' + d.run;})
    .attr('xlink:show', 'new');
  markers.append('path')
    .attr('transform',
          function(d) {
            return "translate(" + tp.x(d.date) + "," + tp.y(d.missing) + ")";
            })
    .attr("d", d3.svg.symbol().type('circle'))
  markers.append('title').text(function(d) {return 'missing: ' + d.missing;});
}

$(renderPlot);
