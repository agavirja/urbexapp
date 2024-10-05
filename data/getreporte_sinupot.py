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
from pypdf import PdfMerger, PdfReader
from sqlalchemy import create_engine 
from bs4 import BeautifulSoup
from multiprocessing.dummy import Pool

from data.getdatabuilding import chip2codigolote_sinupot

def main(chip=None,barmanpre=None,reporte_chip=True,licencias=True,plusvalia=True,estratificacion=True,telecomunicacion=True,pot_190=True):
    
    if chip is not None or barmanpre is not None:
        st.write('')
        titulo = 'Reporte completo del inmueble (SINUPOT)'
        html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
        texto  = BeautifulSoup(html, 'html.parser')
        st.markdown(texto, unsafe_allow_html=True)

        col1,col2 = st.columns(2)
        with col1:
            formato    = {'NINGUNO':'000','UNIFAMILIAR-BIFAMILIAR': '101', 'MULTIFAMILIAR-COLECTIVA': '102', 'HABITACIONALES CON SERVICIOS': '103', 'COMERCIOS Y SERVICIOS BASICOS': '201', 'SERVICIOS DE OFICINAS Y SERVICIOS DE HOSPEDAJE': '202', 'SERVICIOS AL AUTOMOVIL': '203', 'SERVICIOS ESPECIALES': '204', 'SERVICIOS LOGISTICOS': '205', 'PRODUCCION ARTESANAL': '301', 'INDUSTRIA LIVIANA': '302', 'INDUSTRIA MEDIANA': '303', 'INDUSTRIA PESADA': '304', 'DOTACIONAL': '401'}
            tipo       = st.selectbox('Confirma uso del suelo POT 555',options=list(formato))
            tipocodigo = formato[tipo]
            
        with col2:
            formato  = {'Menor a 500 m2':'TIPO 1','Entre 500 y 4.000 m2':'TIPO 2','Mayor a 4.000 m2':'TIPO 3'}
            tipo     = st.selectbox('Área construida destinada al uso',options=list(formato))
            tipoarea = formato[tipo]
            
        st.write('')
        st.write('')
        col1,col2 = st.columns(2)
        PDFbyte = False
        with col1:
            if st.button('Generar Reporte SINUPOT'):
                with st.spinner("Generando PDF"):
                    PDFbyte = generalSINUPOT(chip=chip,barmanpre=barmanpre,tipocodigo=tipocodigo,tipoarea=tipoarea,reporte_chip=reporte_chip,licencias=licencias,plusvalia=plusvalia,estratificacion=estratificacion,telecomunicacion=telecomunicacion,pot_190=pot_190)
        if PDFbyte:
            with col2:
                st.download_button(label="Descargar Reporte",
                                    data=PDFbyte,
                                    file_name=f"reporte-sinupot-{chip}.pdf",
                                    mime='application/octet-stream')
        st.write('')
        st.write('')

@st.cache_data(show_spinner=False)
def generalSINUPOT(chip=None,barmanpre=None,tipocodigo=None,tipoarea=None,reporte_chip=True,licencias=True,plusvalia=True,estratificacion=True,telecomunicacion=True,pot_190=True):
    
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
    if licencias:
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
    if reporte_chip:
        if isinstance(chip,list) and chip!=[]:
            for ichip in chip:
                url = f'https://sinupot.sdp.gov.co/serverp/rest/services/Reportes/GeneracionReportes/GPServer/GeneracionReportes/execute?f=json&tipo=CONS&codigo={ichip}&generar=true'
                urlist.append({'tipo':'reporte','url':url,'pdf':None})
        
    # Plusvalia:
    if plusvalia:
        if isinstance(chip,list) and chip!=[]:
            for ichip in chip:
                url = f'https://sinupot.sdp.gov.co/serverp/rest/services/Reportes/GeneracionReportes/GPServer/GeneracionReportes/execute?f=json&tipo=PLUS&codigo={ichip}&generar=true'
                urlist.append({'tipo':'plusvalia','url':url,'pdf':None})
        
    # Estacion telecomunicacion
    if telecomunicacion:
        if isinstance(chip,list) and chip!=[]:
            for ichip in chip:
                url = f'https://sinupot.sdp.gov.co/serverp/rest/services/Reportes/GeneracionReportes/GPServer/GeneracionReportes/execute?f=json&tipo=ESTE&codigo={ichip}&generar=true'
                urlist.append({'tipo':'telecomunicacion','url':url,'pdf':None})
        
    # Estratificacion
    if estratificacion:
        if isinstance(chip,list) and chip!=[]:
            for ichip in chip:
                codigo_json = {"chip": ichip, "generado": ""}
                codigo_encoded = urllib.parse.quote(str(codigo_json).replace("'", '"'))
                url = f'https://sinupot.sdp.gov.co/serverp/rest/services/Reportes/GeneracionReportes/GPServer/GeneracionReportes/execute?f=json&tipo=EXT&codigo={codigo_encoded}&generar=true'
                urlist.append({'tipo':'estratificacion','url':url,'pdf':None})
    # Pot 555
    if isinstance(chip,list) and chip!=[] and isinstance(tipocodigo,str) and isinstance(tipoarea,str) and tipocodigo!="000":
        for ichip in chip:
            codigo_json    = {"chip": ichip,"tipocodigo": "subuso","codigo": tipocodigo,"tipo": tipoarea}
            codigo_encoded = urllib.parse.quote(str(codigo_json).replace("'", '"'))
            url            = f'https://sinupot.sdp.gov.co/serverp/rest/services/Reportes/GeneracionReportes/GPServer/GeneracionReportes/execute?f=json&tipo=RSPU&codigo={codigo_encoded}&generar=true'
            urlist.append({'tipo':'usosueloPOT555','url':url,'pdf':None})
    # POT 190
    if pot_190:
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

        output_pdf = 'combined.pdf'
        merger     = PdfMerger()
        
        for idx, url in enumerate(pdf_urls):
            try:
                response = requests.get(url,verify=False)
                response.raise_for_status()
                temp_pdf = f'temp_{idx}.pdf'
                with open(temp_pdf, 'wb') as file:
                    file.write(response.content)
                try:
                    reader = PdfReader(temp_pdf)
                    merger.append(reader)
                except: pass
                finally: os.remove(temp_pdf)
            except: pass
        with open(output_pdf, 'wb') as final_pdf:
            merger.write(final_pdf)
            
        merger.close()
        with open(output_pdf, "rb") as pdf_file:
            PDFbyte = pdf_file.read()
            
    return PDFbyte


@st.cache_data(show_spinner=False)
def getpdfsinupot1(urlist):
    PDFbyte = None
    #-----------------------------------------------------------------------------#
    # Requests paralelo y asyncronico
    if isinstance(urlist,list) and urlist!=[]:
        pool       = Pool(5)
        futures    = []
        pdf_urls = []
        for x in urlist:
            futures.append(pool.apply_async(requests.get, [x['url']],dict(verify=False)))
        for future in futures:
            r = future.get().json()
            try:    urlappend = r['results'][0]['value']['url'] if r.get('results') else None
            except: urlappend = None
            pdf_urls.append(urlappend)
        
        #-----------------------------------------------------------------------------#
        # Consolidar todos los pdf en uno solo
        output_pdf = 'combined.pdf'
        merger     = PdfMerger()
        
        for idx, url in enumerate(pdf_urls):
            try:
                response = requests.get(url,verify=False)
                response.raise_for_status()
                temp_pdf = f'temp_{idx}.pdf'
                with open(temp_pdf, 'wb') as file:
                    file.write(response.content)
                try:
                    reader = PdfReader(temp_pdf)
                    merger.append(reader)
                except: pass
                finally: os.remove(temp_pdf)
            except: pass
        with open(output_pdf, 'wb') as final_pdf:
            merger.write(final_pdf)
            
        merger.close()
        with open(output_pdf, "rb") as pdf_file:
            PDFbyte = pdf_file.read()
            
    return PDFbyte

def extract_year(titulo):
    match = re.search(r'\b(19|20)\d{2}\b', titulo)
    return int(match.group()) if match else None
