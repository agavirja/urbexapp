import streamlit as st

@st.cache_data
def mapstreetview(latitud,longitud):
    html = ""
    if (isinstance(latitud, float) or isinstance(latitud, int)) and (isinstance(longitud, float) or isinstance(longitud, int)):
        style = """
        <style>
            #map-container {
                width: 100%;
                height: 450px;
            }
        </style>
        """
        streetview = """
        <script>
            function initMap() {
                var latitud = latitud_replace;
                var longitud = longitud_replace;
                var latLng = new google.maps.LatLng(latitud, longitud);
                var panoramaOptions = {
                    position: latLng,
                    pov: {
                        heading: 0, // Dirección inicial
                        pitch: 0 // Ángulo de inclinación inicial
                    },
    
                };
                var panorama = new google.maps.StreetViewPanorama(
                    document.getElementById('map-container'),
                    panoramaOptions
                );
                var map = new google.maps.Map(document.getElementById('map-container'), {
                    streetView: panorama
                });
            }
        </script>
        <script src="https://maps.googleapis.com/maps/api/js?key=AIzaSyBEjvAMTg70W6oUvWc5HzYUS3O9rzEI9Jw&callback=initMap" async defer></script>                          
        """
        streetview = streetview.replace('latitud_replace',str(latitud)).replace('longitud_replace',str(longitud))
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="UTF-8">
          <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/nucleo-icons.css" rel="stylesheet">
          <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/nucleo-svg.css" rel="stylesheet">
          <link id="pagestyle" href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/soft-ui-dashboard.css?v=1.0.7" rel="stylesheet">
          {style}
        </head>
        <body>
        <div id="map-container"></div>
          {streetview}
        </div>    
        </body>
        </html>
        """
    return html
    
@st.cache_data
def mapsatelite(latitud,longitud):
    html = ""
    if (isinstance(latitud, float) or isinstance(latitud, int)) and (isinstance(longitud, float) or isinstance(longitud, int)):
        style = """
        <style>
            #map-container {
                width: 100%;
                height: 450px;
            }
        </style>
        """
        
        map_view = """
        <script>
            function initMap() {
                var latitud = latitud_replace;
                var longitud = longitud_replace;
                var mapOptions = {
                    center: {lat: latitud, lng: longitud},
                    zoom: 20, 
                    mapTypeId: google.maps.MapTypeId.SATELLITE
                };
                var map = new google.maps.Map(document.getElementById('map-container'), mapOptions);
            }
        </script>
        <script src="https://maps.googleapis.com/maps/api/js?key=AIzaSyBEjvAMTg70W6oUvWc5HzYUS3O9rzEI9Jw&callback=initMap" async defer></script>                          
        """
        map_view = map_view.replace('latitud_replace', str(latitud)).replace('longitud_replace', str(longitud))
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="UTF-8">
          <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/nucleo-icons.css" rel="stylesheet">
          <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/nucleo-svg.css" rel="stylesheet">
          <link id="pagestyle" href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/soft-ui-dashboard.css?v=1.0.7" rel="stylesheet">
          {style}
        </head>
        <body>
        <div id="map-container"></div>
          {map_view}
        </div>    
        </body>
        </html>
        """
    return html
