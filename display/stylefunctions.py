def style_function(feature):
    return {
        'fillColor': '#0095ff',
        'color': 'blue',
        'weight': 0,
        #'dashArray': '5, 5'
    }

def style_lote(feature):
    return {
        'fillColor': '#003F2D',
        'color':'#003F2D',
        'weight': 1,
        #'dashArray': '5, 5'
    }  

def style_lote_transacciones(feature):
    return {
        'fillColor': '#33105d',
        'color':'#33105d',
        'weight': 1,
        #'dashArray': '5, 5'
    }  

def style_referencia(feature):
    return {
        'fillColor': '#B20256',
        'color':'#B20256',
        'weight': 1,
        #'dashArray': '5, 5'
    }  

def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }

def style_function_geojson(feature):
    color = feature['properties']['color']
    return {
        'fillColor': color,
        'color': color,
        'weight': 1,
        #'fillOpacity': 0.2,
    }

def style_function_geojson_icon(feature):
    icon_image = feature['properties']['icon_image']
    return {
        'icon_image':icon_image,
        'icon_size': (15, 15)
        #'fillOpacity': 0.2,
    }
