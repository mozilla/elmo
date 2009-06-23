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
          $('tr', node).empty()
          for (var i in slice) {
            var item = slice[i]
            if (!item['domobj']) {
              item['domobj'] = Array()
            }
            for (var attr in item) {
              tr = $('tr.'+attr, node)
              if (tr) {
                if (item['domobj'][attr]) {
                  var td = item['domobj'][attr]
                } else {
                  var td = $('<td/>').addClass('item-'+item.id)
                  customRow(node, attr, td, item)
                  item['domobj'][attr] = td
                }
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
