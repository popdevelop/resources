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
        GMap.clearMarkers();
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

var Search = {
    _lastQry: "",
    //Objects
    $canvas: false,
    $input: false,
    $results: false,
    init: function(search_id) {
        Search.$canvas = $(search_id);
        if(!Search.$canvas) {
            throw("[Search init] Failed to init search");
        }
        // Create UI
        Search.$input = $('<input>')
            .attr('id', 'search')
            .attr('type', 'text');
        Search.$results = $('<ul>')
            .attr('id', 'stops');
        $('<form>')
            .attr('id', 'searchform')
            .append(Search.$input)
            .appendTo(Search.$canvas);
        Search.$canvas.append(Search.$results);
    },
    send: function() {
        var qry = escape(Search.$input.val());
        if(qry.length < 3 || qry == Search._lastQry) return;
        Search._lastQry = qry;
        Cmd.send('searchStops', {
            data: {q: qry},
            success: Search.display,
            callbackParameter: 'callback'
        });
    },
    clear: function() {
        Search.$input.val('');
        Search.$results.empty();
    },
    display: function(json) {
        Search.$results.html($('#stopItem').tmpl(json)) ;
        GMap.addMarkers(json);
        GMap.set(json[0]);
        GMap.autoZoom();
    }
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

var timer = false;

$(document).ready(function() {
    GMap.init('#map_canvas');
    Search.init('#search');
    TimeTable.init('#timetable');
    $("#stops li").live("click", function(e) {
        var item = $.tmplItem(e.target);
        GMap.set({lat: item.data.lat, lon: item.data.lon, zoom: 15});
        GMap.displayInfo(item.data.key, item.data.name)
        TimeTable.fetch(item.data.key);
    });

    $("#search").bind("keyup", function() {
        clearTimeout(timer);
        timer = setTimeout(Search.send, 300);
    });

    $("#searchform").submit(function(e) {
        e.preventDefault();
        return false;
    });
});
