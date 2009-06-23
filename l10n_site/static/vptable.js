(function($) {
  var defaults = {
    'width': 10,
    'items': Array(),
  }
  
  function addInPos(tr, td, pos) {
  }

  $.vpTable = function(tableNode, options) {
    var opts = $.extend({}, defaults, options)
    var node = tableNode

    return {
      draw: function(offset, customRow, cb) {
        if (!offset) offset=0
      
        function draw(slice, cb) {
          //var tr = $('tr.revision', node)
          //tr.empty()
          $('tr', node).empty()
          for (var i in slice) {
            var item = slice[i]
            //var tr = $('tr.revision', node)
            //if (item['domobj']) {
            //  var td = item['domobj']
            //} else {
            //  var td = $('<td/>').text(item)
            //  item['domobj'] = td
            //}
            //td.appendTo(tr)
            for (var attr in item) {
              tr = $('tr.'+attr, node)
              if (tr) {
                var td = $('<td/>').addClass('item-'+item.id)
                customRow(node, attr, td, item)
                td.appendTo(tr)
              }
            }
          }
          if (cb) cb()
        }
        opts['items'].get(offset, offset+opts['width'], draw, cb)
      }
    }
  }
})(jQuery);
