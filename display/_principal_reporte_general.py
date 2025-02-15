import streamlit as st
import pandas as pd
import geopandas as gpd
import shapely.wkt as wkt
import json
import base64
import urllib.parse
import random
from shapely.geometry import Point
from datetime import datetime
from shapely.geometry import Polygon, MultiPolygon

from functions.getuso_destino import usosuelo_class

@st.cache_data(show_spinner=False)
def main(formato, data_predios, data_transacciones, data_listings, datactl, datalicencias, formato_estadisticas, data_transacciones_historicas, data_construcciones, latitud, longitud, polygon, grupo=None, pdfversion=False):

    #-------------------------------------------------------------------------#
    # Información General
    #-------------------------------------------------------------------------#
    sections_html = """
    <section>
        <div class="urbex-container">
            <div class="urbex-row">
    """
    for section in formato:
        section_title = section["seccion"]
        items = section["items"]
        
        # Determinar si la sección contiene listas verificando el primer item
        contains_list = any(isinstance(item.get("valor"), list) for item in items)
        
        if not contains_list:
            sections_html += f'''
            <div class="urbex-col-12 urbex-col-md-6 urbex-p-1">
                <div class="urbex-h-100 urbex-d-flex urbex-flex-column urbex-p-3" id="box_shadow_default">
                    <h1 class="urbex-mt-2" id="title_inside_table">{section_title}</h1>
                    <div class="urbex-table-responsive urbex-flex-grow-1" style="line-height: 0.1;">
                        <table class="urbex-table urbex-table-sm urbex-table-borderless">
                            <tbody>'''
            for item in items:
                is_empty = "valor" in item and ((isinstance(item["valor"], str) and item["valor"] == '') or item["valor"] is None)
                title_style = 'color: #666666; font-weight: bold;' if is_empty else ''
                if is_empty:
                    sections_html += """<tr><td colspan="2" style="padding: 0.5rem;"></td></tr>"""
                
                sections_html += f'''
                                <tr>
                                    <td id="firstcoltable" style="padding: 0.1rem; vertical-align: top; line-height: 1;">
                                        <span id="label_inside" style="{title_style}">{item["titulo"]}</span>
                                    </td>
                                    <td style="padding: 0.1rem; vertical-align: top; line-height: 1;">
                                        <span id="value_inside">{item["valor"]}</span>
                                    </td>
                                </tr>'''
            
            sections_html += '''
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>'''
        else:
            first_item = items[0]
            headers = first_item["valor"]
            
            sections_html += f'''
            <div class="urbex-col">
                <div class="urbex-h-100 urbex-d-flex urbex-flex-column urbex-p-3" id="box_shadow_default">
                    <h1 class="urbex-mt-2" id="title_inside_table">{section_title}</h1>
                    <div class="urbex-table-responsive" style="line-height: 0.8;">
                        <table class="urbex-table urbex-table-borderless">
                            <thead>
                                <tr>
                                    <th></th>'''
            for header in headers:
                sections_html += f'''
                                    <th>
                                        <span id="topvalue_inside">{header}</span>
                                    </th>'''
            sections_html += '''
                                </tr>
                            </thead>
                            <tbody>'''
            for item in items[1:]:
                sections_html += f'''
                                <tr>
                                    <td>
                                        <span id="tipovariable_inside">{item["titulo"]}</span>
                                    </td>'''
                for value in item["valor"]:
                    sections_html += f'''
                                    <td>
                                        <span id="value_inside">{value}</span>
                                    </td>'''
                sections_html += '''
                                </tr>'''
            sections_html += '''
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>'''
    
    sections_html += """
            </div>
        </div>
    </section>
    """
    
    #-------------------------------------------------------------------------#
    # Tablas 
    #-------------------------------------------------------------------------#
    fulltable = 'style="max-height: 500px; filter: blur(0px); line-height: 1;"'
    if pdfversion: fulltable = ''
    
    data_predios['link'] = data_predios['prechip'].apply(
        lambda x: f"http://www.urbex.com.co/Busqueda_avanzada?type=predio&code={x}&vartype=chip&token={st.session_state.token}"
    ) if 'prechip' in data_predios else ''
    
    data_transacciones['link'] = data_transacciones['docid'].apply(
        lambda x: f"https://radicacion.supernotariado.gov.co/app/static/ServletFilesViewer?docId={x}"
    ) if 'docid' in data_transacciones else ''

    if 'fecha_documento_publico' in data_transacciones:
        data_transacciones['fecha_documento_publico'] = pd.to_datetime(data_transacciones['fecha_documento_publico'], unit='ms')

    datactl['link'] = datactl['url'].copy()  if not datactl.empty and 'url' in datactl else ''

    dmerge = usosuelo_class()
    if not dmerge.empty:
        dmerge = dmerge.drop_duplicates(subset='precuso')

    if not data_predios.empty:
        data_predios = data_predios.merge(dmerge[['precuso','usosuelo']],on='precuso',how='left',validate='m:1')
    
    if not data_transacciones.empty:
        data_transacciones = data_transacciones.merge(dmerge[['precuso','usosuelo']],on='precuso',how='left',validate='m:1')

        if 'fecha_documento_publico' in data_transacciones:
            data_transacciones['fecha_documento_publico'] = pd.to_datetime(data_transacciones['fecha_documento_publico'])
            data_transacciones['fecha_documento_publico'] = data_transacciones['fecha_documento_publico'].dt.date

    if not datalicencias.empty and  'fecha' in datalicencias:
        datalicencias['fecha'] = pd.to_datetime(datalicencias['fecha'])
        datalicencias['fecha'] = datalicencias['fecha'].dt.date

    formato_data = [
        {
            'data': data_predios,
            'columns': ['Link', 'predirecc', 'usosuelo', 'prechip', 'matriculainmobiliaria', 'precedcata', 'preaconst', 'preaterre'],
            'rename': {'predirecc': 'Dirección', 'usosuelo': 'Uso del suelo', 'prechip': 'Chip', 'matriculainmobiliaria': 'Matrícula Inmobiliaria', 'precedcata': 'Cédula Catastral', 'preaconst': 'Área Construida', 'preaterre': 'Área de Terreno'},
            'icon': 'https://iconsapp.nyc3.digitaloceanspaces.com/lupa.png',
            'filtercolumn': 'predirecc',
            'title': 'Predios'
        },
        {
            'data': data_transacciones,
            'columns': ['Link', 'predirecc', 'fecha_documento_publico', 'codigo', 'nombre', 'cuantia', 'entidad', 
                       'numero_documento_publico', 'oficina', 'preaconst', 'preaterre', 'chip', 'usosuelo', 
                       'tipo_documento_publico', 'titular', 'email', 'tipo', 'nrodocumento'],
            'rename': {'chip':'Chip','codigo':'Código', 'cuantia':'Cuantía', 'entidad':'Entidad', 'fecha_documento_publico':'Fecha', 'nombre':'Tipo', 
                       'numero_documento_publico':'Número escritura', 'oficina':'Oficina', 'preaconst':'Área Construida', 'preaterre':'Área de Terreno', 'usosuelo':'Uso del suelo', 'predirecc':'Dirección', 
                       'tipo_documento_publico':'Tipo de documento', 'titular':'Titular', 'email':'Email', 'tipo':'Tipo documento', 'nrodocumento':'Número documento'},
            'icon': 'https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/publicimg/pdf.png',
            'filtercolumn': 'fecha_documento_publico',
            'ascending':False,
            'title': 'Transacciones'
        },
        {
            'data': datactl,
            'columns': ['Link', 'predirecc', 'prechip', 'matriculainmobiliaria', 'preaconst'],
            'rename': {'predirecc': 'Direccion', 'prechip': 'Chip', 'matriculainmobiliaria': 'Matricula Inmobiliaria', 'preaconst': 'Area Construida'},
            'icon': 'https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/publicimg/pdf.png',
            'filtercolumn': 'predirecc',
            'title': 'Certificados de libertad y tradición'
        },
        {
            'data': datalicencias,
            'columns': ['licencia','formato_direccion','tramite', 'propietarios', 'proyecto', 'estado','curaduria','fecha'],
            'rename': {'licencia':'Licencia','formato_direccion':'Dirección','tramite':'Tramite', 'propietarios':'Propietario', 'proyecto':'Proyecto', 'estado':'Estado','curaduria':'Curaduría','fecha':'Fecha'},
            'icon': 'https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/publicimg/pdf.png',
            'filtercolumn': 'fecha',
            'ascending':False,
            'title': 'Licencias'
        },

    ]

    tables_html = ""
    for items in formato_data:
        if not items['data'].empty:
            data = items['data'].sort_values(by=items['filtercolumn'], ascending=items['ascending'] if 'ascending' in items else True)
    
            # Renombrar columnas usando el diccionario 'rename'
            rename_dict = items.get('rename', {})
            columns_with_rename = [rename_dict.get(col, col) for col in items['columns']]
    
            tables_html += f'''
            <section>
                <div class="urbex-container">
                    <div class="urbex-row urbex-p-3">
                        <div class="urbex-col" style="font-size: 14px;">
                            <h1 id="seccion_title">{items['title']}</h1>
                            <div class="urbex-table-responsive urbex-text-center urbex-shadow" {fulltable}>
                                <table class="urbex-table urbex-table-striped urbex-table-sm urbex-table-bordered">
                                    <thead class="urbex-bg-primary urbex-text-white" style="font-size: 16px;; position: sticky; top: 0; z-index: 2;">
                                        <tr>
                                            {''.join(f'<th id="table-header-style">{col}</th>' for col in columns_with_rename)}
                                        </tr>
                                    </thead>
                                    <tbody>
            '''
    
            for _, row in data.iterrows():
                tables_html += "<tr>"
                for col in items['columns']:
                    if col == 'Link':
                        tables_html += f'''
                            <td style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                <a href="{row['link']}" target="_blank">
                                    <img src="{items['icon']}" alt="link" style="width: 16px; height: 16px; object-fit: contain;">
                                </a>
                            </td>
                        '''
                    elif col == 'cuantia' and isinstance(row.get(col), (int, float)):
                        tables_html += f'''<td style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${row[col]:,.0f}</td>'''
                    elif not pd.isna(row.get(col)):
                        tables_html += f'''<td style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{row.get(col, '')}</td>'''
                    else:
                        tables_html += '''<td style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"></td>'''
                tables_html += "</tr>"
    
            tables_html += '''
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </section>
            '''

    #-------------------------------------------------------------------------#
    # Listings
    #-------------------------------------------------------------------------#
    listings_html = ""
    if not data_listings.empty:
        # Separar listings activos e históricos
        active_listings = data_listings[data_listings['activo'] == 1]
        historic_listings = data_listings[data_listings['activo'] == 0]
        
        for listing_data, title in [(active_listings, 'Listings Activos'), (historic_listings, 'Listings Históricos')]:
            if not listing_data.empty:
                listings_html += f'''
                <section>
                 <div class="urbex-row urbex-p-2">
                  <div class="urbex-col">
                   <h1 id="seccion_title">
                    {title}
                   </h1>
                  </div>
                 </div>
                </section>
                
                <section>
                 <div class="urbex-container">
                   <div class="urbex-row urbex-p-3">
                '''
                


                for _, items in listing_data.iterrows():
                    
                    params    = {'type':'ficha','code':items['code'],'tiponegocio':items['tiponegocio'].lower(),'tipoinmueble':items['tipoinmueble'].lower(),'token':st.session_state.token}
                    params    = json.dumps(params)
                    params    = base64.urlsafe_b64encode(params.encode()).decode()
                    params    = urllib.parse.urlencode({'token': params})
                    urlexport = "http://www.urbex.com.co/Reporte"
                    urllink   = f"{urlexport}?{params}"
                    imagen_principal = items['url_img'].split('|')[0].strip() if 'url_img' in items and isinstance(items['url_img'], str) else "https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png"

                    listings_html += f'''
                     <div class="urbex-col-12 urbex-col-md-4 urbex-p-2">
                      <div class="urbex-h-100 urbex-d-flex urbex-flex-column urbex-p-3" id="box_shadow_default">
                       <a href="{urllink}" target="_blank">
                         <img src="{imagen_principal}" alt="property image" style="height: 250px;width: 100%;margin-bottom: 10px;" onerror="this.src='https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png';">
                       </a>
                       <div class="urbex-table-responsive urbex-flex-grow-1" style="line-height: 0.6;font-size: 14px;">
                        <table class="urbex-table urbex-table-borderless">
                         <tbody>
                    '''
                    
                    
                    # Agregar información del listing
                    if 'tiponegocio' in items and isinstance(items['tiponegocio'], str):
                        listings_html += f'''
                        <tr>
                            <td id="firstcoltable"><span id="label_inside_listing">Tipo de negocio:</span></td>
                            <td><span id="value_inside_listing">{items['tiponegocio']}</span></td>
                        </tr>
                        '''
                        
                    if 'tipoinmueble' in items and isinstance(items['tipoinmueble'], str):
                        listings_html += f'''
                        <tr>
                            <td id="firstcoltable"><span id="label_inside_listing">Tipo de inmueble:</span></td>
                            <td><span id="value_inside_listing">{items['tipoinmueble']}</span></td>
                        </tr>
                        '''
                    if 'direccion' in items and isinstance(items['direccion'], str):
                        listings_html += f'''
                        <tr>
                            <td id="firstcoltable"><span id="label_inside_listing">Dirección:</span></td>
                            <td><span id="value_inside_listing">{items['direccion']}</span></td>
                        </tr>
                        '''
                        
                    if 'valor' in items and (isinstance(items['valor'], float) or isinstance(items['valor'], int)):
                        listings_html += f'''
                        <tr>
                            <td id="firstcoltable"><span id="label_inside_listing">Precio:</span></td>
                            <td><span id="value_inside_listing">${items['valor']:,.0f}</span></td>
                        </tr>
                        '''
                        
                    if 'valormt2' in items and (isinstance(items['valormt2'], float) or isinstance(items['valormt2'], int)):
                        listings_html += f'''
                        <tr>
                            <td id="firstcoltable"><span id="label_inside_listing">Valor m²:</span></td>
                            <td><span id="value_inside_listing">${items['valormt2']:,.0f} m²</span></td>
                        </tr>
                        '''
                        
                    if 'areaconstruida' in items and isinstance(items['areaconstruida'], (float,int)):
                        listings_html += f'''
                        <tr>
                            <td id="firstcoltable"><span id="label_inside_listing">Área construida:</span></td>
                            <td><span id="value_inside_listing">{items['areaconstruida']} m²</span></td>
                        </tr>
                        '''
                    # Características especiales para apartamentos y casas
                    if 'tipoinmueble' in items and isinstance(items['tipoinmueble'], str):
                        tipoinmueble = items['tipoinmueble'].lower()
                        if any(x in tipoinmueble for x in ['apartamento', 'casa']):
                            if all(x in items for x in ['habitaciones', 'banos', 'garajes', 'areaconstruida']):
                                
                                
                                try:    areaconstruida = f"{items['areaconstruida']} m²"
                                except: areaconstruida = ""
                                try:    habitaciones = f"| {int(float(items['habitaciones']))} H"
                                except: habitaciones = ""
                                try:    banos = f"| {int(float(items['banos']))} B"
                                except: banos = ""
                                try:    garajes = f"| {int(float(items['garajes']))} G"
                                except: garajes = ""
    
                                listings_html += f'''
                                <tr>
                                    <td id="firstcoltable"><span id="label_inside_listing">Características:</span></td>
                                    <td><span id="value_inside_listing">{areaconstruida} {habitaciones} {banos} {garajes} </span></td>
                                </tr>
                                '''
                    if 'fecha_inicial' in items:
                        fecha = datetime.utcfromtimestamp(items['fecha_inicial'] / 1000).strftime('%Y-%m-%d')
                        listings_html += f'''
                        <tr>
                            <td id="firstcoltable"><span id="label_inside_listing">Fecha publicación:</span></td>
                            <td><span id="value_inside_listing">{fecha}</span></td>
                        </tr>
                        '''

                    
                    
                    listings_html += '''
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    '''
                
                listings_html += '''
                      </div>
                    </div>
                </section>
                '''

    #-------------------------------------------------------------------------#
    # Mapas
    #-------------------------------------------------------------------------#
    maps_html = map_function(latitud, longitud, polygon=str(polygon), data_construcciones=data_construcciones, grupo=grupo)


    #-------------------------------------------------------------------------#
    # Estadisticas
    #-------------------------------------------------------------------------#
    df = pd.DataFrame()
    if 'transaccionesyear' in  formato_estadisticas and 'value' in formato_estadisticas['transaccionesyear']:
        dfpaso          = pd.DataFrame(formato_estadisticas['transaccionesyear']['value'])
        if not dfpaso.empty:
            df1          = dfpaso[['year','cuantiamt2']]
            df1.columns  = ['year','valor']
            df1['label'] = 'Transacciones mt2'
            df           = pd.concat([df,df1])
            
            df1          = dfpaso[['year','transacciones']]
            df1.columns  = ['year','valor']
            df1['label'] = 'Transacciones'
            df           = pd.concat([df,df1])
        
    if 'predialesyear' in  formato_estadisticas and 'value' in formato_estadisticas['predialesyear']:
        dfpaso = pd.DataFrame(formato_estadisticas['predialesyear']['value'])
        if not dfpaso.empty:
            df1          = dfpaso[['year','avaluomt2']]
            df1.columns  = ['year','valor']
            df1['label'] = 'Avalúo mt2'
            df           = pd.concat([df,df1])
            
            df1          = dfpaso[['year','predialmt2']]
            df1.columns  = ['year','valor']
            df1['label'] = 'Predial mt2'
            df           = pd.concat([df,df1])
            
    if 'venta' in  formato_estadisticas and 'value' in formato_estadisticas['venta']:
        dfpaso = pd.DataFrame(formato_estadisticas['venta']['value'])
        if not dfpaso.empty:
            df1          = dfpaso[['year','valormt2']]
            df1.columns  = ['year','valor']
            df1['label'] = 'Venta mt2'
            df           = pd.concat([df,df1])
            
            df1          = dfpaso[['year','listings']]
            df1.columns  = ['year','valor']
            df1['label'] = 'Listings venta'
            df           = pd.concat([df,df1])
            
    if 'arriendo' in  formato_estadisticas and 'value' in formato_estadisticas['arriendo']:
        dfpaso = pd.DataFrame(formato_estadisticas['arriendo']['value'])
        if not dfpaso.empty:
            df1          = dfpaso[['year','valormt2']]
            df1.columns  = ['year','valor']
            df1['label'] = 'Arriendo mt2'
            df           = pd.concat([df,df1])
            
            df1          = dfpaso[['year','listings']]
            df1.columns  = ['year','valor']
            df1['label'] = 'Listings arriendo'
            df           = pd.concat([df,df1])
             
    style_chart = ""
    try:    
        if not df.empty:
            style_chart += double_axis_chart(df,'ChartBarras')
    except: pass

        #------------#
        # Proporcion #
    df = pd.DataFrame()
    if isinstance(formato,list) and formato!=[]:
        for j in formato:
            if 'seccion' in j and 'Tipología' in j['seccion']:
                try:
                    df               = pd.DataFrame(j['items'])
                    df['titulo']     = df['titulo'].apply(lambda x: x.strip())
                    df               = df[df["titulo"]!='']
                    df["proporcion"] = df["valor"].apply(lambda x: x[2] if isinstance(x, list) and len(x) > 2 else None)
                    df["proporcion"] = df["proporcion"].str.replace('%', '').astype(float) / 100
                    df               = df[["titulo", "proporcion"]]
                    break
                except: pass
            
    if not df.empty:
        try:
            df.rename(columns={'titulo':'ejex','proporcion':'ejey'},inplace=True)
            df.columns = ['ejex','ejey']
            df         = df.sort_values(by=['ejey'],ascending=False)
            df['color'] = '#5C9AE0'
            if not df.empty:
                st.dataframe(df)
                style_chart += pie_chart(df,'byProporcion',title='Tipos de uso')
        except: pass
    
        #---------------#
        # Transacciones #
    if not data_transacciones_historicas.empty:
        for column in ['cuantia', 'preaconst']:
            if column in data_transacciones_historicas:
                data_transacciones_historicas[column] = pd.to_numeric(data_transacciones_historicas[column], errors='coerce')
                data_transacciones_historicas         = data_transacciones_historicas[(data_transacciones_historicas[column].notnull()) & (data_transacciones_historicas[column] > 0)]

    if not data_transacciones_historicas.empty: 
        data_transacciones_historicas['valor'] = data_transacciones_historicas['cuantia'] / data_transacciones_historicas['preaconst']
        df           = data_transacciones_historicas[['valor']]
        style_chart += boxplot_chart(df,'BoxTransacciones',title='Transacciones')
        
        #---------#
        # Predios #
    df = pd.DataFrame(columns=['valor'])
    if not data_predios.empty and 'precuso' in data_predios:
        df    = data_predios.copy()
        dl    = usosuelo_class()
        lista = list(dl[dl['clasificacion'].isin(['Depósitos','Parqueadero'])]['precuso'].unique())
        if '050' in lista: lista.remove('050')
        idd   = df['precuso'].isin(lista)
        df    = df[~idd]

    if not df.empty and 'preaconst' in df:
        df.rename(columns={'preaconst':'valor'},inplace=True)
        style_chart += boxplot_chart(df,'BoxArea',title='Área construida')
        
    graficas_html = '''
    <section>
     <div class="urbex-row urbex-p-2">
      <div class="urbex-col">
       <h1 id="seccion_title">
        Estadísticas
       </h1>
      </div>
     </div>
    </section>
    <section>
     <div class="urbex-container">
      <div class="urbex-row">
       <div class="urbex-col-12 urbex-col-sm-12 urbex-p-5">
        <div id="box_shadow_default" style="min-height: 400px;">
         <canvas id="ChartBarras" style="height: 100%;"></canvas>
        </div>
       </div>
       <div class="urbex-col-12 urbex-col-lg-4 urbex-p-2">
        <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default" style="min-height: 200px;">
         <canvas id="BoxTransacciones" style="height: 100%;"></canvas>
        </div>
       </div>
       <div class="urbex-col-12 urbex-col-lg-4 urbex-p-2">
        <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default" style="min-height: 400px;">
         <canvas id="byProporcion" style="height: 100%;"></canvas>
        </div>
       </div>
       <div class="urbex-col-12 urbex-col-lg-4 urbex-p-2">
        <div class="urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default" style="min-height: 200px;">
         <canvas id="BoxArea" style="height: 100%;"></canvas>
        </div>
       </div>
      </div>
     </div>
    </section>
    '''
  
        
    #-------------------------------------------------------------------------#
    # CSS y HTML final
    #-------------------------------------------------------------------------#
 
    html_content = f'''
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

        body::-webkit-scrollbar {{
            display: none;
        }}
      </style>

    </head>
    <body>
        <section>
         <div class="urbex-container">
          <div class="urbex-row">
           <div class="urbex-col-12 urbex-col-sm-12 urbex-col-md-6 urbex-col-lg-4 urbex-col-xl-4 urbex-col-xxl-4">
            <div class="urbex-d-flex urbex-flex-column urbex-h-100 urbex-p-1" id="box_shadow_default">
                 <div id="mapstreetview" style="width: 100%; height: 400px;"></div>
            </div>
           </div>
           <div class="urbex-col-12 urbex-col-sm-12 urbex-col-md-6 urbex-col-lg-4 urbex-col-xl-4 urbex-col-xxl-4">
            <div class="urbex-d-flex urbex-flex-column urbex-h-100 urbex-p-1" id="box_shadow_default">
                <div id="mapsatelital" style="width: 100%; height: 400px;"></div>
            </div>
           </div>
           <div class="urbex-col-12 urbex-col-sm-12 urbex-col-md-6 urbex-col-lg-4 urbex-col-xl-4 urbex-col-xxl-4">
            <div class="urbex-d-flex urbex-flex-column urbex-h-100 urbex-p-1" id="box_shadow_default">
                <div id="3dmapbox" style="width: 100%; height: 400px;"></div>
            </div>
           </div>
          </div>
         </div>
        </section>
            
        {maps_html}
        {sections_html}
        {graficas_html}
        {tables_html}
        {listings_html}
        {style_chart}
    </body>
    </html>
    '''
    
    return html_content

def map_function(latitud, longitud, polygon=None, data_construcciones=pd.DataFrame(), grupo=None):
    html    = ""
    api_key = st.secrets['API_KEY']

    if (isinstance(latitud, float) or isinstance(latitud, int)) and (isinstance(longitud, float) or isinstance(longitud, int)):
        
        #---------------------------------------------------------------------#
        # Google maps
        map_view = """
        <script>
            function initMap() {
                // Mapa de Street View
                var latitud = latitud_replace;
                var longitud = longitud_replace;
                var latLng = new google.maps.LatLng(latitud, longitud);
                var panoramaOptions = {
                    position: latLng,
                    pov: {
                        heading: 0,
                        pitch: 0
                    },
                };
                var panorama = new google.maps.StreetViewPanorama(
                    document.getElementById('mapstreetview'),
                    panoramaOptions
                );
                var map1 = new google.maps.Map(document.getElementById('mapstreetview'), {
                    streetView: panorama
                });

                // Mapa Satelital con Polígono
                var mapOptions2 = {
                    center: {lat: latitud, lng: longitud},
                    zoom: 19, 
                    mapTypeId: google.maps.MapTypeId.SATELLITE
                };
                var map2 = new google.maps.Map(document.getElementById('mapsatelital'), mapOptions2);
                
                if (polygon_replace) {
                    var polygonCoords = polygon_replace;
                    var polygon = new google.maps.Polygon({
                        paths: polygonCoords,
                        strokeColor: '#FF0000',
                        strokeOpacity: 0.8,
                        strokeWeight: 2,
                        fillColor: '#808080',
                        fillOpacity: 0.35
                    });
                    polygon.setMap(map2);
                }
            }
        </script>
        """
        map_view += f"""<script src="https://maps.googleapis.com/maps/api/js?key={api_key}&callback=initMap" async defer></script>"""
        
        if polygon:
            polygon_coords = [[float(lng), float(lat)] for lng, lat in (coord.split() for coord in polygon.replace("POLYGON ((", "").replace("))", "").split(", "))]
            polygon_js = "[{}]".format(", ".join("{{lat: {}, lng: {}}}".format(lat, lng) for lng, lat in polygon_coords))
            map_view = map_view.replace('polygon_replace', polygon_js)
        else:
            map_view = map_view.replace('polygon_replace', 'null')
        
        map_view = map_view.replace('latitud_replace', str(latitud)).replace('longitud_replace', str(longitud))

        #---------------------------------------------------------------------#
        # 3D Mapbox
        
        if not data_construcciones.empty:

            if isinstance(grupo, (int, float)) and not isinstance(grupo, bool):
                grupo = int(grupo) if isinstance(grupo, float) and grupo.is_integer() else grupo
            if isinstance(grupo,str) and grupo!='':
                grupo = grupo.split('|')
            elif isinstance(grupo,(float,int)):
                grupo = [f'{grupo}']
            if isinstance(grupo,list) and grupo!=[]:
                grupo = list(map(int, grupo))
                                
                data_construcciones['geometry'] = data_construcciones['wkt'].apply(wkt.loads)
                data_construcciones             = gpd.GeoDataFrame(data_construcciones, geometry='geometry')
                data_construcciones['color'] = "#E1E5F2"
                if 'grupo' in data_construcciones:
                    idd = data_construcciones['grupo'].isin(grupo)
                    if sum(idd)>0:
                        data_construcciones.loc[idd,'color'] = "#A16CFF"
            # Generar el geojson de los edificios existentes con sus respectivos pisos
            altura_pisos      = 3
            edificios_geojson = []
            if not data_construcciones.empty:
                for idx, row in data_construcciones.iterrows():
                    geom             = row.geometry
                    connpisos        = row['connpisos']
                    edificio_geojson = polygon_to_geojson(geom)
                    color            = row['color']
                    edificios_geojson.append((idx, edificio_geojson, connpisos, color))
    
            # Mapbox access token (replace with your token)
            access_token = 'pk.eyJ1IjoiYWdhdmlyaWFqIiwiYSI6ImNrYWQ4dXlvZzIyMXIyeW50aHJldGVtcmgifQ.j7XuNBmPQ8SlrUeTPWsrNQ'
    
            map_3dmapbox = f"""
            <script>
                mapboxgl.accessToken = '{access_token}';
                const map = new mapboxgl.Map({{
                    style: 'mapbox://styles/mapbox/light-v11',
                    center: [{longitud}, {latitud}],
                    zoom: 18,
                    pitch: 45,
                    bearing: -17.6,
                    container: '3dmapbox',
                    antialias: true
                }});
    
                map.on('style.load', () => {{
    
                    // Añadir cada edificio existente como una fuente y capas 3D
                    {''.join([generate_building_layers(idx, geojson, connpisos, color, altura_pisos) for idx, geojson, connpisos, color in edificios_geojson])}
    
    
                }});
            </script>
            """

        else:
            #---------------------------------------------------------------------#
            # Leaflet
            geojson   = pd.DataFrame().to_json()
            geopoints = pd.DataFrame().to_json()
            if isinstance(polygon,str) and polygon!='':
                data2geojson = pd.DataFrame([{'geometry':wkt.loads(polygon)}])
                data2geojson = gpd.GeoDataFrame(data2geojson, geometry='geometry')
                data2geojson['color'] = 'blue'
                geojson      = data2geojson.to_json()

            data2geopoints          = pd.DataFrame([{'geometry':Point(longitud,latitud)}])
            data2geopoints          = gpd.GeoDataFrame(data2geopoints, geometry='geometry')
            data2geopoints['color'] = 'blue'
            geopoints               = data2geopoints.to_json()
            map_3dmapbox            = mapa_leaflet(latitud, longitud, geojson, geopoints)
            
        
        html = f"""
        {map_view}
        {map_3dmapbox}
        """
    return html



def double_axis_chart(df, name):
    # Definir el orden específico de las etiquetas
    order = ['Transacciones', 'Transacciones mt2', 'Venta mt2', 'Avalúo mt2', 'Predial mt2', 'Arriendo mt2']
    
    # Agrupar datos
    data = df.groupby(['year', 'label'])['valor'].sum().unstack(fill_value=0)
    years = data.index.tolist()
    
    # Reordenar las columnas según el orden especificado
    # Solo incluir las columnas que existen en los datos
    labels = [label for label in order if label in data.columns]
    data = data[labels]
    
    # Separar datasets por escala
    large_values = ['Transacciones mt2', 'Avalúo mt2', 'Venta mt2']
    medium_values = ['Predial mt2', 'Arriendo mt2']
    small_values = ['Transacciones', 'Listings arriendo']
    
    # Definir una gama de azules (de oscuro a menos oscuro)
    colors = [
        'rgba(0, 32, 96, 0.8)',    # Azul muy oscuro
        'rgba(0, 51, 153, 0.8)',   # Azul oscuro
        'rgba(0, 70, 171, 0.8)',   # Azul medio-oscuro
        'rgba(0, 90, 189, 0.8)',   # Azul medio
        'rgba(0, 109, 207, 0.8)',  # Azul medio-claro
        'rgba(0, 128, 225, 0.8)'   # Azul menos oscuro
    ]
    
    datasets = []
    for i, label in enumerate(labels):
        yAxisID = 'y1' if label in large_values else ('y2' if label in medium_values else 'y3')
        
        datasets.append({
            'label': label,
            'data': data[label].tolist(),
            'backgroundColor': colors[i % len(colors)],
            'borderColor': colors[i % len(colors)].replace('0.8', '1'),
            'borderWidth': 1,
            'yAxisID': yAxisID,
        })
    
    return f"""
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.0.0"></script>
    
    <canvas id="{name}" width="400" height="400"></canvas>
    <script>
    Chart.register(ChartDataLabels);
    var ctx = document.getElementById('{name}').getContext('2d');
    var {name} = new Chart(ctx, {{
        type: 'bar',
        data: {{
            labels: {years},
            datasets: {datasets}
        }},
        options: {{
            plugins: {{
                datalabels: {{
                    color: 'white',
                    anchor: 'center',
                    align: 'center',
                    rotation: -90,
                    font: {{
                        weight: 'bold',
                        size: 10
                    }},
                    formatter: function(value, context) {{
                        if (value >= 1000000) {{
                            return (value/1000000).toFixed(1) + 'M';
                        }} else if (value >= 1000) {{
                            return (value/1000).toFixed(1) + 'K';
                        }}
                        return value.toFixed(0);
                    }},
                    display: function(context) {{
                        return context.dataset.data[context.dataIndex] > 0;
                    }}
                }},
                legend: {{
                    display: true,
                    position: 'bottom',
                    align: 'center',
                    labels: {{
                        boxWidth: 20,
                        padding: 15,
                    }}
                }}
            }},
            scales: {{
                y1: {{
                    type: 'linear',
                    position: 'left',
                    beginAtZero: true,
                    title: {{
                        display: true,
                        text: 'Millones de pesos'
                    }},
                    ticks: {{
                        callback: function(value) {{
                            return (value/1000000).toFixed(1) + 'M';
                        }}
                    }},
                    grid: {{
                        display: false  // Quitar líneas de la grilla
                    }}
                }},
                y2: {{
                    type: 'linear',
                    position: 'right',
                    beginAtZero: true,
                    title: {{
                        display: true,
                        text: 'Miles de pesos'
                    }},
                    ticks: {{
                        callback: function(value) {{
                            return (value/1000).toFixed(1) + 'K';
                        }}
                    }},
                    grid: {{
                        display: false  // Quitar líneas de la grilla
                    }}
                }},
                y3: {{
                    type: 'linear',
                    position: 'right',
                    beginAtZero: true,
                    title: {{
                        display: true,
                        text: 'Unidades'
                    }},
                    ticks: {{
                        stepSize: 1
                    }},
                    grid: {{
                        display: false  // Quitar líneas de la grilla
                    }}
                }},
                x: {{
                    grid: {{ 
                        display: false  // Quitar líneas de la grilla
                    }},
                    title: {{
                        display: true,
                        text: 'Año'
                    }}
                }}
            }},
            responsive: true,
            maintainAspectRatio: false,
            title: {{
                display: true,
                text: 'Indicadores por Año',
                position: 'top',
                align: 'center',
                font: {{
                    size: 16
                }}
            }}
        }}
    }});
    </script>
    """

def pie_chart(df, name, title=''):

    colors = ['#4A148C', '#7B1FA2', '#9C27B0', '#BA68C8', '#E1BEE7',
              '#006837', '#66BD63', '#D9EF8B', '#00ACC1', '#4DD0E1', '#B2EBF2']
    
    #colors = ['#77CFF3', '#86cff4', '#96d0f6', '#a6d0f7', '#b6d1f9', 
    #          '#c5d2fa', '#dad2fc', '#D2EEFF', '#DFF3FF', '#DFD3FD']
    
    while len(colors) < len(df):
        colors.extend(colors)

    df = df.copy()
    df['color'] = colors[:len(df)]
    df = df.sort_values(by='ejey').copy()
    
    return f"""
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.0.0"></script>
    
    <div style="height: 400px; width: 100%;">
        <canvas id="{name}"></canvas>
    </div>
    
    <script>
    (function() {{
        Chart.register(ChartDataLabels);
        
        new Chart(document.getElementById('{name}'), {{
            type: 'pie',
            data: {{
                labels: {df['ejex'].tolist()},
                datasets: [{{
                    data: {df['ejey'].tolist()},
                    backgroundColor: {df['color'].tolist()},
                    borderColor: 'white',
                    borderWidth: 1
                }}]
            }},
            options: {{
                plugins: {{
                    datalabels: {{
                        color: 'white',
                        font: {{ size: 12, weight: 'bold' }},
                        formatter: function(value, context) {{
                            var total = context.dataset.data.reduce((a, b) => a + b, 0);
                            var percentage = Math.round((value / total) * 100);
                            return context.chart.data.labels[context.dataIndex] + '\\n(' + percentage + '%)';
                        }}
                    }},
                    legend: {{
                        position: 'bottom',
                        labels: {{
                            font: {{ size: 12 }}
                        }}
                    }},
                    title: {{
                        display: true,
                        text: '{title}',
                        font: {{ size: 16, weight: 'bold' }},
                        padding: 20
                    }}
                }},
                responsive: true,
                maintainAspectRatio: false
            }}
        }});
    }})();
    </script>
    """
    
def boxplot_chart(df, name, title=''):
    # Asignar colores si hay múltiples categorías
    colors = ['#4A148C', '#7B1FA2', '#9C27B0', '#BA68C8', '#E1BEE7',
              '#006837', '#66BD63', '#D9EF8B', '#00ACC1', '#4DD0E1', '#B2EBF2']

    while len(colors) < len(df):
        colors.extend(colors)

    # Preparar datos del boxplot: Chart.js requiere mínimos, máximos, cuartiles y medianas
    dataset = {
        'label': title,
        'data': [{
            'min': df['valor'].min(),
            'q1': df['valor'].quantile(0.25),
            'median': df['valor'].median(),
            'q3': df['valor'].quantile(0.75),
            'max': df['valor'].max()
        }],
        'backgroundColor': colors[0],
        'borderColor': colors[0],
        'borderWidth': 1
    }

    # Construir y retornar el HTML y el script JavaScript
    return f"""
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@sgratzl/chartjs-chart-boxplot"></script>
    
    <div style="height: 400px; width: 100%;">
        <canvas id="{name}"></canvas>
    </div>
    
    <script>
    (function() {{
        new Chart(document.getElementById('{name}'), {{
            type: 'boxplot',
            data: {{
                labels: ['{title}'],
                datasets: [{dataset}]
            }},
            options: {{
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    title: {{
                        display: true,
                        text: '{title}',
                        font: {{ size: 16, weight: 'bold' }},
                        padding: 20
                    }}
                }},
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: false,
                        min: {df['valor'].min()},
                        max: {df['valor'].max()},
                        grid: {{
                            display: false // Elimina líneas horizontales
                        }},
                        ticks: {{
                            precision: 0
                        }}
                    }},
                    x: {{
                        grid: {{
                            display: false // Elimina líneas verticales
                        }}
                    }}
                }}
            }}
        }});
    }})();
    </script>
    """
    
    
def polygon_to_geojson(geom):
    if isinstance(geom, Polygon):
        return {
            'type': 'Feature',
            'geometry': {
                'type': 'Polygon',
                'coordinates': [[[coord[0], coord[1]] for coord in geom.exterior.coords]]
            }
        }
    elif isinstance(geom, MultiPolygon):
        return {
            'type': 'FeatureCollection',
            'features': [
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': [[[coord[0], coord[1]] for coord in poly.exterior.coords]]
                    }
                }
                for poly in geom.geoms
            ]
        }
    else:
        raise ValueError("Input must be a Polygon or MultiPolygon")

def interpolate_color(color1, color2, factor):
    """Interpolate between two colors."""
    r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
    r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
    
    r = int(r1 + factor * (r2 - r1))
    g = int(g1 + factor * (g2 - g1))
    b = int(b1 + factor * (b2 - b1))
    
    return f'#{r:02x}{g:02x}{b:02x}'

def generate_color_function(num_pisos, color):
    # Color generation based on the number of floors
    if num_pisos == 0:
        return f"'fill-extrusion-color': '{color}',"
    
    # For single floor or existing buildings, use a fixed gray
    if num_pisos == 1:
        return f"'fill-extrusion-color': '{color}',"

    # For the additional building with multiple floors
    start_color = f"{color}"
    end_color = f"{color}"
    colors = [interpolate_color(start_color, end_color, i / (num_pisos - 1)) for i in range(num_pisos)]
    
    # Generate color function for Mapbox
    color_function = "'fill-extrusion-color': "
    for i, color in enumerate(colors):
        if i == 0:
            color_function += f"i === {i} ? '{color}'"
        else:
            color_function += f" : i === {i} ? '{color}'"
    color_function += " : '#FFFFFF',"
    
    return color_function


def generate_building_layers(idx, geojson, connpisos, color, altura_pisos):
    # Use a fixed gray color for existing buildings, including single-floor buildings
    color_function = generate_color_function(connpisos, color)

    layers = f"""
    map.addSource('edificio-{idx}', {{
        'type': 'geojson',
        'data': {json.dumps(geojson)}
    }});

    for (let i = 0; i < {connpisos}; i++) {{
        map.addLayer({{
            'id': `edificio-{idx}-piso-${{i}}`,
            'type': 'fill-extrusion',
            'source': 'edificio-{idx}',
            'paint': {{
                {color_function}
                'fill-extrusion-height': (i + 1) * {altura_pisos},
                'fill-extrusion-base': i * {altura_pisos},
                'fill-extrusion-opacity': 0.5
            }}
        }});
    }}
    """
    return layers

def mapa_leaflet(latitud, longitud, geojson, geopoints):
    html_mapa_leaflet = f"""
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
    <script>
        var geojsonData = {geojson};
        var geojsonPoints = {geopoints};
        
        var map_leaflet = L.map('3dmapbox').setView([{latitud}, {longitud}], 16);
        
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }}).addTo(map_leaflet);

        // Estilo para el geojson
        function style(feature) {{
            return {{
                color: feature.properties.color || '#3388ff',
                weight: 1,
            }};
        }}

        // Agregar geometría del geojson al mapa
        L.geoJSON(geojsonData, {{
            style: style
        }}).addTo(map_leaflet);

        // Agregar puntos al mapa
        function pointToLayer(feature, latlng) {{
            return L.circleMarker(latlng, {{
                radius: 0,
                //color: feature.properties.color || '#ff7800',
                weight: 0,
            }});
        }}

        L.geoJSON(geojsonPoints, {{
            pointToLayer: pointToLayer
        }}).addTo(map_leaflet);
    </script>
    """
    return html_mapa_leaflet
