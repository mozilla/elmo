(function($) {
  var defaults = {
    'json_url': '',
    'json_items': 'items',
    'length': 10,
    'length_url': '',
  }

  $.AjaxArray = function(options, pitems) {
    var opts = $.extend({}, defaults, options)
    var items = Array()

    for (var i in pitems) {
      items[i] = pitems[i]
    }

    function get(from, to) {
      return items.slice(from, to)
    }

    function loadMissing(from, to, cb) {
      $.getJSON(opts['json_url'].replace('$1',from).replace('$2',to+1),
        function(data){
          $.each(data[opts['json_items']], function(i, item){
            items[from+i] = item
          })
          if (cb) cb(get(from, to))
        }
      )
    }
    
    function getLength(force, N) {
      return opts['length']
    }

    return {
      get: function (from, to, cb) {
        var lseq = false
        var rseq = false
        for (var i=from;i<to&&lseq===false;i++) {
          if (!items[i])
            lseq = i
        }
        for (var i=to;i>=from-lseq&&rseq===false;i--) {
          if (!items[i])
            rseq = i
        }
        if (lseq!==rseq)
          loadMissing(lseq, rseq, cb)
        else
          if (cb) cb(get(from, to))
      },
      length: getLength,
    }
  }
})(jQuery);
