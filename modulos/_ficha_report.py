import streamlit as st
import pdfcrowd
import pandas as pd
import re
import folium
import tempfile
import time
from sqlalchemy import create_engine 
from streamlit_folium import st_folium
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from datetime import datetime
import mapbox

def main(code=None,tipoinmueble=None,tiponegocio=None):

    with st.spinner('Buscando información'):
        data = getdatamarketbycode(code=code,tipoinmueble=tipoinmueble,tiponegocio=tiponegocio)
        if not data.empty:
            data         = data.to_dict(orient='records')[0]
            API_KEY      = st.secrets["API_KEY"]
            pdfcrowduser = st.secrets["pdfcrowduser"]
            pdfcrowdpass = st.secrets["pdfcrowdpass"]
            
            col1, col2,col3 = st.columns([3,1,1])
            with col2:
                if st.button('Generar Ficha en PDF'):
                    with st.spinner("Generando PDF"):
                        if st.session_state.html_pdf is not None:
                            fd, temp_path     = tempfile.mkstemp(suffix=".html")
                            wd, pdf_temp_path = tempfile.mkstemp(suffix=".pdf")       
                            
                            client = pdfcrowd.HtmlToPdfClient(pdfcrowduser,pdfcrowdpass)
                            client.convertStringToFile(st.session_state.html_pdf, pdf_temp_path)
                            client.setPageSize('Letter')
                            
                            with open(pdf_temp_path, "rb") as pdf_file:
                                PDFbyte = pdf_file.read()
                            
                            with col3:
                                st.download_button(label="Descargar Ficha",
                                                    data=PDFbyte,
                                                    file_name=f"ficha-codigo-{code}.pdf",
                                                    mime='application/octet-stream')
                            
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
            try:areaconstruida = int(data['areaconstruida'])
            except: pass
            try:habitaciones   = int(data['habitaciones'])
            except: pass
            try:banos          = int(data['banos'])
            except: pass
            try:garajes        = int(data['garajes'])
            except: pass
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
                    valoradministracion  = f'''<p class="caracteristicas-info">Administración:  ${valoradministracion:,.0f}</p>'''
                else: valoradministracion = ""
            except: valoradministracion = ""
            
            caracteristicas = f'<strong>{areaconstruida}</strong> mt<sup>2</sup> | <strong>{habitaciones}</strong> habitaciones | <strong>{banos}</strong> baños | <strong>{garajes}</strong> garajes'
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
        
            imagenes   = '<div class="property-card-images">\n'
            imagelinks = [x.strip() for x in data['url_img'].split('|')] if 'url_img' in data and isinstance(data['url_img'], str) else None
            conteo     = 0
            if isinstance(imagelinks, list):
                for i in imagelinks:
                    if isinstance(i, str) and len(i)>=7:
                        if 'sin_imagen' not in i:
                            imagenes += f'''<img src="{i}" alt="property image" onerror="this.src='https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png';">\n'''
                            conteo += 1
                    if conteo==2:
                        imagenes += '</div>\n'
                        imagenes += '<div class="property-card-images">\n'
                        conteo   = 0
            imagenes = BeautifulSoup(imagenes, 'html.parser')
            
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
            for i,j in outuput_list.items():
                if j is not None:
                    tabla_detalle += f""" 
                    <tr>
                      <td style="border-top:none; border-left:none;border-right:none;border-bottom: 1px solid #ccc;">
                        <h6 class="text-sm" style="margin-bottom: -20px">{i}</h6>
                      </td>
                      <td style="border-top:none; border-left:none;border-right:none;border-bottom: 1px solid #ccc;">
                        <h6 class="text-sm" style="margin-bottom: -20px">{j}</h6>
                      </td>                    
                    </tr>     
                    """
            tabla_detalle = f"""
            <div class="tabla_principal">
                <table class="table align-items-center mb-0">
                  {tabla_detalle}
                </table>
            </div>
            """
        
            #---------------------------------------------------------------------#
            # Descripcion
            #---------------------------------------------------------------------#
            descripcion_seccion = ""
            if descripcion!='':
                descripcion_seccion = f"""
                <div class="col-xl-12 col-sm-6 mb-xl-2 mb-0">
                  <div class="card">
                    <div class="card-body p-3">
                      <div class="container-fluid py-2">
                        <h6 class="caracteristicas-info">Descripción</h6>
                        <p class="text-justify">{descripcion}</p>            
                      </div>            
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
            for i,j in outuput_list.items():
                if j is not None:
                    tabla_contacto += f""" 
                    <tr>
                      <td style="border:none;">
                        <h6 class="text-sm" style="margin-bottom: -20px">{i}</h6>
                      </td>
                      <td style="border:none;">
                        <h6 class="text-sm" style="margin-bottom: -20px">{j}</h6>
                      </td>                    
                    </tr>     
                    """
        
            if isinstance(data['url'], str) and len(data['url'])>20: 
                link = f'''[Link]({data['url']})'''
                tabla_contacto += f"""
                <tr>
                  <td style="border:none;">
                    <h6 class="text-sm" style="margin-bottom: -20px">Ver inmueble</h6>
                  </td>
                  <td style="border:none;">
                    <h6 class="text-sm" style="margin-bottom: -20px">
                        <a href="{data['url']}">Link</a>
                    </h6>
                  </td>                    
                </tr>  
                """
        
            tabla_contacto = f"""
            <div class="tabla_principal">
                <h6 class="caracteristicas-info">Contacto</h6>
                <table class="table align-items-center mb-0">
                  {tabla_contacto}
                </table>
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
            style = """
            <style>
                .tabla_principal {
                  max-width: 100%; 
                  max-height: 100%; 
                }  
                .price-info {
                  font-family: 'Roboto', sans-serif;
                  font-size: 30px;
                  margin-top:30px;
                  margin-bottom: 10px;
                  text-align: left;
                }
                .caracteristicas-info {
                  font-family: 'Roboto', sans-serif;
                  font-size: 16px;
                  margin-bottom: 10px;
                  text-align: left;
                }
                .property-card-left {
                  width: 100%;
                  height: 100%; /* or max-height: 300px; */
                  overflow-y: scroll; /* enable vertical scrolling for the images */
                }
                .property-card-right {
                  width: 100%;
                  margin-left: 10px;
                }
            
                .text-justify {
                  text-align: justify;
                }
                
                .no-margin {
                  margin-bottom: 1px;
                }
                
                .price-part1 {
                  font-family: 'Comic Sans MS', cursive;
                  font-size: 24px;
                  margin-bottom: 1px;
                }
                
                .price-part2 {
                  font-size: 14px;
                  font-family: 'Comic Sans MS';
                  margin-bottom: 1px;
                }
        
                .nota {
                  font-size: 12px;
                }
                img{
                  max-width: 100%;
                  width: 45%;
                  height:250px;
                  object-fit: cover;
                  margin-bottom: 10px; 
                }
            </style>
            """
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
              <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/nucleo-icons.css" rel="stylesheet">
              <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/nucleo-svg.css" rel="stylesheet">
              <link id="pagestyle" href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/soft-ui-dashboard.css?v=1.0.7" rel="stylesheet">
              {style}
            </head>
            <body>
            <div class="row">
              <div class="col-xl-7 col-sm-0 mb-xl-0 mb-0">    
                {imagenes}
              </div>
                
              <div class="col-xl-5 col-sm-0 mb-xl-0 mb-0">
                
                <div class="col-xl-12 col-sm-6 mb-xl-2 mb-0">
                  <div class="card">
                    <div class="card-body p-3"> 
                      <div class="container-fluid py-2">
                        <h3 class="price-info">{precio}</h3>
                        {valoradministracion}
                        <p class="caracteristicas-info">{caracteristicas}</p>
                        <p class="caracteristicas-info">Código: <strong>{code}</strong></p>
                      </div>
                    </div>
                  </div>
                </div> 
                
                <div class="col-xl-12 col-sm-6 mb-xl-2 mb-0">
                  <div class="card">
                    <div class="card-body p-3">
                      <div class="container-fluid py-2">
                          {tabla_detalle}
                      </div>            
                    </div>        
                  </div>
                </div>
                
                {descripcion_seccion}
                
                <div class="col-xl-12 col-sm-6 mb-xl-2 mb-0">
                  <div class="card">
                    <div class="card-body p-3">
                      <div class="container-fluid py-2">
                          {tabla_contacto}
                      </div>            
                    </div>        
                  </div>
                </div>
                
                {mapa}
        
              </div>
            </div>
        
            </body>
            </html>
            """     
            texto = BeautifulSoup(html, 'html.parser')
            st.markdown(texto, unsafe_allow_html=True)
            
            
            #---------------------------------------------------------------------#
            # PDF
            #---------------------------------------------------------------------#
            pdf_tabla_detalle       = tabla_detalle[:]
            pdf_descripcion_seccion = descripcion_seccion[:]
            pdf_mapa                = mapa[:]
            
            pdf_tabla_detalle       = pdf_tabla_detalle.replace('-20px','0px')
            pdf_descripcion_seccion = pdf_descripcion_seccion.replace('mb-xl-2','mb-xl-0')
            pdf_mapa = pdf_mapa.replace('mb-xl-2','mb-xl-0')
            pdf_mapa = pdf_mapa.replace('style="width: 100%; height: 100%;"','style="width: 60%; height: 60%;display: flex; justify-content: center; align-items: center;"')
            #pdf_mapa = pdf_mapa.replace('420x250','250x150')
            
            html_pdf = f"""
            <!DOCTYPE html>
            <html>
            <head>
              <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/nucleo-icons.css" rel="stylesheet">
              <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/nucleo-svg.css" rel="stylesheet">
              <link id="pagestyle" href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/soft-ui-dashboard.css?v=1.0.7" rel="stylesheet">
              {style}
            </head>
            <body>
            <div class="row">
        
              <div class="col-xl-5 col-sm-0 mb-xl-0 mb-0">
                
                <div class="col-xl-12 col-sm-6 mb-xl-0 mb-0">
                  <div class="card">
                    <div class="card-body p-3"> 
                      <div class="container-fluid py-2">
                        <h3 class="price-info">{precio}</h3>
                        {valoradministracion}
                        <p class="caracteristicas-info">{caracteristicas}</p>
                        <p class="caracteristicas-info">Código: <strong>{code}</strong></p>
                      </div>
                    </div>
                  </div>
                </div> 
                
                <div class="col-xl-12 col-sm-6 mb-xl-0 mb-0">
                  <div class="card">
                    <div class="card-body p-3">
                      <div class="container-fluid py-2">
                          {pdf_tabla_detalle}
                      </div>            
                    </div>        
                  </div>
                </div>
                
                {pdf_descripcion_seccion}
                
                {pdf_mapa}
        
              <div class="col-xl-7 col-sm-0 mb-xl-0 mb-0">    
                {imagenes}
              </div>
              
              </div>
            </div>
        
            </body>
            </html>
            """     
            html_pdf = html_pdf.replace('p-3','p-1')
            html_pdf = html_pdf.replace('py-2','py-1')
            st.session_state.html_pdf = BeautifulSoup(html_pdf, 'html.parser')
                                
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
    
    
    