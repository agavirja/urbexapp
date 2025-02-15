import streamlit as st
import requests
import pandas as pd
import os
import urllib.parse
import re
import nest_asyncio
import aiohttp
import asyncio
import ssl
from pypdf import PdfReader, PdfWriter
from sqlalchemy import create_engine 

@st.cache_data(show_spinner=False)
def main(chip=None,barmanpre=None,arealote=None):
    
    urlist      = []
    PDFbyte     = None
    codigo_lote = None
    
    if isinstance(barmanpre,str) and barmanpre!='':
        barmanpre = barmanpre.split('|')
    if isinstance(barmanpre,list) and barmanpre!=[]:
        user     = st.secrets["user_bigdata"]
        password = st.secrets["password_bigdata"]
        host     = st.secrets["host_bigdata_lectura"]
        schema   = st.secrets["schema_bigdata"]
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')

        lista        = "','".join(barmanpre)
        query        = f" barmanpre IN ('{lista}')"
        datacatastro = pd.read_sql_query(f"SELECT barmanpre,prechip FROM  bigdata.data_bogota_catastro WHERE {query} AND (preaconst, barmanpre) IN (SELECT MAX(preaconst) AS max_preaconst, barmanpre  FROM  bigdata.data_bogota_catastro WHERE {query} GROUP BY barmanpre)" , engine)
        if chip is None:
            chip = list(datacatastro['prechip'].unique())
            
    if isinstance(chip,str) and chip!='':
        chip = chip.split('|')
    if isinstance(chip,list) and chip!=[]:
        codigo_lote = chip2codigolote_sinupot(chip)
    
    # Licencias
    if isinstance(codigo_lote,list) and codigo_lote!=[]:
        for codigo in codigo_lote:
            # Licencias
            params = {
                "f": "json",
                "where": f"CODIGO_LOTE = '{codigo}'",
                "returnGeometry": "false",
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "NEW_ID_EXPEDIENTE",
                "returnDistinctValues": "true"
            }
            url = "https://sinupot.sdp.gov.co/serverp/rest/services/Consultas/MapServer/15/query?" + urllib.parse.urlencode(params)
            try:    r = requests.get(url,verify=False).json()
            except: r = None
            
            if r is not None:
                if 'features' in r:
                    for j in r['features']:
                        if 'attributes' in j and 'NEW_ID_EXPEDIENTE' in j['attributes']:
                            codigo = j['attributes']['NEW_ID_EXPEDIENTE']
                            urlist.append({'tipo':'expendiente','numero':codigo,'url':f'https://sinupot.sdp.gov.co/serverp/rest/services/Reportes/GeneracionReportes/GPServer/GeneracionReportes/execute?f=json&tipo=LIC&codigo={codigo}&generar=true','pdf':None})
    # Reporte [chip]
    if isinstance(chip,list) and chip!=[]:
        for ichip in chip:
            url = f'https://sinupot.sdp.gov.co/serverp/rest/services/Reportes/GeneracionReportes/GPServer/GeneracionReportes/execute?f=json&tipo=CONS&codigo={ichip}&generar=true'
            urlist.append({'tipo':'reporte','url':url,'pdf':None})
        
    # Plusvalia:
    if isinstance(chip,list) and chip!=[]:
        for ichip in chip:
            url = f'https://sinupot.sdp.gov.co/serverp/rest/services/Reportes/GeneracionReportes/GPServer/GeneracionReportes/execute?f=json&tipo=PLUS&codigo={ichip}&generar=true'
            urlist.append({'tipo':'plusvalia','url':url,'pdf':None})
    
    # Estacion telecomunicacion
    if isinstance(chip,list) and chip!=[]:
        for ichip in chip:
            url = f'https://sinupot.sdp.gov.co/serverp/rest/services/Reportes/GeneracionReportes/GPServer/GeneracionReportes/execute?f=json&tipo=ESTE&codigo={ichip}&generar=true'
            urlist.append({'tipo':'telecomunicacion','url':url,'pdf':None})
        
    # Estratificacion
    if isinstance(chip,list) and chip!=[]:
        for ichip in chip:
            codigo_json = {"chip": ichip, "generado": ""}
            codigo_encoded = urllib.parse.quote(str(codigo_json).replace("'", '"'))
            url = f'https://sinupot.sdp.gov.co/serverp/rest/services/Reportes/GeneracionReportes/GPServer/GeneracionReportes/execute?f=json&tipo=EXT&codigo={codigo_encoded}&generar=true'
            urlist.append({'tipo':'estratificacion','url':url,'pdf':None})
    
    # Pot 555
    tipoarea = clasificar_area_lote(arealote)
    if isinstance(chip,list) and chip!=[] and isinstance(tipoarea,str) and tipoarea!='':
        formato    = {'UNIFAMILIAR-BIFAMILIAR': '101', 'MULTIFAMILIAR-COLECTIVA': '102', 'HABITACIONALES CON SERVICIOS': '103', 'COMERCIOS Y SERVICIOS BASICOS': '201', 'SERVICIOS DE OFICINAS Y SERVICIOS DE HOSPEDAJE': '202', 'SERVICIOS AL AUTOMOVIL': '203', 'SERVICIOS ESPECIALES': '204', 'SERVICIOS LOGISTICOS': '205', 'PRODUCCION ARTESANAL': '301', 'INDUSTRIA LIVIANA': '302', 'INDUSTRIA MEDIANA': '303', 'INDUSTRIA PESADA': '304', 'DOTACIONAL': '401'}
        for key, value in formato.items():
            for ichip in chip:
                codigo_json    = {"chip": ichip,"tipocodigo": "subuso","codigo": value,"tipo": tipoarea}
                codigo_encoded = urllib.parse.quote(str(codigo_json).replace("'", '"'))
                url            = f'https://sinupot.sdp.gov.co/serverp/rest/services/Reportes/GeneracionReportes/GPServer/GeneracionReportes/execute?f=json&tipo=RSPU&codigo={codigo_encoded}&generar=true'
                urlist.append({'tipo':'usosueloPOT555','url':url,'pdf':None})
    
    # POT 190
    if isinstance(chip,list) and chip!=[]:
        for ichip in chip:
            url = f'https://sinupot.sdp.gov.co/serverp/rest/services/Reportes/GeneracionReportes/GPServer/GeneracionReportes/execute?f=json&tipo=NURB&codigo={ichip}&generar=true'
            urlist.append({'tipo':'pot190','url':url,'pdf':None})
    
            # reserva vial POT 190
            url = f'https://sinupot.sdp.gov.co/serverp/rest/services/Reportes/GeneracionReportes/GPServer/GeneracionReportes/execute?f=json&tipo=REVI&codigo={ichip}&generar=true'
            urlist.append({'tipo':'reservavialpot190','url':url,'pdf':None})
    
            # reserva vial POT 190
            url = f'https://sinupot.sdp.gov.co/serverp/rest/services/Reportes/GeneracionReportes/GPServer/GeneracionReportes/execute?f=json&tipo=AME&codigo={ichip}&generar=true'
            urlist.append({'tipo':'zonasamenazapot190','url':url,'pdf':None})

    if isinstance(urlist,list) and urlist!=[]:
        PDFbyte = getpdfsinupot(urlist)

    return PDFbyte


@st.cache_data(show_spinner=False)
def getpdfsinupot(urlist):
    PDFbyte = None
    #-----------------------------------------------------------------------------#
    # Requests paralelo y asyncronico
    if isinstance(urlist,list) and urlist!=[]:
        nest_asyncio.apply()

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        async def fetch_pdf(session, url_info):
            try:
                async with session.get(url_info['url'], ssl=ssl_context) as response:  # ssl=ssl_context deshabilita la verificación
                    r = await response.json()
                    pdf_url = r['results'][0]['value']['url'] if r.get('results') else None
                    url_info['pdf'] = pdf_url
            except:
                url_info['pdf'] = None
            return url_info
        
        async def fetch_all_pdfs(urls):
            async with aiohttp.ClientSession() as session:
                tasks = [fetch_pdf(session, url_info) for url_info in urls]
                return await asyncio.gather(*tasks)
        
        async def main():
            await fetch_all_pdfs(urlist)
        
        asyncio.run(main())
        
        #-----------------------------------------------------------------------------#
        # Consolidar todos los pdf en uno solo
        pdf_urls = []
        for i in urlist:
            if 'pdf' in i and isinstance(i['pdf'],str) and i['pdf']!='':
                pdf_urls.append(i['pdf'])

        #-----------------------------------------------------------------------------#
        # Consolidar todos los pdf en uno solo
        output_pdf = 'combined.pdf'
        writer = PdfWriter()  # Usar PdfWriter en lugar de PdfMerger
        
        for idx, url in enumerate(pdf_urls):
            try:
                response = requests.get(url, verify=False)
                response.raise_for_status()
                temp_pdf = f'temp_{idx}.pdf'
                with open(temp_pdf, 'wb') as file:
                    file.write(response.content)
                
                try:
                    reader = PdfReader(temp_pdf)
                    for page in range(len(reader.pages)):
                        writer.add_page(reader.pages[page])  # Agregar cada página al PdfWriter
                except: pass
                finally:
                    os.remove(temp_pdf)
            except: pass
        
        with open(output_pdf, 'wb') as final_pdf:
            writer.write(final_pdf)
            
        with open(output_pdf, "rb") as pdf_file:
            PDFbyte = pdf_file.read()
            
    return PDFbyte

def extract_year(titulo):
    match = re.search(r'\b(19|20)\d{2}\b', titulo)
    return int(match.group()) if match else None

@st.cache_data(show_spinner=False)
def chip2codigolote_sinupot(chip):
    user       = st.secrets["user_bigdata"]
    password   = st.secrets["password_bigdata"]
    host       = st.secrets["host_bigdata_lectura"]
    schema     = st.secrets["schema_bigdata"]
    engine     = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    codigolote = None
    if isinstance(chip, str) and chip!='':
        datacatastro = pd.read_sql_query(f"SELECT precbarrio,precmanz,precpredio FROM  bigdata.data_bogota_catastro WHERE prechip='{chip}'" , engine)
        if not datacatastro.empty:
            codigolote = f"{datacatastro['precbarrio'].iloc[0]}{datacatastro['precmanz'].iloc[0]}{datacatastro['precpredio'].iloc[0]}"

    if isinstance(chip, list) and chip!=[]:
        lista        = "','".join(chip)
        query        = f" prechip IN ('{lista}')"
        datacatastro = pd.read_sql_query(f"SELECT precbarrio,precmanz,precpredio FROM  bigdata.data_bogota_catastro WHERE {query}" , engine)
        if not datacatastro.empty:
            datacatastro['codigo'] = datacatastro.apply(lambda x: f"{x['precbarrio']}{x['precmanz']}{x['precpredio']}",axis=1)
            codigolote             = list(datacatastro['codigo'].unique())
    engine.dispose()
    return codigolote

@st.cache_data(show_spinner=False)
def clasificar_area_lote(area):
    if area is None:
        return None
    else:
        if area < 500:
            return 'TIPO 1' # 'Menor a 500 m2'
        elif 500 <= area <= 4000:
            return 'TIPO 2' # 'Entre 500 y 4.000 m2'
        else:
            return 'TIPO 3' # 'Mayor a 4.000 m2'
    