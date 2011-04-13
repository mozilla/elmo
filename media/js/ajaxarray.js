(function($) {
  var defaults = {
    'json_url': '',
    'json_items': 'items',
    'length': 10,
    'length_url': '',
    'buffer': 10,
  }

  // scans an array looking for a first element missing
  function array_scan(slice, pt, dir) {
    if (pt>slice.length) return pt
    for (var i=pt;i<=slice.length&&i>=0;i+=dir)
      if (slice[i]===undefined)
        return i
    return null
  }

  $.AjaxArray = function(options, pitems) {
    var opts = $.extend({}, defaults, options)
    var items = Array()
    var loading = false

    for (var i in pitems[0]) {
      items[parseInt(i)+parseInt(pitems[1])] = pitems[0][i]
    }

    function get(from, to) {
      return items.slice(from, to)
    }

    function loadMissing(from, to, cb, cbarg, cbf, cbt) {
      if (loading)
        return
      loading = true
      $.getJSON(opts['json_url'].replace('$1',from).replace('$2',to),
        function(data){
          $.each(data[opts['json_items']], function(i, item){
            items[from+i] = item
          })
          loading = false
          if (cb) cb(get(cbf, cbt), cbarg)
        }
      )
    }
    
    function getLength(force, N) {
      return opts['length']
    }

    return {
      get: function(from, to, cb, cbarg) {
        var buf = opts['buffer']
        var lseq = array_scan(items, Math.max(from-buf,0), 1)
        var rseq = array_scan(items, Math.min(to+buf, opts['length']-1), -1) 
        if (lseq!==null && rseq!==null && lseq!==rseq && (rseq>=from && lseq<=to))
          loadMissing(lseq, rseq, cb, cbarg, from, to)
        else
          if (cb) cb(get(from, to), cbarg)
      },
      get_current: function() {
        for (var i in items) {
          if (items[i] && items[i]['signoff'])
            return i
        }
        return null
      },
      length: getLength,
    }
  }
})(jQuery);
