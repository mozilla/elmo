(function($) {
  var defaults = {
    'vp_width': 10,
    'items': Array(),
  }

  $.fn.vptable = function(options) {
    return this.each(function (){
      this.vpt_opts = $.extend({}, defaults, options)
    })
  }

  $.fn.vptDraw = function() {
    return this.each(function (){
      var self = this
      
      function draw(slice) {
        for (var i in slice) {
          var item = slice[i]
          for (var attr in item) {
            tr = $('tr.'+attr, self).get()[0]
            if (tr) {
              var td = $('<td/>').addClass('item-'+item.id)
              td.text(item[attr])
              td.appendTo(tr)
            }
          }
        }
      }

      self.vpt_opts['items'].get(0, 10, draw)
    }) 
  }
})(jQuery);
