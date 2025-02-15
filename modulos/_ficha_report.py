import streamlit as st
import pandas as pd
import re
from sqlalchemy import create_engine 
from bs4 import BeautifulSoup
from datetime import datetime
#import mapbox

from functions._principal_getpdf import main as _principal_getpdf


def main(code=None,tipoinmueble=None,tiponegocio=None):

    coldownbutton1,coldownbutton2 = st.columns([0.7,0.3])
    
    with st.spinner('Buscando información'):
        data = getdatamarketbycode(code=code,tipoinmueble=tipoinmueble,tiponegocio=tiponegocio)
        if not data.empty:
            data = data.to_dict(orient='records')[0]
            
            #-------------------------------------------------------------------------#
            # Catacteristicas del inmueble
            ciudad,localidad,barrio,tipoinmueble,direccion,latitud,longitud,estrato,areaconstruida,habitaciones,banos,garajes,precio = [None,None,None,None,None,None,None,None,None,None,None,None,None]
            
            try: ciudad        = data['mpio_cnmbr']
            except: pass
            try:localidad      = data['locnombre']
            except: pass
            try:barrio         = data['scanombre']
            except: pass
            try:tipoinmueble   = data['tipoinmueble']
            except: pass
            try:direccion      = data['direccion']
            except: pass
            try:latitud        = data['latitud']
            except: pass
            try:longitud       = data['longitud']
            except: pass
            try:estrato        = int(data['estrato'])
            except: pass
            try: 
                areaconstruida = int(data['areaconstruida'])
                areaconstruida = f'<strong>{areaconstruida} </strong> mt<sup>2</sup>' if isinstance(areaconstruida,int) else "" 
            except: pass

            try:
                habitaciones   = int(data['habitaciones'])
                if habitaciones==1:
                    habitaciones = f' | <strong>{habitaciones} </strong> Habitación' if isinstance(habitaciones,int) else "" 
                elif habitaciones>1:
                    habitaciones = f' | <strong>{habitaciones} </strong> Habitaciones' if isinstance(habitaciones,int) else ""
                else: habitaciones = ''
            except: habitaciones = ''
            try:
                banos = int(data['banos'])
                if banos==1:
                    banos = f' | <strong>{banos} </strong> Baño' if isinstance(banos,int) else "" 
                elif banos>1:
                    banos = f' | <strong>{banos} </strong> Baños' if isinstance(banos,int) else "" 
                else: banos = ''
            except: banos = ''
            try:
                garajes = int(data['garajes'])
                if garajes==1:
                    garajes = f' | <strong>{garajes} </strong> Garaje' if isinstance(garajes,int) else "" 
                elif garajes>1:
                    garajes = f' | <strong>{garajes} </strong> Garajes' if isinstance(garajes,int) else "" 
                else: garajes = ''
            except: garajes = ''
            try:
                precio = data['valor']
                precio = f'${precio:,.0f}'
            except: pass
        
            try:    antiguedad = datetime.now().year-int(data['antiguedad'])
            except: antiguedad = ""
            try:    piso = int(data['piso'])
            except: piso = ""
            try:
                if data['valoradministracion'] is not None and float(data['valoradministracion'])>0:
                    valoradministracion = data['valoradministracion']
                    valoradministracion  = f'''Administración:  ${valoradministracion:,.0f}'''
                else: valoradministracion = ""
            except: valoradministracion = ""
            
            #caracteristicas = f'<strong>{areaconstruida} </strong> mt<sup>2</sup> | if isinstance(areaconstruida,(float,int)) else "" <strong>{habitaciones}</strong> habitaciones | <strong>{banos}</strong> baños | <strong>{garajes}</strong> garajes'
            caracteristicas = f'{areaconstruida}{habitaciones}{banos}{garajes}'

            try:
                descripcion     = data['descripcion']
                descripcion     = homogenizar_texto(descripcion)
            except: descripcion = ''
            
            #-------------------------------------------------------------------------#
            # Datos de contacto
            telefono1    = data['telefono1'] if 'telefono1' in data and isinstance(data['telefono1'], str) else ''
            telefono2    = data['telefono2'] if 'telefono2' in data and isinstance(data['telefono2'], str) else ''
            telefono3    = data['telefono3'] if 'telefono3' in data and isinstance(data['telefono3'], str) else ''
            email        = data['email1']    if 'email1' in data and isinstance(data['email1'], str) else ''
            inmobiliaria = data['inmobiliaria'] if 'inmobiliaria' in data and isinstance(data['inmobiliaria'], str) else ''
            
            #-------------------------------------------------------------------------#
        
            imagelinks = [x.strip() for x in data.get("url_img", "").split("|")] if isinstance(data.get("url_img"), str) else []
    
            imagenes = """
            <div class="urbex-col-12 urbex-col-lg-7">
              <div class="urbex-row">
            """
            conteo = 0
             
            for i in imagelinks:
                if isinstance(i, str) and len(i) >= 7 and "sin_imagen" not in i:
                    imagenes += f"""
            <div class="urbex-col-6">
                 <div class="urbex-d-flex urbex-flex-column urbex-h-100 urbex-p-2" id="box_shadow_default">
                  <img src="{i}" alt="property image" style="height: 250px;width: 100%;" onerror="this.src='https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png';"/>
                 </div>
            </div>
            """
                conteo += 1
                
            imagenes += """
              </div>
            </div>
            """

            
            #---------------------------------------------------------------------#
            # Detalle del inmueble
            #---------------------------------------------------------------------#
            outuput_list = {'Ciudad':None,'Dirección':None,'Localidad':None,'Barrio':None,'Tipo de inmueble':None,'Estrato':None,'Antiguedad':None,'Piso':None}
            if isinstance(ciudad, str) and len(ciudad)>=4: outuput_list.update({'Ciudad':ciudad})
            if isinstance(direccion, str) and len(direccion)>=7: outuput_list.update({'Dirección':direccion})
            if isinstance(localidad, str) and len(localidad)>=4: outuput_list.update({'Localidad':localidad})
            if isinstance(barrio, str) and len(barrio)>=4: outuput_list.update({'Barrio':barrio})
            if isinstance(tipoinmueble, str) and len(tipoinmueble)>=4: outuput_list.update({'Tipo de inmueble':tipoinmueble})
            if isinstance(estrato, int) or isinstance(estrato, float): outuput_list.update({'Estrato':int(estrato)})
            if isinstance(antiguedad, int) or isinstance(antiguedad, float): outuput_list.update({'Antiguedad':int(antiguedad)})
            if isinstance(piso, int) or isinstance(piso, float): outuput_list.update({'Piso':int(piso)})
        
            tabla_detalle = ""
            for i, j in outuput_list.items():
                if j is not None:
                    tabla_detalle += f"""
                    <tr>
                      <td>
                        <span id="label_inside">{i}</span>
                      </td>
                      <td>
                        <span id="value_inside">{j}</span>
                      </td>                    
                    </tr>     
                    """
            
            tabla_detalle = f"""
            <div class="urbex-col-12" style="margin-top:20px">
                <div class="urbex-text-center urbex-d-flex urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
                    <div class="urbex-table-responsive urbex-flex-grow-1" style="line-height: 0.5;">
                        <table class="urbex-table urbex-table-sm urbex-table-borderless">
                            <tbody>
                                {tabla_detalle}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            """
                    
            #---------------------------------------------------------------------#
            # Telefonos y link
            #---------------------------------------------------------------------#
            outuput_list = {'Telefono 1:':None,'Telefono 2:':None,'Telefono 3:':None,'Email contacto:':None,'Inmobilairia:':None}
            if isinstance(telefono1, str) and len(telefono1)>=7: outuput_list.update({'Telefono 1:':telefono1})
            if (isinstance(telefono1, int) or isinstance(telefono1, float)) and len(str(telefono1))>=7: outuput_list.update({'Telefono 1:':telefono1})
            if isinstance(telefono2, str) and len(telefono2)>=7: outuput_list.update({'Telefono 2:':telefono2})
            if (isinstance(telefono2, int) or isinstance(telefono2, float)) and len(str(telefono2))>=7: outuput_list.update({'Telefono 2:':telefono2})
            if isinstance(telefono3, str) and len(telefono3)>=7: outuput_list.update({'Telefono 3:':telefono3})
            if (isinstance(telefono3, int) or isinstance(telefono3, float)) and len(str(telefono3))>=7: outuput_list.update({'Telefono 3:':telefono3})
            if isinstance(email, str) and '@' in email: outuput_list.update({'Email contacto:':email})
            if isinstance(inmobiliaria, str) and len(inmobiliaria)>=4: outuput_list.update({'Inmobilairia:':inmobiliaria})
            
            
            tabla_contacto = ""
            for i, j in outuput_list.items():
                if j is not None:
                    tabla_contacto += f"""
                    <tr>
                      <td>
                        <span id="label_inside">{i}</span>
                      </td>
                      <td>
                        <span id="value_inside">{j}</span>
                      </td>                    
                    </tr>     
                    """
            
            if isinstance(data['url'], str) and len(data['url']) > 20:
                link = f'''[Link]({data['url']})'''
                tabla_contacto += f"""
                <tr>
                  <td>
                    <span id="label_inside">Ver inmueble</span>
                  </td>
                  <td>
                    <span id="value_inside">
                        <a href="{data['url']}">Link</a>
                    </span>
                  </td>                    
                </tr>  
                """
            
            tabla_contacto = f"""
            <div class="urbex-col-12" style="margin-top:20px">
                <div class="urbex-text-center urbex-d-flex urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
                    <div class="urbex-table-responsive urbex-flex-grow-1" style="line-height: 0.5;">
                        <table class="urbex-table urbex-table-sm urbex-table-borderless">
                            <tbody>
                                {tabla_contacto}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            """

        
            #---------------------------------------------------------------------#
            # Mapa
            #---------------------------------------------------------------------#
            #if latitud is not None and latitud
            
            
            # Gogole maps
            #mapa = f"""
            #<div class="col-xl-12 col-sm-6 mb-xl-2 mb-0">
            #  <div class="card">
            #    <div class="card-body p-3">
            #      <div class="container-fluid py-2">
            #          <img src="https://maps.googleapis.com/maps/api/staticmap?center={latitud},{longitud}&zoom=15&size=420x250&markers=color:blue|{latitud},{longitud}&style=feature:administrative|element:labels|visibility:off&style=feature:landscape|element:labels|visibility:off&style=feature:poi|element:labels|visibility:off&style=feature:road.highway|element:labels|visibility:on&style=feature:road.arterial|element:labels|visibility:on&style=feature:road.local|element:labels|visibility:on&style=feature:transit|element:labels|visibility:off&style=feature:water|element:labels|visibility:off&key={API_KEY}" alt="Google Map" style="width: 100%; height: 100%;">
            #      </div>            
            #    </div>        
            #  </div>
            #</div>
            #"""
            
            # Mapbox
            # https://www.mapbox.com/maps
            # Estilos de mapas mapbox: https://docs.mapbox.com/api/maps/styles/#mapbox-styles
            access_token = 'pk.eyJ1IjoiYWdhdmlyaWFqIiwiYSI6ImNrYWQ4dXlvZzIyMXIyeW50aHJldGVtcmgifQ.j7XuNBmPQ8SlrUeTPWsrNQ'
            static_map_url = f'https://api.mapbox.com/styles/v1/mapbox/streets-v12/static/pin-s+3b83bd({longitud},{latitud})/{longitud},{latitud},14,0,0/420x250?access_token={access_token}'
            #static_map_url = f'https://api.mapbox.com/styles/v1/mapbox/streets-v11/static/url-https%3A%2F%2Fdocs.mapbox.com%2Fapi%2Fimg%2Fcustom-marker.png({longitud},{latitud})/{longitud},{latitud},15,0,0/420x250?access_token={access_token}'
        
            mapa = f"""
            <div class="col-xl-12 col-sm-6 mb-xl-2 mb-0">
              <div class="card">
                <div class="card-body p-3">
                  <div class="container-fluid py-2">
                      <img src="{static_map_url}" alt="Mapbox Map" class="property-map" style="width: 100%; height: 100%;">
                  </div>            
                </div>        
              </div>
            </div>
            """              
            
            #m = folium.Map(location=[latitud, longitud], zoom_start=12, tiles="cartodbpositron")
            #folium.Marker(location=[latitud, longitud]).add_to(m)
            #m.save("map.html")
            #mapa = open("map.html").read()
            #st.components.v1.html(mapa)
            #mapa = BeautifulSoup(mapa, 'html.parser')
            #mapa_head   = str(mapa.head).replace('<head>','').replace('</head>','')
            #mapa_script = str(mapa.findAll('script')[-1])
            #body        = str(mapa.body).replace('<body>','').replace('</body>','')
                    
            
            
            #<img src="https://maps.googleapis.com/maps/api/staticmap?center={latitud},{longitud}&zoom=16&size=400x200&markers=color:blue|{latitud},{longitud}&key={API_KEY}" alt="Google Map" class="property-map">
            
            
        
            #---------------------------------------------------------------------#
            # Visual
            #---------------------------------------------------------------------#
            html = f"""
            <!DOCTYPE html>
            <html data-bs-theme="light" lang="en">
            <head>
              <meta charset="utf-8"/>
              <meta content="width=device-width, initial-scale=1.0, shrink-to-fit=no" name="viewport"/>
              <link href="https://iconsapp.nyc3.digitaloceanspaces.com/_estilo_general/prefixed_bootstrap.min.css" rel="stylesheet"/>
              <link href="https://iconsapp.nyc3.digitaloceanspaces.com/_estilo_general/prefixed_styles.css" rel="stylesheet"/>
              <style>
        
                body::-webkit-scrollbar {{
                    display: none;
                }}
                
                .precio {{
                        font-size: 24px;
                        font-weight: bold;
                        margin-top:20px;
                        margin-left: 20px;
                        text-align: left;
                    }}
                .caracteristicas, .valor-admin, .codigo {{
                    font-size: 16px;
                    font-weight: normal;
                    margin-left: 20px;
                    text-align: left;
                }}
                .codigo strong {{
                    font-weight: bold;
                    margin-left: 20px;
                    text-align: left;
                }}
                    
                .urbex-table {{
                    margin-top:20px;
                    width: 100%;
                    font-size: 16px;
                    border: none;
                }}
                
                .urbex-table tr, 
                .urbex-table th, 
                .urbex-table td {{
                    border: none;
                    padding: 8px;
                    text-align: left;
                }}
                
                #label_inside, #value_inside {{
                    font-size: 16px;
                    font-weight: normal;
                    text-align: left;
                }}
    
                #label_descripcion {{
                    margin-top:20px;
                    font-size: 24px;
                    font-weight: bold;
                    color: black;
                    text-align: left;
                }}
    
                #texto_descripcion {{
                    font-size: 16px;
                    color: black;
                    text-align: justify;
                }}
    
              </style>
        
            </head>
            <body>
              <section>
               <div class="urbex-container-fluid">
                <div class="urbex-row">
                {imagenes}
                 <div class="urbex-col-12 urbex-col-lg-5">
                  <div class="urbex-row">
                   <div class="urbex-col-12">
                    <div class="urbex-text-center urbex-d-flex urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
                     <p class="precio">
                      {precio}
                     </p>
                     <p class="caracteristicas">
                      {tiponegocio if isinstance(tiponegocio,str) else ""}
                     </p>
                     <p class="caracteristicas">
                      {caracteristicas}
                     </p>
                     <p class="valor-admin">
                      {valoradministracion}
                     </p>
                     <p class="codigo">
                      Código:<strong>{code}</strong>
                     </p>
                    </div>
                   </div>
                   {tabla_detalle}
                   <div class="urbex-col-12" style="margin-top:20px">
                    <div class="urbex-text-center urbex-d-flex urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
                     <p id="label_descripcion">
                      Descripción:
                     </p>
                     <p id="texto_descripcion">
                      {descripcion}
                     </p>
                    </div>
                   </div>
                   {tabla_contacto}
                   <div class="urbex-col-12" style="margin-top:20px">
                    <div class="urbex-text-center urbex-d-flex urbex-h-100 urbex-d-flex urbex-flex-column" id="box_shadow_default">
                     <img src="{static_map_url}" alt="Mapbox Map" class="property-map" style="width: 100%; height: 100%;">
                    </div>
                   </div>
                  </div>
                 </div>
                </div>
               </div>
              </section>
            </body>
            </html>
            """     
            texto = BeautifulSoup(html, 'html.parser')
            st.markdown(texto, unsafe_allow_html=True)
            
            
        with coldownbutton2:
            if st.button('Generar PDF'):
                with st.spinner('Procesando PDF...'):
                    
                    # Html version pdf
                    pdf_bytes = _principal_getpdf(html,seccion='_download_pdf_detalle_building')
                    
                    if pdf_bytes:
                        # Ofrecer el PDF para descarga
                        st.download_button(
                            label="Descargar PDF",
                            data=pdf_bytes,
                            file_name="reporte.pdf",
                            mime='application/pdf'
                        )
                    else:
                        st.error("Error al generar el PDF. Por favor intente nuevamente.")
                        
@st.cache_data(show_spinner=False)
def homogenizar_texto(texto):
    # Remover múltiples espacios en blanco
    texto = re.sub(r'\s+', ' ', texto)
    # Poner todo en minúsculas, a menos que la palabra empiece después de una puntuación
    texto = re.sub(r'(?<=[^\w\s])\w+', lambda x: x.group().lower(), texto)
    # Remover caracteres no alfanuméricos
    texto = re.sub(r'[^\w\s.,;]', '', texto)
    # Remover cuando hay codigos dentro del texto
    texto = re.sub(r'C\w+ Fincaraíz: \d+', '', texto)
    # Remover telefono
    texto = re.sub(r'\b\d{7,}\b', '', texto)
    texto = texto.replace('Código Fincaraíz',' ')
    return texto

@st.cache_data(show_spinner=False)
def getdatamarketbycode(code=None,tipoinmueble=None,tiponegocio=None):
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    datamarketactivos   = pd.read_sql_query(f"SELECT * FROM bigdata.market_portales_activos WHERE code='{code}'" , engine)
    datamarkethistorico = pd.read_sql_query(f"SELECT * FROM bigdata.market_portales_historico WHERE code='{code}'" , engine)
    engine.dispose()
    
    data = pd.DataFrame()
    if not datamarketactivos.empty: 
        data = datamarketactivos.copy()
    elif not datamarkethistorico.empty:
        data = datamarkethistorico.copy()
    return data    
    
    
    
