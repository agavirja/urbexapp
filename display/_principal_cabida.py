import streamlit as st
import pandas as pd
import geopandas as gpd
import html
import shapely.wkt as wkt
from shapely.geometry import Point
from bs4 import BeautifulSoup

from display._principal_cabida_mapbox_multiple import main as mapa_mapbox
from display._principal_cabida_mapbox_huella import main as mapa_mapbox_huella

from data._algoritmo_cabida  import getareapolygon

def main( info_pot, info_terreno, proporcion_areas_comunes, datapricing, data_precios_referencia, numero_pisos, alturapiso, latitud, longitud, data_lotes, data_construcciones, building_shape_geometry, poligono_lote, grid_aislamiento, data_andenes, data_vias):

    formato = []
    formato = formatoPOT(formato, info_pot)
    formato = formatoTerreno(formato, info_terreno)
    
    #-------------------------------------------------------------------------#
    # Mapa mapbox buildings
    html_mapa = mapa_mapbox(alturapiso, latitud, longitud, data_lotes, data_construcciones, building_shape_geometry, numero_pisos=numero_pisos)
    
    if html_mapa is not None:
        soup = BeautifulSoup(html_mapa, 'html.parser')
        mapa_body = soup.body.decode_contents() if soup.body else ''
    else:
        mapa_body = ""
        
    #-------------------------------------------------------------------------#
    # Mapa mapbox huella
    plote                            = gpd.GeoDataFrame(geometry=[poligono_lote])
    plote['color']                   = '#87cefa'
    building_shape_geometry['color'] = '#DFD3FD'
    grid_aislamiento['color']        = 'green'
    combined_gdf                     = pd.concat([grid_aislamiento,building_shape_geometry,plote,data_andenes,data_vias])

    if not data_andenes.empty:
        data_andenes['color'] = '#FDD835'
        combined_gdf          = pd.concat([combined_gdf,data_andenes])

    if not data_vias.empty:
        data_vias['color'] = '#FFA726'
        combined_gdf       = pd.concat([combined_gdf,data_vias])
        
    html_mapa = mapa_mapbox_huella(latitud, longitud, combined_gdf)
    if html_mapa is not None:
        soup       = BeautifulSoup(html_mapa, 'html.parser')
        map_huella = soup.body.decode_contents() if soup.body else ''
    else:
        map_huella = ""

    #-------------------------------------------------------------------------#
    # Cuadro Resumen
    #-------------------------------------------------------------------------#    
    area_total_poligono         = getareapolygon(poligono_lote) if poligono_lote is not None else 0
    area_superficie_planta      = building_shape_geometry['area'].sum()
    area_superficie_planta_neta = area_superficie_planta * (1 - proporcion_areas_comunes)
    area_total_edificada        = area_superficie_planta * numero_pisos
    area_neta_vendible          = area_superficie_planta_neta * numero_pisos
    altura_total_edificada = f'{alturapiso * numero_pisos} mt'
    
    inputvar_resumen = {
        'area_total_poligono': area_total_poligono,
        'area_superficie_planta': area_superficie_planta,
        'area_superficie_planta_neta': area_superficie_planta_neta,
        'area_total_edificada': area_total_edificada,
        'area_neta_vendible': area_neta_vendible,
        'altura_total_edificada': altura_total_edificada,
        'pisos': numero_pisos,
        'alturapiso': alturapiso,
        'proporcion_areas_comunes': proporcion_areas_comunes,
    }
    inputvar_resumen = formatoResumenMapa([], inputvar_resumen)
    
    html_resumen = ""
    if isinstance(inputvar_resumen, list) and inputvar_resumen != [] and 'items' in inputvar_resumen[0] and isinstance(inputvar_resumen[0]['items'], list) and inputvar_resumen[0]['items'] != []:
        html_resumen = """
        <div class="urbex-col-12 urbex-col-lg-4 urbex-p-2">
         <div class="urbex-h-100 urbex-d-flex urbex-flex-column urbex-p-3" id="box_shadow_default">
          <h1 class="urbex-mt-2" id="title_inside_table">
           Supuestos para el análisis
          </h1>
          <div class="urbex-table-responsive urbex-flex-grow-1" style="line-height: 0.1;">
           <table class="urbex-table urbex-table-sm urbex-table-borderless">
            <tbody>
        """
        for i in inputvar_resumen[0]['items']:
            key = i['titulo']
            value = i['valor']
            if isinstance(value, list):
                html_resumen += f"""
                <tr>
                    <td id="firstcoltable" style="padding: 0.1rem; vertical-align: top; line-height: 1;"><span id="label_inside">{html.escape(key)}</span></td>
                    <td style="padding: 0.1rem; vertical-align: top; line-height: 1;"><span id="value_inside">
                """
                for val in value:
                    html_resumen += f"""
                    <span id="value_inside">{html.escape(str(val))}</span>
                    """
                html_resumen += """
                    </span></td>
                </tr>
                """
            else:
                html_resumen += f"""
                <tr>
                    <td id="firstcoltable" style="padding: 0.1rem; vertical-align: top; line-height: 1;"><span id="label_inside">{html.escape(key)}</span></td>
                    <td style="padding: 0.1rem; vertical-align: top; line-height: 1;"><span id="value_inside">{html.escape(str(value))}</span></td>
                </tr>
                """
        
        html_resumen += """
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        """
        
    #-------------------------------------------------------------------------#
    # Vecinos
    #-------------------------------------------------------------------------#

    inputvar_resumen = [{'seccion': 'Resumen',
      'items': [{'titulo': 'Área del terreno vecino:', 'valor': '800'},
                {'titulo': 'Pisos del vecino:', 'valor': '7'},
                {'titulo': 'Codigo del vecino:', 'valor': '0084125845'},
                ]
      
      }]
    
    #{inputvar_resumen = 'area_lote_vecino': 800,
    #    'pisos_vecino': 7,
    #    'codigo_lote': '0084125845'}
    i#nputvar_resumen = formatoResumenMapa([], inputvar_resumen)
    
    if isinstance(inputvar_resumen, list) and inputvar_resumen != [] and 'items' in inputvar_resumen[0] and isinstance(inputvar_resumen[0]['items'], list) and inputvar_resumen[0]['items'] != []:
        html_resumen += """
        <div class="urbex-col-12 urbex-col-lg-4 urbex-p-2">
         <div class="urbex-h-100 urbex-d-flex urbex-flex-column urbex-p-3" id="box_shadow_default">
          <h1 class="urbex-mt-2" id="title_inside_table">
           Análisis lotes colindantes
          </h1>
          <div class="urbex-table-responsive urbex-flex-grow-1" style="line-height: 0.1;">
           <table class="urbex-table urbex-table-sm urbex-table-borderless">
            <tbody>
        """
        for i in inputvar_resumen[0]['items']:
            key = i['titulo']
            value = i['valor']
            if isinstance(value, list):
                html_resumen += f"""
                <tr>
                    <td id="firstcoltable" style="padding: 0.1rem; vertical-align: top; line-height: 1;"><span id="label_inside">{html.escape(key)}</span></td>
                    <td style="padding: 0.1rem; vertical-align: top; line-height: 1;"><span id="value_inside">
                """
                for val in value:
                    html_resumen += f"""
                    <span id="value_inside">{html.escape(str(val))}</span>
                    """
                html_resumen += """
                    </span></td>
                </tr>
                """
            else:
                html_resumen += f"""
                <tr>
                    <td id="firstcoltable" style="padding: 0.1rem; vertical-align: top; line-height: 1;"><span id="label_inside">{html.escape(key)}</span></td>
                    <td style="padding: 0.1rem; vertical-align: top; line-height: 1;"><span id="value_inside">{html.escape(str(value))}</span></td>
                </tr>
                """
        
        html_resumen += """
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        """
        
    #-------------------------------------------------------------------------#
    # Información General
    #-------------------------------------------------------------------------#
    html_content = ""
    for seccion in formato:
        html_content += f"""
            <div class="urbex-col-12 urbex-col-md-6 urbex-p-1">
                <div class="urbex-h-100 urbex-d-flex urbex-flex-column urbex-p-3" id="box_shadow_default">
                    <h1 class="urbex-mt-2" id="title_inside_table">{html.escape(seccion['seccion'])}</h1>
                    <div class="urbex-table-responsive urbex-flex-grow-1" style="line-height: 0.1;">
                        <table class="urbex-table urbex-table-sm urbex-table-borderless">
                            <tbody>
        """
        for item in seccion['items']:
            if isinstance(item['valor'], list):
                html_content += f"""
                                <tr>
                                    <td id="firstcoltable" style="padding: 0.1rem; vertical-align: top; line-height: 1;"><span id="label_inside">{html.escape(item['titulo'])}</span></td>
                                    <td style="padding: 0.1rem; vertical-align: top; line-height: 1;">
                """
                for valor in item['valor']:
                    html_content += f"""
                                        <span id="value_inside">{html.escape(str(valor))}</span>
                    """
                html_content += """
                                    </td>
                                </tr>
                """
            else:
                html_content += f"""
                                <tr>
                                    <td id="firstcoltable" style="padding: 0.1rem; vertical-align: top; line-height: 1;"><span id="label_inside">{html.escape(item['titulo'])}</span></td>
                                    <td style="padding: 0.1rem; vertical-align: top; line-height: 1;"><span id="value_inside">{html.escape(str(item['valor']))}</span></td>
                                </tr>
                """
        
        html_content += """
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        """

    if html_content!='':
        html_content = f"""
        <section>
         <div class="urbex-container-fluid">
          <div class="urbex-row">
              {html_content}
          </div>
         </div>
        </section>  
        """
    #-------------------------------------------------------------------------#
    # Data Pricing
    #-------------------------------------------------------------------------#
    html_pricing = ""
    formato      = []
    if not datapricing.empty:
        datapricingappend = pd.DataFrame([{'tipoinmueble':'Total','areavendible':datapricing['areavendible'].sum(),
                                           'precio':" ",'recaudo':datapricing['recaudo'].sum()},
                                          {'tipoinmueble':"",'areavendible':"",'precio':"",'recaudo':""},
                                          {'tipoinmueble':"",'areavendible':"",'precio':"",'recaudo':""},
                                          {'tipoinmueble':"",'areavendible':"",'precio':"",'recaudo':""},
                                          {'tipoinmueble':"Avalúo catastral total",'areavendible':"",'precio':"",'recaudo':info_terreno['avaluo_catastral']},
                                          {'tipoinmueble':"Impuesto predial total",'areavendible':"",'precio':"",'recaudo':info_terreno['impuesto_predial']},
                                          ])
        datapricing  = pd.concat([datapricing,datapricingappend])
        formato.append(formatoFactibilidad(datapricing))      
        
    if not data_precios_referencia.empty:
        formato.append(formatoDatapricingTable(data_precios_referencia))      
        
    if isinstance(formato, list) and formato != []:
        html_pricing = ""
        for section in formato:
            section_title = section["seccion"]
            items = section["items"]
            
            # Determinar si la sección contiene listas verificando el primer item
            contains_list = any(isinstance(item.get("valor"), list) for item in items)
            
            if not contains_list:
                html_pricing += f'''
                <div class="urbex-col-12 urbex-col-md-6 urbex-p-1">
                    <div class="urbex-h-100 urbex-d-flex urbex-flex-column urbex-p-3" id="box_shadow_default">
                        <h1 class="urbex-mt-2" id="title_inside_table">{section_title}</h1>
                        <div class="urbex-table-responsive urbex-flex-grow-1" style="line-height: 0.1;">
                            <table class="urbex-table urbex-table-sm urbex-table-borderless">
                                <tbody>'''
                for item in items:
                    is_empty    = True if "valor" in item and ((isinstance(item["valor"],str) and item["valor"]=='') or item["valor"] is None) else False
                    title_style = 'color: #666666; font-weight: bold;' if is_empty else ''
                    if is_empty:
                        html_pricing += """<tr><td style="padding: 0.1rem; vertical-align: top; line-height: 1;"></td></tr>"""
                    
                    html_pricing += f'''
                                    <tr>
                                    <td id="firstcoltable" style="padding: 0.1rem; vertical-align: top; line-height: 1;"><span id="label_inside">{item["titulo"]}</span></td>
                                    <td style="padding: 0.1rem; vertical-align: top; line-height: 1;"><span id="value_inside">{item["valor"]}</span></td>
                                    </tr>'''
                
                html_pricing += '''
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>'''
            else:
                first_item = items[0]
                headers    = first_item["valor"]
                
                html_pricing += f'''
                <div class="urbex-col-12 urbex-col-md-6 urbex-p-1">
                    <div class="urbex-h-100 urbex-d-flex urbex-flex-column urbex-p-3" id="box_shadow_default">
                        <h1 class="urbex-mt-2" id="title_inside_table">{section_title}</h1>
                        <div class="urbex-table-responsive urbex-flex-grow-1" style="line-height: 0.1;">
                            <table class="urbex-table urbex-table-sm urbex-table-borderless">
                                <thead>
                                    <tr>
                                    <th></th>'''
    
                for header in headers:
                    html_pricing += f'''
                                    <th><span id="topvalue_inside">{header}</span></th>'''
                html_pricing += '''
                                    </tr>
                                </thead>
                                <tbody>'''
    
                for item in items[1:]:
                    html_pricing += f'''
                                    <tr>
                                    <td style="padding: 0.1rem; vertical-align: top; line-height: 1;"><span id="tipovariable_inside">{item["titulo"]}</span></td>'''
                    
                    for value in item["valor"]:
                        html_pricing += f'''
                                    <td style="padding: 0.1rem; vertical-align: top; line-height: 1;"><span id="value_inside">{value}</span></td>'''
                    html_pricing += '''
                                    </tr>'''
                html_pricing += '''
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>'''
                
    if html_pricing!='':
        html_pricing = f"""
        <section>
         <div class="urbex-container-fluid">
          <div class="urbex-row">
              {html_pricing}
          </div>
         </div>
        </section>  
        """
        
    #-------------------------------------------------------------------------#
    # Html
    #-------------------------------------------------------------------------#   

    html_content = f"""
    <!DOCTYPE html>
    
    <html data-bs-theme="light" lang="en">
    <head>
    <meta charset="utf-8"/>
    <meta content="width=device-width, initial-scale=1.0, shrink-to-fit=no" name="viewport"/>
    <link href="https://iconsapp.nyc3.digitaloceanspaces.com/_estilo_general/prefixed_bootstrap.min.css" rel="stylesheet"/>
    <link href="https://iconsapp.nyc3.digitaloceanspaces.com/_estilo_general/prefixed_styles.css" rel="stylesheet"/>
    <link href="https://api.mapbox.com/mapbox-gl-js/v3.1.2/mapbox-gl.css" rel="stylesheet">
    <script src="https://api.mapbox.com/mapbox-gl-js/v3.1.2/mapbox-gl.js"></script>
    <style>
        .map-container {{
            display: flex;
            flex-direction: row;
            width: 100%;
            height: 600px;
        }}
        #mapa_body {{
            flex: 7; /* 70% */
            height: 100%;
            position: relative;
        }}
        #map_huella {{
            flex: 3; /* 30% */
            height: 100%;
            position: relative;
        }}
        .map {{
            position: absolute;
            top: 0;
            bottom: 0;
            width: 100%;
            height: 100%;
        }}
    </style>
    </head>
    <body>
    {html_content}
      
      <section>
       <div class="urbex-container-fluid">
        <div class="urbex-row">
         <div class="urbex-col-12 urbex-col-lg-8 urbex-p-2" style="min-height: 600px;">
          <div class="urbex-h-100 urbex-d-flex urbex-flex-column urbex-p-1" id="box_shadow_default">
            <div class="map-container">
                <div id="mapa_body">
                    <div id="map" class="map">{mapa_body}</div>
                </div>
            </div>
          </div>
         </div>
         <div class="urbex-col-12 urbex-col-lg-4 urbex-p-2" style="min-height: 600px;">
          <div class="urbex-h-100 urbex-d-flex urbex-flex-column urbex-p-1" id="box_shadow_default">
            <div class="map-container">
                <div id="map_huella">
                    <div id="lotem" class="map">{map_huella}</div>
                </div>
            </div>
          </div>
         </div>
        </div>
       </div>
      </section>
        
      <section>
       <div class="urbex-container-fluid">
        <div class="urbex-row">
          {html_resumen}
        </div>
       </div>
      </section>
 
    {html_pricing}
    </body>
    </html>
    """
    return html_content

    
def formatoPOT(formato,inputvar):
    formato_unico = [{'variable':'tipotratamiento','label':'Tipo de tratamiento'},
                     {'variable':'tipologia','label':'Tipología'},
                     {'variable':'max_altura','label':'Altura máxima tratamiento','formato':'int'},
                     {'variable':'max_altura_manzana','label':'Máxima altura construida en la manzana','formato':'int'},
                     {'variable':'altura_aeronautica','label':'Altura aeronáutica','formato':'int'},
                     {'variable':'elevacion_aeronautica','label':'Elevación aeronáutica','formato':'int'},
                     {'variable':'area_actividad','label':'Área de actividad'},
                     {'variable':'actuacion_estrategica','label':'Actuación estrategíca'},
                     {'variable':'antejarin_obs','label':'Antejardín'},
                     {'variable':'antejarin_dimension_min','label':'Antejardín (mínimo)','formato':'miles'},
                     {'variable':'antejarin_dimension_max','label':'Antejardín (máximo)','formato':'miles'},
                     {'variable':'cultual_nombre','label':'Cultural'},
                     {'variable':'cultual_categoria','label':'Área cultural'},
                     ]
    formato = getformato(formato,formato_unico,inputvar,'P.O.T')
    return formato
        
def formatoTerreno(formato,inputvar):
    formato_unico = [{'variable':'areapolygon','label':'Área de terreno','formato':'miles'},
                     {'variable':'preaconst','label':'Área construida actual','formato':'miles'},
                     {'variable':'estrato','label':'Estrato','formato':'int'},
                     {'variable':'predios','label':'Número de predios','formato':'int'},
                     {'variable':'propietarios','label':'Número de propietarios','formato':'int'},
                     {'variable':'connpisos','label':'Pisos máximos construidos','formato':'int'},
                     {'variable':'connsotano','label':'Sotanos','formato':'int'},
                     {'variable':'prevetustzmin','label':'Antigüedad mínima','formato':'int'},
                     {'variable':'prevetustzmax','label':'Antigüedad máxima','formato':'int'},
                     {'variable':'esquinero','label':'Esquinero'},
                     {'variable':'tipovia','label':'Tipo de vía'},
                     {'variable':'avaluo_catastral','label':'Avalúo catastral total','formato':'currency'},
                     {'variable':'avaluomt2terre','label':'Avalúo catastral del suelo por m²','formato':'currency'},
                     {'variable':'impuesto_predial','label':'Impuesto predial total','formato':'currency'},
                     ]
    formato = getformato(formato,formato_unico,inputvar,'Información del Terreno')
    return formato

def formatoResumenMapa(formato,inputvar):
    
    formato_unico = [
                     {'variable':'pisos','label':'Número de pisos','formato':'int'},
                     {'variable':'alturapiso','label':'Altura por planta','formato':'miles'},
                     {'variable':'proporcion_areas_comunes','label':'Áreas comúnes (%)','formato':'miles'},
                     {'variable':'area_total_poligono','label':'Área del terreno','formato':'miles'},
                     {'variable':'area_superficie_planta','label':'Área por planta','formato':'miles'},
                     {'variable':'area_superficie_planta_neta','label':'Área vendible por planta','formato':'miles'},
                     {'variable':'area_total_edificada','label':'Área total edificada','formato':'miles'},
                     {'variable':'area_neta_vendible','label':'Área total vendible','formato':'miles'},
                     {'variable':'altura_total_edificada','label':'Altura total edificada'},
                     ]
    formato = getformato(formato,formato_unico,inputvar,'Resumen')
    return formato
    
def getformato(formato,formato_unico,inputvar,titulo_general):
    formato_merge = []
    for i in formato_unico:
        titulo      = i['label']
        tipoformato = i['formato'] if 'formato' in i and isinstance(i['formato'],str) and i['formato']!='' else None
        value       = inputvar[i['variable']] if i['variable'] in inputvar and not pd.isna(inputvar[i['variable']]) else None
        if isinstance(value,str) and value=='': value = None
        try: value = "${:,.0f}".format(value) if isinstance(tipoformato,str) and 'currency' in tipoformato else value
        except: pass
        try: value = "{:,.1f}".format(value) if isinstance(tipoformato,str) and 'miles' in tipoformato else value
        except: pass
        try: value = int(float(value)) if isinstance(tipoformato,str) and 'int' in tipoformato else value
        except: pass
        if value is not None:
            formato_merge.append({'titulo': f'{titulo}:', 'valor': value})
        
    if isinstance(formato_merge,list) and formato_merge!=[]:
        formato_merge = {'seccion': titulo_general,'items':formato_merge}
        formato.append(formato_merge)
    return formato


def formatoFactibilidad(datapricing):
    json_output = {
        "seccion": "Estimación prefactibilidad",
        "items": []
    }
    json_output["items"].append({
        "titulo": "",
        "valor": ["","Área Vendible", "Precio m²", "Recaudo"]
    })
    for index, row in datapricing.iterrows():
        json_output["items"].append({
            "titulo": "",
            "valor": [
                row["tipoinmueble"],
                "{:,.1f}".format(row['areavendible']) if pd.notna(row['areavendible']) and isinstance(row['areavendible'],(float,int)) else "",
                "${:,.0f}".format(row['precio']) if pd.notna(row['precio']) and isinstance(row['precio'],(float,int)) else "",
                "${:,.0f}".format(row['recaudo'])  if pd.notna(row['recaudo']) and isinstance(row['recaudo'],(float,int)) else ""
            ]
        })
    return json_output

def formatoDatapricingTable(data_precios_referencia):
    json_output = {
        "seccion": "Referencia de precios (500 m²)",
        "items": []
    }

    json_output["items"].append({
        "titulo": "",
        "valor": ["","Tipo de inmueble", "Mediana", "Mínimo", "Máximo"]
    })
    for _,items in data_precios_referencia.iterrows():
        json_output["items"].append({
            "titulo": "",
            "valor": [
                items["tipo"],
                items["tipoinmueble"],
                "${:,.0f}".format(items['median']) if 'median' in items and isinstance(items['median'],(float,int)) else '',
                "${:,.0f}".format(items['min'])  if 'min' in items and isinstance(items['min'],(float,int)) else '',
                "${:,.0f}".format(items['max'])  if 'max' in items and isinstance(items['max'],(float,int)) else '',
            ]
        })
    return json_output