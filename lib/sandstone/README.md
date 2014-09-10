Sandstone
=========

Sandstone is a bootstrap for sites in the Mozilla Universe. Download 
and installation instructions are available on 
[GitHub](https://github.com/ossreleasefeed/Sandstone/). The
``templates`` folder contains the base Django template and the 
``static`` folder contains CSS, JS, fonts and images.

In Elmo, slightly modified Sandstone is used. To make updates easier, 
we're keeping the original copy here with instructions on how to 
process it to make it work with Elmo.


CSS
---

All Sandstone .less files are replaced with one preprocessed .css file 
instead. Before [preprocessing](http://lesstocss.com/), .less files 
need to be joined in the following order:

* lib.less
* reset.less
* fonts.less
* buttons.less
* video-resp.less
* sandstone-resp.less

There are some edits made, namely

* replace /media/ with /static/ in all .less files
* locale-specific hacks removed in buttons.less
* locale-dependent fonts removed in lib.less
* locale-specific hacks removed in sandstone-resp.less
* add video-resp to sandstone-resp for easier processing


Fonts
-----

Some font references in CSS don't have corresponding font files. It's 
3 different font faces in 4 different formats each (12 files):

* OpenSans-LightItalic-webfont.*
* OpenSans-Bold-webfont.*
* OpenSans-Italic-webfont.*

These fonts were downloaded from 
[Bedrock](https://github.com/mozilla/bedrock/).


Images
------

Unused Sandstone icons are removed (e.g. Aurora logos). We're keeping 
alternative backgrounds and common icons for now. We might need them 
later and don't want to look for 3rd party ones instead.
