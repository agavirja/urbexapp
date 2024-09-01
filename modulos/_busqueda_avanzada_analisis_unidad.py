import re
import streamlit as st
import pandas as pd
import hashlib
import plotly.express as px
import plotly.graph_objects as go
from bs4 import BeautifulSoup
from streamlit_js_eval import streamlit_js_eval
from datetime import datetime
from plotly.subplots import make_subplots

from data.getdatabuilding import main as getdatabuilding, chip2codigolote_sinupot
from data.getreporte_sinupot import main as getreportesinupot

def main(chip=None,barmanpre=None,vartype=None):
    
    #-------------------------------------------------------------------------#
    # Tamano de la pantalla 
    screensize = 1920
    mapwidth   = int(screensize)
    mapheight  = int(screensize)
    try:
        screensize = streamlit_js_eval(js_expressions='screen.width', key = 'SCR')
        mapwidth   = int(screensize)
        mapheight  = int(screensize)
    except: pass
    
    col1,col2,col3      = st.columns([0.05,0.4,0.55],gap="small")
    chip_referencia = chip

    if isinstance(barmanpre, str):
        with st.spinner('Buscando información'):
            datacatastro,datausosuelo,datalote,datavigencia,datatransacciones,datactl = getdatabuilding(barmanpre)
            
        if not datacatastro.empty:
            datacatastro = datacatastro.sort_values(by=['predirecc','prechip'],ascending=True)

        if not datavigencia.empty:
            datavigencia          = datavigencia.sort_values(by='vigencia',ascending=False)
            datavigencia['link']  = datavigencia.apply(lambda x: linkPredial(x['chip'],x['vigencia'],x['idSoporteTributario']),axis=1)
            datavigencia['name']  = datavigencia.apply(lambda x: buildname(x['primerNombre'],x['segundoNombre'],x['primerApellido'],x['segundoApellido']),axis=1)
            varphones             = [x for x in ['telefono1','telefono2','telefono3','telefono4','telefono5'] if x in datavigencia]
            datavigencia['phone'] = datavigencia[varphones].apply(buildphone, axis=1)
            varemails             = [x for x in ['email1','email2'] if x in datavigencia]
            datavigencia['email'] = datavigencia[varemails].apply(buildemail, axis=1)
            
        chip = None
        if not datacatastro.empty:
            if len(datacatastro)>1:
                lista     = datacatastro['predirecc'].tolist()
                listachip = datacatastro['prechip'].tolist()
                index     = 0
                if isinstance(chip_referencia, str):
                    index = listachip.index(chip_referencia)
                
                with col2:
                    predirecc = st.selectbox('Lista de direcciones: ',options=lista,index=index)
                    chip      = datacatastro[datacatastro['predirecc']==predirecc]['prechip'].iloc[0]
            else: chip = datacatastro['prechip'].iloc[0]
            
        datacatastro_predio      = pd.DataFrame()
        datavigencia_predio      = pd.DataFrame()
        datatransacciones_predio = pd.DataFrame()
        datausosuelo_predio      = pd.DataFrame()
        datactl_predio           = pd.DataFrame()

        if isinstance(chip, str):
            if not datacatastro.empty:
                datacatastro_predio = datacatastro[datacatastro['prechip']==chip]
            if not datavigencia.empty:
                datavigencia_predio = datavigencia[datavigencia['chip']==chip]
            if not datatransacciones.empty:
                datatransacciones_predio = datatransacciones[datatransacciones['prechip']==chip]
            if not datacatastro_predio.empty and not datausosuelo.empty:
                datausosuelo_predio = datausosuelo[datausosuelo['precuso']==datacatastro_predio['precuso'].iloc[0]]
            if not datactl.empty:
                datactl_predio = datactl[datactl['prechip']==chip]
            
        html,elementos = principal_table(datacatastro=datacatastro_predio,datausosuelo=datausosuelo_predio,datavigencia=datavigencia_predio,mapwidth=mapwidth,mapheight=mapheight)
        st.components.v1.html(html,height=int(elementos*600/30),scrolling=True)
        colg1,colg2 = st.columns([0.001,0.999])

        #-------------------------------------------------------------------------#
        # Tabla Transacciones
        #-------------------------------------------------------------------------#
        if not datatransacciones_predio.empty:       
            
            datatransacciones_predio = gruoptransactions(datatransacciones_predio)
            datapaso          = datatransacciones_predio.copy()

            st.write('')
            titulo = 'Transacciones'
            html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
            texto  = BeautifulSoup(html, 'html.parser')
            st.markdown(texto, unsafe_allow_html=True)
            
            for inputval in ['cuantia']:
                iddnull = datatransacciones_predio[inputval].isnull()
                if sum(iddnull)>0:
                    datatransacciones_predio.loc[iddnull,inputval] = ''
                    
            if   len(datapaso)>=10: tableH = 450
            elif len(datapaso)>=5:  tableH = int(len(datapaso)*45)
            elif len(datapaso)>1:   tableH = int(len(datapaso)*60)
            elif len(datapaso)==1:  tableH = 100
            else: tableH = 100
            
            ngroup = len(list(datapaso['group'].unique())) if 'group' in datapaso else 1
            html_paso = ""
            for _,items in datapaso.iterrows():
                
                group = "<td></td>"
                if ngroup>1:
                    try:    group = f"<td>{items['group']}</td>"
                    except: group = "<td></td>"
                try:    cuantia = f"${items['cuantia']:,.0f}" if 'cuantia' in items and isinstance(items['cuantia'],(int,float)) else ''
                except: cuantia = ''
                try:    areaconstruida = f"{round(items['preaconst'],2)}"
                except: areaconstruida = ''     
                try:    areaterreno = f"{round(items['preaterre'],2)}"
                except: areaterreno = ''  
                html_paso += f"""
                <tr>
                    {group}
                    <td class="align-middle text-center text-sm" style="border: none;padding: 8px;">
                       <a href="{items['link']}" target="_blank">
                       <img src="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/publicimg/pdf.png" alt="link" width="20" height="20">
                       </a>                    
                    </td>
                    <td>{items['fecha_documento_publico']}</td>    
                    <td>{items['predirecc']}</td>
                    <td>{items['codigo']}</td>
                    <td>{items['nombre']}</td>
                    <td>{items['tarifa']}</td>
                    <td>{cuantia}</td>
                    <td>{areaconstruida}</td>
                    <td>{areaterreno}</td>
                    <td>{items['tipo_documento_publico']}</td>
                    <td>{items['numero_documento_publico']}</td>
                    <td>{items['entidad']}</td>                
                </tr>
                """
            html_paso = f"""
            <thead>
                <tr>
                    <th>Grupo</th>
                    <th>Link</th>
                    <th>Fecha</th>
                    <th>Dirección</th>
                    <th>Código</th>
                    <th>Tipo</th>
                    <th>Tarifa</th>
                    <th>Valor</th>
                    <th>Área construida</th>
                    <th>Área de terreno</th>
                    <th>Tipo documento</th>
                    <th>Número de documento</th>
                    <th>Notaria</th>                
                </tr>
            </thead>
            <tbody>
            {html_paso}
            </tbody>
            """
            style = tablestyle()
            html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            {style}
            </head>
            <body>
                <div class="table-wrapper table-background">
                    <div class="table-scroll">
                        <table class="fl-table">
                        {html_paso}
                        </table>
                    </div>
                </div>
            </body>
            </html>
            """
            st.components.v1.html(html,height=tableH)   
            
        #-------------------------------------------------------------------------#
        # Tabla CTL
        #-------------------------------------------------------------------------#
        if not datactl_predio.empty:    
            
            datapaso = datactl_predio.copy()

            st.write('')
            titulo = 'Certificados de libertad y tradición'
            html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
            texto  = BeautifulSoup(html, 'html.parser')
            st.markdown(texto, unsafe_allow_html=True)
                 
            if   len(datapaso)>=10: tableH = 450
            elif len(datapaso)>=5:  tableH = int(len(datapaso)*45)
            elif len(datapaso)>1:   tableH = int(len(datapaso)*60)
            elif len(datapaso)==1:  tableH = 100
            else: tableH = 100
            
            html_paso = ""
            for _,items in datapaso.iterrows():
                try:    areaconstruida = f"{round(items['preaconst'],2)}"
                except: areaconstruida = ''     
                try:    areaterreno = f"{round(items['preaterre'],2)}"
                except: areaterreno = ''  

                html_paso += f"""
                <tr> 
                    <td class="align-middle text-center text-sm" style="border: none;padding: 8px;">
                       <a href="{items['url']}" target="_blank">
                       <img src="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/publicimg/pdf.png" alt="link" width="20" height="20">
                       </a>                    
                    </td>
                    <td>{items['last_fecha']}</td>
                    <td>{items['predirecc']}</td>
                    <td>{items['matriculainmobiliaria']}</td>
                    <td>{areaconstruida}</td>
                    <td>{areaterreno}</td>
                    <td>{items['usosuelo']}</td>            
                </tr>
                """
            html_paso = f"""
            <thead>
                <tr>
                    <th>Link</th>
                    <th>Fecha</th>
                    <th>Dirección</th>
                    <th>Matrícula</th>
                    <th>Área construida</th>
                    <th>Área de terreno</th>
                    <th>Uso del suelo</th>             
                </tr>
            </thead>
            <tbody>
            {html_paso}
            </tbody>
            """
            style = tablestyle()
            html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            {style}
            </head>
            <body>
                <div class="table-wrapper table-background">
                    <div class="table-scroll">
                        <table class="fl-table">
                        {html_paso}
                        </table>
                    </div>
                </div>
            </body>
            </html>
            """
            st.components.v1.html(html,height=tableH) 

        #-------------------------------------------------------------------------#
        # Tabla historial catastral
        #-------------------------------------------------------------------------#
        if not datavigencia_predio.empty:
    
            variables = [x for x in ['link','vigencia','valorAutoavaluo','valorImpuesto','copropiedad','tipoPropietario','tipoDocumento','name','phone','email'] if x in datavigencia_predio]
            datapaso  = datavigencia_predio[variables]
           
            st.write('')
            titulo = 'Historial Catastral'
            html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
            texto  = BeautifulSoup(html, 'html.parser')
            st.markdown(texto, unsafe_allow_html=True)
            
            for inputval in ['valorAutoavaluo','valorImpuesto']:
                iddnull = datavigencia_predio[inputval].isnull()
                if sum(iddnull)>0:
                    datavigencia_predio.loc[iddnull,inputval] = ''
                    
            if   len(datapaso)>=10: tableH = 450
            elif len(datapaso)>=5:  tableH = int(len(datapaso)*45)
            elif len(datapaso)>1:   tableH = int(len(datapaso)*60)
            elif len(datapaso)==1:  tableH = 100
            else: tableH = 100
            
            html_paso    = ""
            for _,items in datapaso.iterrows():
                try:    
                    link = items['link'] if 'link' in items and isinstance(items['link'], str) else ""
                    link = f"""
                    <td class="align-middle text-center text-sm" style="border: none;padding: 8px;">
                       <a href="{link}" target="_blank">
                       <img src="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/publicimg/pdf.png" alt="link" width="20" height="20">
                       </a>                    
                    </td>
                    """
                except: link = "<td></td>"
                try:    vigencia = f"<td>{items['vigencia']}</td>" if 'vigencia' in items and (isinstance(items['vigencia'], int) or isinstance(items['vigencia'], float)) else "<td></td>"
                except: vigencia = "<td></td>"
                try:    avaluo = f"<td>${items['valorAutoavaluo']:,.0f}</td>" if 'valorAutoavaluo' in items and isinstance(items['valorAutoavaluo'], (int,float)) else "<td></td>"
                except: avaluo = "<td></td>"
                try:    predial = f"<td>${items['valorImpuesto']:,.0f}</td>" if 'valorImpuesto' in items and (isinstance(items['valorImpuesto'], int) or isinstance(items['valorImpuesto'], float)) else "<td></td>"
                except: predial = "<td></td>"
                try:    copropiedad = f"<td>{int(items['copropiedad'])}</td>" if 'copropiedad' in items and (isinstance(items['copropiedad'], int) or isinstance(items['copropiedad'], float)) else "<td></td>"
                except: copropiedad = "<td></td>"
                try:    tipopropietario = f"<td>{items['tipoPropietario']}</td>" if 'tipoPropietario' in items and isinstance(items['tipoPropietario'], str) else "<td></td>"
                except: tipopropietario = "<td></td>"
                try:    tipodocumento = f"<td>{items['tipoDocumento']}</td>" if 'tipoDocumento' in items and isinstance(items['tipoDocumento'], str) else "<td></td>"
                except: tipodocumento = "<td></td>"
                try:    name = f"<td>{items['name']}</td>" if 'name' in items and isinstance(items['name'], str) else "<td></td>"
                except: name = "<td></td>"
                try:    phone = f"<td>{items['phone']}</td>" if 'phone' in items and isinstance(items['phone'], str) else "<td></td>"
                except: phone = "<td></td>"
                try:    email = f"<td>{items['email']}</td>" if 'email' in items and isinstance(items['email'], str) else "<td></td>"
                except: email = "<td></td>"
                
                html_paso += f"""
                <tr>
                    {link}
                    {vigencia}
                    {avaluo}
                    {predial}
                    {copropiedad}
                    {tipopropietario}
                    {tipodocumento}
                    {name}
                    {phone}
                    {email}
                </tr>
                """
            html_paso = f"""
            <thead>
                <tr>
                    <th>Link</th>
                    <th>Vigencia</th>
                    <th>Avalúo catastral</th>
                    <th>Predial</th>
                    <th>Co-propiedad</th>
                    <th>Tipo de propietario</th>
                    <th>Tipo de documento</th>
                    <th>Propietario</th>
                    <th>Contacto</th>
                    <th>Email</th>
                </tr>
            </thead>
            <tbody>
            {html_paso}
            </tbody>
            """
            style = tablestyle()
            html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            {style}
            </head>
            <body>
                <div class="table-wrapper table-background">
                    <div class="table-scroll">
                        <table class="fl-table">
                        {html_paso}
                        </table>
                    </div>
                </div>
            </body>
            </html>
            """
            st.components.v1.html(html,height=tableH)       
        
        
        #-------------------------------------------------------------------------#
        # SINUPOT
        #-------------------------------------------------------------------------#
        if isinstance(chip,str) and chip!='':
            getreportesinupot(chip=chip,reporte_chip=True,licencias=True,plusvalia=True,estratificacion=True,telecomunicacion=True,pot_190=True)
    
                    
        #-------------------------------------------------------------------------#
        # Graficas
        #-------------------------------------------------------------------------#
        if not datatransacciones_predio.empty or not datavigencia_predio.empty:
            with colg2:
                st.write('')
                titulo = 'Estadísticas'
                html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
                texto  = BeautifulSoup(html, 'html.parser')
                st.markdown(texto, unsafe_allow_html=True)
    
                html,numgraph = graficasHtml(datatransacciones=datatransacciones_predio,datavigencia=datavigencia_predio,mapwidth=mapwidth,mapheight=400)
                st.components.v1.html(html, height=numgraph*420)


@st.cache_data(show_spinner=False)
def principal_table(datacatastro=pd.DataFrame(),datausosuelo=pd.DataFrame(),datavigencia=pd.DataFrame(),mapwidth=1280,mapheight=200):
    
    tabladescripcion = ""
    html_paso        = ""
    chip             = None
    elementos        = 0
    if not datacatastro.empty and len(datacatastro)==1:
        try:    chip = datacatastro['prechip'].iloc[0]
        except: chip = None
        try:    matricula = datacatastro['matriculainmobiliaria'].iloc[0]
        except: matricula = None
        try:    cedulacatastral = datacatastro['precedcata'].iloc[0]
        except: cedulacatastral = None
        try:    areaconstruida = f"{round(datacatastro['preaconst'].iloc[0],2)} m²"
        except: areaconstruida = None  
        try:    areaterreno = f"{round(datacatastro['preaterre'].iloc[0],2)} m²"
        except: areaterreno = None          
        try:    usosuelo = datacatastro['usosuelo'].iloc[0]
        except: usosuelo = None

        formato   = {'Chip:':chip,'Matrícula Inmobiliaria:':matricula,'Cédula catastral':cedulacatastral,'Área construida':areaconstruida,'Área de terreno':areaterreno,'Uso':usosuelo}
        for key,value in formato.items():
            if value is not None:
                html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
                elementos += 1
        if html_paso!="":
            labeltable     = "Información del predio"
            tabladescripcion = f"""
            <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            {html_paso}
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            """
            tabladescripcion = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tabladescripcion}</tbody></table></div></div>"""
        
        
    tablabuilding = ""
    html_paso     = ""
    if not datausosuelo.empty:
        try:    predios = datausosuelo['predios_precuso'].iloc[0]
        except: predios = None
        try:    estrato = int(datausosuelo['estrato'].iloc[0])
        except: estrato = None
        try:    pisos = int(datausosuelo['connpisos'].iloc[0])
        except: pisos = None
        try:    antiguedad = int(datausosuelo['prevetustzmin'].iloc[0])
        except: antiguedad = None  

        if not datacatastro.empty and 'prevetustz' in datacatastro:
            try:    antiguedad = int(datacatastro['prevetustz'].iloc[0])
            except: antiguedad = None  

        formato   = {'Predios (mismo uso):':predios,'Estrato':estrato,'Pisos':pisos,'Antiguedad':antiguedad}
        for key,value in formato.items():
            if value is not None:
                html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
                elementos += 1
        if html_paso!="":
            labeltable     = "Información General"
            tablabuilding = f"""
            <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            {html_paso}
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            """
            tablabuilding = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablabuilding}</tbody></table></div></div>"""
        
    tablacatastro     = ""
    tablapropietarios = ""
    if not datavigencia.empty:

        datapaso = datavigencia.sort_values(by='vigencia',ascending=False)
        datapaso = datapaso[datapaso['vigencia']==datapaso['vigencia'].max()]
        if not datapaso.empty:
            try:    vigencia = int(datapaso['vigencia'].iloc[0])
            except: vigencia = None
            try:    avaluo = f"${datapaso['valorAutoavaluo'].iloc[0]:,.0f}"
            except: avaluo = None
            try:    predial = f"${datapaso['valorImpuesto'].iloc[0]:,.0f}"
            except: predial = None
            try:
                year = ''
                if vigencia is not None: year = vigencia
                link = f"""<a href="{datapaso['link'].iloc[0]}" target="_blank">Predial {year}</a>"""
            except: link = None
            
        # Datos catastrales
        html_paso = ""
        formato   = {'Vigencia:':vigencia,'Avalúo Catastral':avaluo,'Predial':predial,'link':link}
        for key,value in formato.items():
            if value is not None:
                html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
                elementos += 1
        if html_paso!="":
            labeltable     = "Información Catastral"
            tablacatastro = f"""
            <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            {html_paso}
            <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
            """
            tablacatastro = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablacatastro}</tbody></table></div></div>"""
        
        # Propietarios
        datapaso = datavigencia.sort_values(by='vigencia',ascending=False)
        datapaso = datapaso[datapaso['tipoDocumento'].notnull()]
        if not datapaso.empty:
            datapaso               = datapaso[datapaso['vigencia']==datapaso['vigencia'].max()]
            datapaso.idnex         = range(len(datapaso))
            html_propietarios_paso = ""
            k                      = len(datapaso)
            conteo                 = 0
            for j in range(len(datapaso)):
                html_paso = ""
                try:    tipopropietario = datapaso['tipoPropietario'].iloc[j]
                except: tipopropietario = None
                try:    tipoid = datapaso['tipoDocumento'].iloc[j]
                except: tipoid = None          
                try:    identificacion = datapaso['nroIdentificacion'].iloc[j]
                except: identificacion = None   
                try:    nombre = datapaso['name'].iloc[j]
                except: nombre = None
                try:    phones = datapaso['phone'].iloc[j]
                except: phones = None
                try:    email = datapaso['email'].iloc[j]
                except: email = None
                
                formato   = {'Tipo de propietario:':tipopropietario,'Tipo Id:':tipoid,'Identificación:':identificacion,'Propietario:':nombre,'Contacto:':phones,'Email:':email}
                for key,value in formato.items():
                    if value is not None:
                        html_paso += f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #908F8F;">{key}</h6></td><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #515151;">{value}</h6></td></tr>"""
                        elementos += 1
                if html_paso!="":
                    conteo += 1
                    titulo  = ""
                    spacio  = ""
                    if k>1:
                        titulo = f"""<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;">Propietario {conteo}:</h6></td>"""
                        spacio = """<tr><td style="border: none;"><h6 class="mb-0 text-sm" style="color: #000;"></h6></td>"""
                    html_propietarios_paso += f"""
                    {spacio}
                    <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
                    {titulo}
                    {html_paso}
                    <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
                    """
            if html_propietarios_paso!="":
                labeltable        = "Tabla Propietarios"
                tablapropietarios = f"""
                <tr><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;">{labeltable}</h6></td><td style="border-bottom: 2px solid #A16CFF;"><h6 class="mb-0 text-sm" style="font-family: 'Inter';color: #A16CFF;"> </h6></td></tr>
                <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
                {html_propietarios_paso}
                <tr><td style="border: none;"><h6></h6></td><td style="border: none;"><h6></h6></td></tr>
                """
                tablapropietarios = f"""<div class="col-md-6"><div class="css-table"><table class="table align-items-center mb-0"><tbody>{tablapropietarios}</tbody></table></div></div>"""
            
    style = """
    <style>
        .css-table {
            overflow-x: auto;
            overflow-y: auto;
            width: 100%;
            height: 100%;
        }
        .css-table table {
            width: 100%;
            padding: 0;
            table-layout: fixed; 
            border-collapse: collapse;
        }
        .css-table td {
            text-align: left;
            padding: 0;
            overflow: hidden; 
            text-overflow: ellipsis; 
        }
        .css-table h6 {
            line-height: 1; 
            font-size: 50px;
            padding: 0;
        }
        .css-table td[colspan="labelsection"] {
          text-align: left;
          font-size: 15px;
          color: #A16CFF;
          font-weight: bold;
          border: none;
          border-bottom: 2px solid #A16CFF;
          margin-top: 20px;
          display: block;
          font-family: 'Inter';
          width: 100%
        }
        .css-table td[colspan="labelsectionborder"] {
          text-align: left;
          border: none;
          border-bottom: 2px solid blue;
          margin-top: 20px;
          display: block;
          padding: 0;
          width: 100%;
        }
        
        #top {
            position: absolute;
            top: 0;
        }
        
        #top:target::before {
            content: '';
            display: block;
            height: 100px; 
            margin-top: -100px; 
        }
    </style>
    """
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
      <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/nucleo-icons.css" rel="stylesheet">
      <link href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/nucleo-svg.css" rel="stylesheet">
      <link id="pagestyle" href="https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/css/soft-ui-dashboard.css?v=1.0.7" rel="stylesheet">
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      {style}
    </head>
    <body>
      <div class="container-fluid py-4" style="margin-bottom: 0px;margin-top: 0px;">
        <div class="row">
          <div class="col-md-12 mb-md-0 mb-2">
            <div class="card h-100">
              <div class="card-body p-3">
                <div class="container-fluid py-4">
                  <div class="row" style="margin-bottom: 0px;margin-top: 0px;">
                    {tabladescripcion}
                    {tablabuilding}
                    {tablacatastro}
                    {tablapropietarios}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </body>
    </html>
    """
    return html,elementos

@st.cache_data(show_spinner=False)
def graficasHtml(datatransacciones=pd.DataFrame(),datavigencia=pd.DataFrame(),mapwidth=600,mapheight=500):
  
    numgraph = 0
    #-------------------------------------------------------------------------#
    # Transacciones
    html_barras  = ""
    html_grafica = ""
    datapaso     = pd.DataFrame()
    df           = pd.DataFrame()
    if not datatransacciones.empty:
        df = datatransacciones.copy()
        if not df.empty and 'codigo' in df:
            df = df[df['codigo'].isin(['125','126','168','169','0125','0126','0168','0169'])]
            
        if not df.empty:
            df['year'] = pd.to_datetime(df['fecha_documento_publico'])
            df['year'] = df['year'].dt.year
            df         = df[df['year']>=(datetime.now().year-6)]
            df         = df.groupby('year').agg({'cuantia':['count','max']}).reset_index()
            df.columns = ['fecha','count','value']
            df.index   = range(len(df))
            datapaso   = df.copy()
    
    if not datavigencia.empty:
        df         = datavigencia.copy()
        df         = df.groupby(['chip','vigencia']).agg({'valorAutoavaluo':'max','valorImpuesto':'max'}).reset_index()
        df.columns = ['chip','vigencia','valorAutoavaluo','valorImpuesto']
        df         = df.groupby('vigencia').agg({'valorAutoavaluo':'max','valorImpuesto':'max'}).reset_index()
        df.columns = ['fecha','valorAutoavaluo','valorImpuesto']
        df         = df[df['fecha']>=(datetime.now().year-6)]
        if not datapaso.empty and not df.empty:
            datapaso = datapaso.merge(df,on='fecha',how='outer',validate='1:1')
        elif datapaso.empty and not df.empty:
            datapaso = df.copy()
            
    if not datapaso.empty:
        fig         = make_subplots(specs=[[{"secondary_y": True}]])
        offsetgrpah = -1
        widthbar    = 0.4
        if 'value' in datapaso: widthbar = 0.3
        if 'valorImpuesto' in datapaso:
            offsetgrpah += 1
            fig.add_trace(go.Bar(x=datapaso['fecha'],y=datapaso['valorImpuesto'],name='Impuesto predial' ,marker_color='#7189FF',offsetgroup=offsetgrpah,width=widthbar,showlegend=True,text=datapaso['valorImpuesto'],texttemplate='$%{text:,.0f}',textposition='inside',textangle=90,textfont=dict(color='white', size=12)),secondary_y=False)
        if 'valorAutoavaluo' in datapaso:
            offsetgrpah += 1
            fig.add_trace(go.Bar(x=datapaso['fecha'],y=datapaso['valorAutoavaluo'],name='Avalúo catastral',marker_color='#624CAB',offsetgroup=offsetgrpah,width=widthbar,showlegend=True,text=datapaso['valorAutoavaluo'],texttemplate='$%{text:,.0f}',textposition='inside',textangle=90,textfont=dict(color='white', size=12)),secondary_y=True)
        if 'value' in datapaso:
            offsetgrpah += 1
            fig.add_trace(go.Bar(x=datapaso['fecha'],y=datapaso['value'],name='Valor transacciones',marker_color='#FF6B6B',offsetgroup=offsetgrpah,width=widthbar,showlegend=True,text=datapaso['value'],texttemplate='$%{text:,.0f}',textposition='inside',textangle=90,textfont=dict(color='white', size=12)),secondary_y=True)

        fig.update_layout(
            xaxis_title=None,
            yaxis_title=None,
            yaxis2_title=None,
            barmode='group',
            height=int(mapheight), 
            width=int(mapwidth*0.9),
            plot_bgcolor='rgba(0, 0, 0, 0)',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            margin=dict(l=0, r=0, t=0, b=100),
            legend=dict(orientation='h', yanchor='top',y=-0.2,xanchor='center',x=0.5,bgcolor='white',font=dict(color='black')),
            title_font=dict(size=11,color='black'),
        )
        fig.update_xaxes(tickmode='linear', dtick=1, tickfont=dict(color='black'),showgrid=False, zeroline=False,)
        fig.update_yaxes(showgrid=False, zeroline=False, tickfont=dict(color='black'), title_font=dict(color='black'))
        fig.update_yaxes(title=None, secondary_y=True, showgrid=False, zeroline=False, tickfont=dict(color='black'))
        html_fig_paso = fig.to_html(config={'displayModeBar': False})
        try:
            soup = BeautifulSoup(html_fig_paso, 'html.parser')
            soup = soup.find('body')
            soup = str(soup.prettify())
            soup = soup.replace('<body>', '<div style="margin-bottom: 0px;">').replace('</body>', '</div>')
            html_grafica = f""" 
            <div class="col-12">
                <div class="card card-stats card-round card-custom">
                    <div class="card-body card-body-custom">
                        <div class="row align-items-center">
                            <div class="col col-stats ms-3 ms-sm-0">
                                <div class="graph-container" style="width: 100%; height: auto;">
                                    {soup}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """
        except: pass

    if isinstance(html_grafica,str) and html_grafica!="":
        numgraph += 1
        html_barras = f"""
        <div class="row mb-20">
            {html_grafica}
        </div>
        """
        
    style = """
    <style>
        body, html {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        .card {
            --bs-card-spacer-y: 1rem;
            --bs-card-spacer-x: 1rem;
            --bs-card-title-spacer-y: 0.5rem;
            --bs-card-title-color: #000;
            --bs-card-subtitle-color: #6c757d;
            --bs-card-border-width: 1px;
            --bs-card-border-color: rgba(0, 0, 0, 0.125);
            --bs-card-border-radius: 0.25rem;
            --bs-card-box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
            --bs-card-inner-border-radius: calc(0.25rem - 1px);
            --bs-card-cap-padding-y: 0.5rem;
            --bs-card-cap-padding-x: 1rem;
            --bs-card-cap-bg: rgba(0, 123, 255, 0.03);
            --bs-card-cap-color: #007bff;
            --bs-card-height: auto;
            --bs-card-color: #000;
            --bs-card-bg: #fff;
            --bs-card-img-overlay-padding: 1rem;
            --bs-card-group-margin: 0.75rem;
            position: relative;
            display: flex;
            flex-direction: column;
            min-width: 0;
            height: var(--bs-card-height);
            color: var(--bs-card-color);
            word-wrap: break-word;
            background-color: var(--bs-card-bg);
            background-clip: border-box;
            border: var(--bs-card-border-width) solid var(--bs-card-border-color);
            border-radius: var(--bs-card-border-radius);
            box-shadow: var(--bs-card-box-shadow);
        }

        .card-stats .icon-big {
            font-size: 3rem;
            line-height: 1;
            color: #fff;
        }

        .card-stats .icon-primary {
            background-color: #007bff;
        }

        .bubble-shadow-small {
            box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
            border-radius: 50%;
            padding: 1rem;
        }

        .card-stats .numbers {
            font-size: 2rem;
            font-weight: bold;
            text-align: center;
        }

        .card-stats .card-category {
            color: #6c757d;
            font-size: 0.8rem;
            margin: 0;
            text-align: center;
        }

        .card-stats .card-title {
            margin: 0;
            font-size: 1.2rem;
            font-weight: bold;
            text-align: center;
        }
        
        .small-text {
            font-size: 0.3rem; 
            color: #6c757d; 
        }
        .graph-container {
            width: 100%;
            height: 100%;
            margin-bottom: 0;
        }
        
        .card-custom {
            height: 400px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
        }

        .card-body-custom {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            text-align: center;
        }
        
        .mb-20 {
            margin-bottom: 10px;
        }
    </style>
    """
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Visitors Card</title>
        <!-- Incluyendo Bootstrap CSS para el diseño de las tarjetas -->
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/5.0.0-alpha1/css/bootstrap.min.css">
        <!-- Font Awesome para los íconos -->
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
        {style}
    </head>
    <body>
        <div class="container-fluid">
            {html_barras}
        </div>
    </body>
    </html>
    """
    return html,numgraph

def generar_codigo(x):
    hash_sha256 = hashlib.sha256(x.encode()).hexdigest()
    codigo      = hash_sha256[:12]
    return codigo

def linkPredial(chip,vigencia,idsoporte):
    result = None
    if isinstance(vigencia, (int,float)):
        if isinstance(idsoporte,str) and idsoporte!='':
            result = f"https://oficinavirtual.shd.gov.co/barcode/certificacion?idSoporte={idsoporte}"
        else:
            filename = generar_codigo(f'{vigencia}{chip}{vigencia}')
            filename = f'{filename.upper()}.pdf'
            result   = f'https://prediales.nyc3.digitaloceanspaces.com/{filename}'
    return result

def buildname(nombre1,nombre2,apellido1,apellido2):
    result = ''
    if isinstance(nombre1, str) and nombre1!='':
        result = f"{result} {nombre1}"
    if isinstance(nombre2, str) and nombre2!='':
        result = f"{result} {nombre2}"
    if isinstance(apellido1, str) and apellido1!='':
        result = f"{result} {apellido1}"
    if isinstance(apellido2, str) and apellido2!='':
        result = f"{result} {apellido2}"
    if result!='':
        result = re.sub('\s+',' ',result)
        result = result.strip()
        result = result.title()
    return result

def buildphone(row):
    result = None
    vector = []
    for x in row:
        try: x = str(int(x))
        except: pass
        if isinstance(x, str) and len(x)>=7:
            vector.append(x)
    if vector!=[]:
        vector = list(set(vector))
        result = ' | '.join(vector)
    return result

def buildemail(row):
    result = None
    vector = []
    for x in row:
        try: x = str(int(x))
        except: pass
        if isinstance(x, str) and len(x)>=7:
            vector.append(x)
    if vector!=[]:
        vector = [x.lower().strip() for x in vector]
        vector = list(set(vector))
        result = ' | '.join(vector)
    return result

@st.cache_data(show_spinner=False)
def gruoptransactions(datatransacciones):
    if not datatransacciones.empty and 'docid' in datatransacciones:
        datamerge = datatransacciones.drop_duplicates(subset='docid',keep='first')
        datamerge = datamerge.sort_values(by='docid',ascending=False)
        datamerge['group'] = range(len(datamerge))
        datamerge['group'] = datamerge['group']+1
        datatransacciones = datatransacciones.merge(datamerge[['docid','group']],on='docid',how='left',validate='m:1')
        datatransacciones = datatransacciones.sort_values(by=['docid','preaconst','cuantia'],ascending=[False,False,False])
    return datatransacciones

@st.cache_data(show_spinner=False)
def tablestyle():
    return """
        <style>
            * {
                box-sizing: border-box;
                -webkit-box-sizing: border-box;
                -moz-box-sizing: border-box;
            }
        
            body {
                font-family: Helvetica;
                -webkit-font-smoothing: antialiased;
            }
        
            .table-background {
                background: rgba(71, 147, 227, 1);
            }
        
            h2 {
                text-align: center;
                font-size: 18px;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: white;
                padding: 30px 0;
            }
        
            /* Table Styles */
        
            .table-wrapper {
                margin: 10px 70px 70px;
                box-shadow: 0px 35px 50px rgba(0, 0, 0, 0.2);
            }
        
            .fl-table {
                border-radius: 5px;
                font-size: 12px;
                font-weight: normal;
                border: none;
                border-collapse: collapse;
                width: 100%;
                max-width: 100%;
                white-space: nowrap;
                background-color: white;
            }
        
            .fl-table td,
            .fl-table th {
                text-align: center;
                padding: 8px;
            }
        
            .fl-table td {
                border-right: 1px solid #f8f8f8;
                font-size: 12px;
            }
        
            .fl-table thead th {
                color: #ffffff;
                background: #A16CFF; /* Manteniendo el color verde claro para el encabezado */
                position: sticky; /* Haciendo el encabezado fijo */
                top: 0; /* Fijando el encabezado en la parte superior */
            }
        
            .fl-table tr:nth-child(even) {
                background: #f8f8f8;
            }
            .table-scroll {
                overflow-x: auto;
                overflow-y: auto;
                max-height: 450px; /* Altura máxima ajustable según tus necesidades */
            }
        
            @media (max-width: 767px) {
                .fl-table {
                    display: block;
                    width: 100%;
                }
                .table-wrapper:before {
                    content: "Scroll horizontally >";
                    display: block;
                    text-align: right;
                    font-size: 11px;
                    color: white;
                    padding: 0 0 10px;
                }
                .fl-table thead,
                .fl-table tbody,
                .fl-table thead th {
                    display: block;
                }
                .fl-table thead th:last-child {
                    border-bottom: none;
                }
                .fl-table thead {
                    float: left;
                }
                .fl-table tbody {
                    width: auto;
                    position: relative;
                    overflow-x: auto;
                }
                .fl-table td,
                .fl-table th {
                    padding: 20px .625em .625em .625em;
                    height: 60px;
                    vertical-align: middle;
                    box-sizing: border-box;
                    overflow-x: hidden;
                    overflow-y: auto;
                    width: 120px;
                    font-size: 13px;
                    text-overflow: ellipsis;
                }
                .fl-table thead th {
                    text-align: left;
                    border-bottom: 1px solid #f7f7f9;
                }
                .fl-table tbody tr {
                    display: table-cell;
                }
                .fl-table tbody tr:nth-child(odd) {
                    background: none;
                }
                .fl-table tr:nth-child(even) {
                    background: transparent;
                }
                .fl-table tr td:nth-child(odd) {
                    background: #f8f8f8;
                    border-right: 1px solid #e6e4e4;
                }
                .fl-table tr td:nth-child(even) {
                    border-right: 1px solid #e6e4e4;
                }
                .fl-table tbody td {
                    display: block;
                    text-align: center;
                }
            }
        </style>
        """
