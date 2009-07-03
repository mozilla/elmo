function Slider(obj) {
  var self
  var swidth = 100
  var length=10
  var vis=10
  var mpos = 0
  var slider
  var marker
  var I=null
  var ch = null
  var cb=null

  return self = {
    setUp: function(o, len, start, callback) {
      slider = o
      marker = o.getElementsByClassName('marker')[0]
      var next = o.getElementsByClassName('next')[0]
      var prev = o.getElementsByClassName('prev')[0]
      length = len
      cb = callback
      mpos = start
      self.redrawMarker()
      $(next).mousedown(self.onNext)
      $(next).mouseup(self.mouseUp)
      $(next).mouseout(self.mouseUp)
      $(prev).mousedown(self.onPrev)
      $(prev).mouseup(self.mouseUp)
      $(prev).mouseout(self.mouseUp)
      $(marker).mousedown(self.markerDown)
      $(marker).mouseup(self.markerUp)
    },
    onNext: function() {
      ch = 1
      if (!I)
        I = setInterval(self.buttonPressed, 10)
      self.buttonPressed()
    },
    onPrev: function() {
      ch = -1
      if (!I)
        I = setInterval(self.buttonPressed, 10)
      self.buttonPressed()
    },
    buttonPressed: function () {
      if (mpos+ch<0 || mpos+vis+ch>length) {
        I = clearInterval(I)
        return
      }
      if (!cb || cb(self.redrawMarker)) {
        self.redrawMarker()
      }
    },
    mouseUp: function() {
      I = clearInterval(I)
    },
    markerDown: function() {
      if (!I)
        I = setInterval(self.markerPressed, 2000)
      return false;
    },
    markerPressed: function() {
      alert(marker.clientX)
    },
    markerUp: function() {
      I = clearInterval(I)
    },
    redrawMarker: function() {
      if (ch)
        mpos += ch
      var mwidth = vis/length
      marker.style.width=swidth*mwidth+'px'
      var marg = (mpos)/length*swidth
      marker.style.marginLeft=marg+'px'
    },
    status: function() {
      return {start: mpos, offset: vis, v: ch}
    }
  }
}
