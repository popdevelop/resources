String.prototype.ts2rel = function() {
    var d = new Date(this).getTime();
    var now = new Date().getTime();
    var diff = (d - now)/1000;
    if(diff < 60) {
        return "now";
    }
    return Math.floor(diff / 60) + " min";
};

var Config =  {
    server: '',
};

var Cmd = {
    send: function(cmd, params) {
        if( !(cmd in API) ) {
            throw("[API] Invalid command");
        }
        if( typeof(params) != 'object') {
            throw("[API] Invalid parameters");
        }
        params.url = Config.server + "/" + API[cmd];
        $.jsonp(params);
    }
};

var API = {
    getStops: 'neareststations',
    searchStops: 'querystation',
    stationResult: 'stationresults'
};

var GMap = {
    $canvas: false,
    _options: {
        scrollwheel: false,
        zoom: 14,
        mapTypeId: google.maps.MapTypeId.ROADMAP,
        lat: -34.397,
        lon: 150.644
    },
    _markers: [],
    _bounds: false,
    _info: false,
    init: function(map_id) {
        GMap.$canvas = $(map_id);
        if(!GMap.$canvas) {
            throw("[GMap init] Canvas not found");
        }
        GMap._options.center = new google.maps.LatLng(GMap._options.lat, GMap._options.lon);
        GMap.map = new google.maps.Map(GMap.$canvas.get(0), GMap._options);
    },
    set: function(options) {
        if(typeof(options) != 'object') {
            throw("[GMap set] Invalid options");
        }
        $.extend(GMap._options, options);
        GMap._options.center = new google.maps.LatLng(GMap._options.lat, GMap._options.lon);
        GMap.map.setCenter(GMap._options.center);
        GMap.map.setZoom(GMap._options.zoom);
    },
    addMarkers: function(positions) {
        GMap._bounds = new google.maps.LatLngBounds();
        for(var i in positions) {
            var p = positions[i];
            var lonlat = new google.maps.LatLng(p.lat, p.lon);
            GMap._markers[p.key] = new google.maps.Marker({
                position: lonlat, 
                map: GMap.map, 
                title: p.name
            });
            GMap._bounds.extend(lonlat);
            /*google.maps.event.addListener(GMap._markers[p.key], "click", function() {
                alert("hej");
            });*/
        }
    },
    clearMarkers: function() {
        if(GMap._info) {
            GMap._info.close();
        }
        for (var i in GMap._markers) {
            GMap._markers[i].setMap(null);
        }
        GMap._markers.length = 0;
    },
    autoZoom: function() {
        var bounds = new google.maps.LatLngBounds();
        GMap.map.fitBounds(GMap._bounds);
        GMap.map.setCenter(GMap._bounds.getCenter());
    },
    displayInfo: function(marker_id, info) {
        if(GMap._info) {
            GMap._info.close();
        }
        marker = GMap._markers[marker_id];
        if(!marker) {
            throw("[GMap displayInfo] Invalid marker");
        }
        GMap._info = new google.maps.InfoWindow(
        {
            content: info,
            position: marker.position
        });
        GMap._info.open(GMap.map);
    }
};

function Search(form_id) {
    var self = this;
    self._lastQry = "";
    self._selectedStation = false;
    //Objects
    self.$form    = false;
    self.$input   = false;
    self.$results = false;
    // Initxs
    self.$form = $(form_id);
    self.$input = $("input", self.$form);
    if(!self.$form || !self.$input) {
        throw("[Search init] Failed to init search");
    }
    
    // Create results area
    self.$results = $('<ul>')
        .hide()
        .addClass('results')
        .attr('id', form_id + '_results')
        .appendTo(self.$form);
    
    // Form actions
    self.$input.bind("keyup", function() {
        clearTimeout(timer);
        timer = setTimeout(self.send, 300);
    });
    //self.$input.bind("blur", function() { self.$results.hide(); })

    self.$form.submit(function(e) {
        e.preventDefault();
        return false;
    });

    // ------ Methods ------
    self.send = function() {
        var qry = escape(self.$input.val());
        if(qry.length < 3 || qry == self._lastQry) {
            self.$results.hide();
            return;
        }
        self._lastQry = qry;
        self.$results.show();
        Cmd.send('searchStops', {
            data: {q: qry},
            success: self.display,
            callbackParameter: 'callback'
        });
    };
    self.clear = function() {
        self.$input.val('');
        self.$results.hide().empty();
    };

    self.display = function(json) {
        self.$results.html($('#stopItem').tmpl(json));
        $("li", self.$results).click(function(e) {
            var item = $.tmplItem(e.target);
            //GMap.set({lat: item.data.lat, lon: item.data.lon, zoom: 15});
            TimeTable.fetch(item.data.key);

            self.$input.val(item.data.name);
            self._selectedStation = item.data;
            self.$results.hide();
            $(document).trigger("search.setStation");
        });
    };
};



var TimeTable = {
    $canvas: false,
    $result: false,
    init: function(tbl_id) {
        TimeTable.$canvas = $(tbl_id);
        if(!TimeTable.$canvas) {
            throw("[TimeTable init] Failed to init");
        }
        TimeTable.$result = $('<table>');
        TimeTable.$canvas.append(TimeTable.$result);
    },
    fetch: function(station_id) {
        Cmd.send('stationResult', {
            data: {s: station_id},
            success: TimeTable.display,
            callbackParameter: 'callback'
        });
    },
    display: function(json) {
        TimeTable.$result.html($('#lineItem').tmpl(json));
    }
};

var Route = {
    _from: false,
    _to: false,
    _path: false,
    init: function() {
        Route._from = new Search('#form_from');
        Route._to = new Search('#form_to');
        
        $(document).bind("search.setStation", Route.display)
    },
    display: function(points) {
        console.log("draw");
        var from = Route._from._selectedStation;
        var to   = Route._to._selectedStation
        if(from && to) {
            if(Route._path) {
                //XXX: howto remove line?
                //Route._path.removeAt();
            }
            var coords = [];
            coords.push(new google.maps.LatLng(from.lat, from.lon));
            coords.push(new google.maps.LatLng(to.lat, to.lon));
            Route._path = new google.maps.Polyline({path: coords});
            Route._path.setMap(GMap.map);
            GMap.clearMarkers();
            GMap.addMarkers([from, to]);
            GMap.autoZoom();
        }
    }
};

var timer = false;

$(document).ready(function() {
    GMap.init('#map_canvas');
    Route.init();
    TimeTable.init('#timetable');
});
