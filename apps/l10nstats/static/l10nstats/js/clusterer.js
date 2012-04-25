/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

var Clusterer = function (data, smoothing_function) {
  this._data = data
  this._clusters = []
  this._smooth = smoothing_function || Math.log
  
  this._flatten = function (a) {
    // Flattens an array so that there are no noested arrays inside it.
    var flat = []
    for (var i = 0; i < a.length; i++) {
      if (a[i].constructor == Array) {
        flat = flat.concat(this._flatten(a[i]))
      }
      else
        flat.push(a[i])
    }
    return flat.sort(function (a, b) {
      return a - b
    })
  }
  
  this._smooth_distance = function (a, b) {
    // Calculate the distance between two numbers using
    // a smoothing function to scale big numbers down.
    return Math.abs(this._smooth(a + 1) - this._smooth(b + 1))
  }
  
  this._distance = function (a, b) {
    // 'Complete linkage' distance for one-dimensional variables. 
    // Returns the biggest distance between members of one cluster 
    // and members of the other cluster.
    return Math.max(this._smooth_distance(a[a.length - 1], b[0]), 
                    this._smooth_distance(b[b.length - 1], a[0]))
  }
  
  this._get_min_distance = function (prev_min_distance) {
    // Finds two clusters which are the closest to each other.
    // Returns the distance and the indexes of the clusters.
    var total = this._clusters.length
    var current_min = {value: Infinity, i: null, j: null}
    for (var i = 0; i < total; i++) {
      for (var j = i + 1; j < total; j++) {
        var distance = this._distance(this._clusters[i], this._clusters[j])
        // We can short-circuit the loops if the distance between 
        // cluster 'i' and cluster 'j' is equal to the smallest
        // distance found in the  previous iteration ('prev_min_distance')
        if (distance == prev_min_distance) {
          return {value: distance, i: i, j: j}
        }
        if (distance < current_min.value) {
          current_min = {value: distance, i: i, j: j}
        }
      }
    }
    return current_min
  }
  
  this._merge = function (i, j) {
    // Merge the two closest clusters, remove them from the cluster set
    // and add the new cluster to the set.
    var new_cluster = this._flatten([this._clusters[i], this._clusters[j]])
    this._clusters.splice(Math.max(i, j), 1)
    this._clusters.splice(Math.min(i, j), 1)
    this._clusters.push(new_cluster)
  }
  
  this.get_clusters = function (level, clusters_max) {
    // Return an array of clusters in which all clusters
    // consist of elements at most 'level' units distant
    // from each other.
    this._clusters = [[item] for each (item in this._data)]
    if (!clusters_max) clusters_max = 10
    var closest = this._get_min_distance(0)
    while (this._clusters.length > clusters_max || closest.value <= level) {
      this._merge(closest.i, closest.j)
      closest = this._get_min_distance(closest.value)
    }
    return this._clusters.sort(function(a, b) {
      return a[0] - b[0]
    })
  }
  
  this.get_ranges = function (level) {
    // Return cluster ranges with number of elements in each cluster.
    // The 'level' argument is optional. If not specified, 
    // ranges will be generated from the previously computed
    // clusters.
    if (this._clusters.length == 0 && !level) {
      throw "Either clusters need to be previously computed, or 'level' argument needs to be passed."
    }
    var clusters = level ? this.get_clusters(level) : this._clusters
    var ranges = []
    for (var cluster, i = 0; cluster = clusters[i]; i++) {
      ranges.push({
        min: cluster[0],
        max: cluster[cluster.length-1],
        count: cluster.length 
      })
    }
    return ranges
  }
}
