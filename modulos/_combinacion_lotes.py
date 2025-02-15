import streamlit as st
import shapely.wkt as wkt
import folium
import pandas as pd
import geopandas as gpd
import json
import random
import base64
import urllib.parse
from shapely.geometry import Polygon
from streamlit_folium import st_folium
from folium.plugins import Draw
from datetime import datetime

from functions._principal_getcombinacionlotes import main as getcombinacionlotes

def main(grupo=None,screensize=1920):

    try:    mapwidth = int(screensize)
    except: mapwidth = 1920

    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'polygon_combinacion_lotes_default':None,
               'zoom_start_data_combinacion_lotes_default':12,
               'latitud_combinacion_lotes_default':4.652652, 
               'longitud_combinacion_lotes_default':-74.077899,
               'mapkey':None,
               'token':None,
               'id_consulta':None,
               'favorito':False,
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    if st.session_state.mapkey is None:
        keytime  = datetime.now().strftime('%Y%m%d%H%M%S%f')
        keyvalue = random.randint(10000, 99999)
        st.session_state.mapkey = f'map_{keytime}{keyvalue}'
        
    #-------------------------------------------------------------------------#
    # Mapa
    if grupo is not None:
        data_general = getcombinacionlotes(grupo)
        datagroup    = pd.DataFrame()
        
        if not data_general.empty:
            col1,col2 = st.columns([0.6,0.4])
            
            if 'latitud' in data_general and 'longitud' in data_general:
                st.session_state.latitud_combinacion_lotes_default  = data_general['latitud'].median()
                st.session_state.longitud_combinacion_lotes_default = data_general['longitud'].median()
                st.session_state.zoom_start_data_combinacion_lotes_default = 18
                
            with col1:
                m = folium.Map(location=[st.session_state.latitud_combinacion_lotes_default, st.session_state.longitud_combinacion_lotes_default], zoom_start=st.session_state.zoom_start_data_combinacion_lotes_default,tiles="cartodbpositron")
                
                if not data_general.empty:
                    draw = Draw(
                                draw_options={"polyline": False,"marker": False,"circlemarker":False,"rectangle":False,"circle":False},
                                edit_options={"poly": {"allowIntersection": False}}
                                )
                    draw.add_to(m)
                
                #-------------------------------------------------------------#
                # Seleccion de lotes
                if not data_general.empty and st.session_state.polygon_combinacion_lotes_default is not None:
                    geojson,datagroup = data2geopandas_lotes_seleccion(data_general,str(st.session_state.polygon_combinacion_lotes_default))
                    folium.GeoJson(geojson,style_function=style_function_geojson_dash).add_to(m)
                    
                #-------------------------------------------------------------#
                # Lotes
                if not data_general.empty:
                    geojson = data2geopandas_lotes(data_general)
                    folium.GeoJson(geojson,style_function=style_function_color).add_to(m)

                st_map = st_folium(m,width=int(mapwidth*0.6),height=700,key=st.session_state.mapkey)
    
                if 'all_drawings' in st_map and st_map['all_drawings'] is not None:
                    if st_map['all_drawings']!=[]:
                        if 'geometry' in st_map['all_drawings'][0] and 'type' in st_map['all_drawings'][0]['geometry'] and "Polygon" in st_map['all_drawings'][0]['geometry']['type']:
                            coordenadas                                        = st_map['all_drawings'][0]['geometry']['coordinates']
                            st.session_state.polygon_combinacion_lotes_default = Polygon(coordenadas[0])
                            st.rerun()
                       
            if not datagroup.empty:
                with col2:
                    htmlrender = buildtable(datagroup)
                    st.components.v1.html(htmlrender, height=400)

                    urlexport = "http://www.urbex.com.co/Reporte"
                    params       = {'type':'predio','grupo':datagroup['grupo'].iloc[0],'barmanpre':datagroup['barmanpre'].iloc[0],'token':st.session_state.token}
                    params       = json.dumps(params)
                    params       = base64.urlsafe_b64encode(params.encode()).decode()
                    params       = urllib.parse.urlencode({'token': params})
                    urllink      = f"{urlexport}?{params}"

                    st.markdown(
                        """
                    <style>
                    .button {
                        background-color: #A16CFF;
                        font-weight: bold;
                        width: 100%;
                        border: 2px solid #A16CFF;
                        color: white;  /* Asegúrate de que el color del texto sea blanco */
                        text-align: center;
                        padding: 10px;
                        border-radius: 5px;
                        text-decoration: none;
                        display: inline-block;
                    }
                    .button:hover {
                        background-color: #A16CFF;
                        font-weight: bold;
                        width: 100%;
                        border: 2px solid #A16CFF;
                        color: white;  /* Asegúrate de que el color del texto sea blanco */
                        text-align: center;
                        padding: 10px;
                        border-radius: 5px;
                        text-decoration: none;
                        display: inline-block;
                    }
                    .button:active {
                        background-color: #A16CFF;
                        font-weight: bold;
                        width: 100%;
                        border: 2px solid #A16CFF;
                        color: white;  /* Asegúrate de que el color del texto sea blanco */
                        text-align: center;
                        padding: 10px;
                        border-radius: 5px;
                        text-decoration: none;
                        display: inline-block;
                    }
                    </style>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    # Botón usando Markdown con el estilo CSS
                    st.markdown(f'<a href="{urllink}" class="button" style="color:white;" target="_blank">Detalle del terreno</a>', unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def data2geopandas_lotes(data):
    data      = data[['wkt']]
    geojson   = pd.DataFrame().to_json()
    if 'wkt' in data: 
        data = data[data['wkt'].notnull()]
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['color']    = '#003F2D' #'#003F2D'
        geojson = data.to_json()
    return geojson

@st.cache_data(show_spinner=False)
def data2geopandas_lotes_seleccion(dataorigen,poligono):
    geojson   = pd.DataFrame().to_json()
    datagroup = pd.DataFrame(columns=['isin','preaconst', 'preaterre', 'predios', 'connpisos', 'connsotano', 'prevetustzmin', 'prevetustzmax', 'estrato', 'areapolygon', 'esquinero', 'tipovia', 'propietarios', 'avaluo_catastral', 'impuesto_predial','lotes'])
    if 'wkt' in dataorigen: 
        dataorigen = dataorigen[dataorigen['wkt'].notnull()]
    if not dataorigen.empty:
        data             = dataorigen[['wkt']]
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        poligono         = wkt.loads(poligono)
        idd              = data['geometry'].apply(lambda x: poligono.contains(x))
        data             = data[idd]
        dataorigen       = dataorigen[idd]
        
        data['color']      = '#003F2D'
        geojson            = data.to_json()
        dataorigen['isin'] = 1
        datagroup          = dataorigen.groupby('isin').agg({'preaconst':'sum','preaterre':'sum','predios':'sum','connpisos':'max','connsotano':'max',
                                                 'prevetustzmin':'min','prevetustzmax':'max','estrato':'max','areapolygon':'sum',
                                                 'esquinero':'max','tipovia':'min','propietarios':'sum','avaluo_catastral':'sum',
                                                 'impuesto_predial':'sum','barmanpre':'nunique'}).reset_index()
        datagroup.columns = ['isin','preaconst', 'preaterre', 'predios', 'connpisos', 'connsotano', 'prevetustzmin', 'prevetustzmax', 'estrato', 'areapolygon', 'esquinero', 'tipovia', 'propietarios', 'avaluo_catastral', 'impuesto_predial','lotes']
    
        for i in ['grupo','barmanpre']:
            datamerge    = dataorigen.copy()
            datamerge[i] = datamerge[i].astype(str)
            datamerge    = datamerge.groupby('isin')[i].agg(lambda x: '|'.join(x)).reset_index()
            datamerge.columns = ['isin',i]
            datagroup    = datagroup.merge(datamerge,on='isin',how='left',validate='1:1')
            
    return geojson,datagroup

def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }

def style_function_geojson_dash(feature):
    return {
        'fillColor': 'green',
        'color': 'blue',
        'weight': 1, 
        'dashArray': '5, 5',
        'fillOpacity': 0.2,
    }

def buildtable(data):
    
    
    sections_html = ""
    esquinero     = 'Si' if 'esquinero' in data and isinstance(data['esquinero'].iloc[0],(float,int)) and data['esquinero'].iloc[0]==1 else 'No'
    viaprincipal  = 'Si' if 'tipovia' in data and isinstance(data['tipovia'].iloc[0],(float,int)) and data['tipovia'].iloc[0]==1 else 'No'
    
    try: areaterreno = "{:,.2f}".format(max(data['areapolygon'].iloc[0], data['preaterre'].iloc[0]))
    except: 
        try: areaterreno = "{:,.2f}".format(data['areapolygon'].iloc[0])
        except: 
            try: areaterreno = "{:,.2f}".format(data['preaterre'].iloc[0])
            except: areaterreno = None
        
    formato = [{'seccion':'Terreno consolidado','items':[
                {'titulo':'# Lotes:','valor':"{:,.0f}".format(data['lotes'].iloc[0]) if not data.empty and 'lotes' in data else None},
                {'titulo':'Área del terreno:','valor':areaterreno },
                {'titulo':'Área total construida:','valor':"{:,.2f}".format(data['preaconst'].iloc[0]) if not data.empty and 'preaconst' in data else None},
                {'titulo':'# Predios:','valor':"{:,.0f}".format(data['predios'].iloc[0]) if not data.empty and 'predios' in data else None},
                {'titulo':'Máximo de pisos:','valor':"{:,.0f}".format(data['connpisos'].iloc[0]) if not data.empty and 'connpisos' in data else None},
                {'titulo':'Máximo de sotanos:','valor':"{:,.0f}".format(data['connsotano'].iloc[0]) if not data.empty and 'connsotano' in data else None},
                {'titulo':'Estrato:','valor':"{:,.0f}".format(data['estrato'].iloc[0]) if not data.empty and 'estrato' in data else None},
                {'titulo':'Antigüedad mínima:','valor':"{:.0f}".format(data['prevetustzmin'].iloc[0]) if not data.empty and 'prevetustzmin' in data else None},
                {'titulo':'Antigüedad máxima:','valor':"{:.0f}".format(data['prevetustzmax'].iloc[0]) if not data.empty and 'prevetustzmax' in data else None},
                {'titulo':'Esquinero:','valor':esquinero},
                {'titulo':'Sobre vía principal:','valor':viaprincipal},           
                {'titulo':'','valor':''},
                {'titulo':'Avaúo catastral total','valor':"${:,.0f}".format(data['avaluo_catastral'].iloc[0]) if not data.empty and 'avaluo_catastral' in data and isinstance(data['avaluo_catastral'].iloc[0],(float,int)) else None},        
                {'titulo':'Impuesto predial total','valor':"${:,.0f}".format(data['impuesto_predial'].iloc[0])if not data.empty and 'impuesto_predial' in data and isinstance(data['impuesto_predial'].iloc[0],(float,int)) else None},        
                {'titulo':'Propietarios total','valor':"{:,.0f}".format(data['propietarios'].iloc[0]) if not data.empty and 'propietarios' in data and isinstance(data['propietarios'].iloc[0],(float,int)) else None},        
                               ]},
        
            ]
    
    
    for section in formato:
        section_title = section["seccion"]
        items = section["items"]
        
        # Determinar si la sección contiene listas verificando el primer item
        contains_list = any(isinstance(item.get("valor"), list) for item in items)
        
        if not contains_list and isinstance(items,list) and items!=[]:
            sections_html += f'''
            <div class="urbex-row">
             <div class="urbex-col">
              <div class="urbex-h-100 urbex-p-3" id="box_shadow_default">
               <h1 class="urbex-mt-2" id="title_inside_table">
                {section_title}
               </h1>
               <div class="urbex-table-responsive urbex-flex-grow-1" style="line-height: 0.5;">
                <table class="urbex-table urbex-table-sm urbex-table-borderless">
                 <tbody>
            '''
            for item in items:
                value  = item["valor"] if "valor" in item else None
                value  = 'Sin información' if value is None else value
                titulo = item["titulo"] if 'titulo' in item else ''
                
                is_empty    = True if "titulo" in item and ((isinstance(item["titulo"],str) and item["titulo"]=='') or item["titulo"] is None) else False
                title_style = 'color: #666666; font-weight: bold;' if is_empty else ''
                if is_empty:
                    sections_html += """<tr><td colspan="2" style="padding: 0.5rem;"></td></tr>"""
                    titulo         = value
                    value          = ''
                
                sections_html += f'''
                                <tr>
                                <td style="padding: 0.1rem; vertical-align: top; line-height: 1;><span id="label_inside" style="{title_style}">{titulo}</span></td>
                                <td style="padding: 0.1rem; vertical-align: top; line-height: 1;><span id="value_inside">{value}</span></td>
                                </tr>'''
            
            sections_html += '''
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>'''
       
        
    sections_html = f"""
    <section>
     <div class="urbex-container-fluid">
         {sections_html}
     </div>
    </section>
    """
    
    
    html = f"""
    <!DOCTYPE html>
    
    <html data-bs-theme="light" lang="en">
    <head>
    <meta charset="utf-8"/>
    <meta content="width=device-width, initial-scale=1.0, shrink-to-fit=no" name="viewport"/>
    <title>urbex_consolidacion_lotes</title>
    <link href="https://iconsapp.nyc3.digitaloceanspaces.com/_estilo_general/prefixed_bootstrap.min.css" rel="stylesheet"/>
    <link href="https://iconsapp.nyc3.digitaloceanspaces.com/_estilo_general/prefixed_styles.css" rel="stylesheet"/>
    </head>
    <body>
    {sections_html}
    </body>
    </html>
    """
    return html
