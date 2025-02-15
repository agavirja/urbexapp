import streamlit as st
import pandas as pd
import re
from datetime import datetime

from functions._principal_getunidades import main as getadataunidades
from functions._principal_getpdf import main as _principal_getpdf

from display._principal_detalle_unidad import main as generar_html

from data._sinupot_getpdf import main as getsinupot
from data.barmanpreFromgrupo import barmanpreFromgrupo
from data.tracking import savesearch
from data.getlastpredial import main as getlastpredial,check_predial

def main(grupo=None,chip_referencia=None,barmanpre=None):
    # grupo =  610954
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
        'data_prediales': pd.DataFrame(),
    }
    
    for key, value in formato.items():
        if key not in st.session_state:
            st.session_state[key] = value
            

    if grupo is not None:
        data_predios, data_usosuelopredios, data_prediales, data_anotaciones, datapropietarios  = getadataunidades(grupo=grupo)       
        
        data_predios         = pd.DataFrame(data_predios)
        data_prediales       = pd.DataFrame(data_prediales)
        data_usosuelopredios = pd.DataFrame(data_usosuelopredios)
        data_anotaciones     = pd.DataFrame(data_anotaciones)

        predirecc = None
        if not data_predios.empty:
            data_predios = data_predios.sort_values(by=['preaconst','predirecc'],ascending=[False,True])
            lista        = data_predios['predirecc'].tolist()
            listachip    = data_predios['prechip'].tolist()
            index        = 0
            if isinstance(chip_referencia, str):
                index = listachip.index(chip_referencia)
                        
            col00,col01,col02       = st.columns([1,10,1],vertical_alignment="center")
            col10,col11,col12,col13,col15 = st.columns([1,3.34,3.34,3.32 ,1],vertical_alignment="center")
            col20,col21,col22,col23 = st.columns([1,5,5,1],vertical_alignment="center")
            with col01:
                predirecc =  st.selectbox('Lista de direcciones: ',options=lista,index=index) 
        
        arealote = int(data_usosuelopredios['preaterre_precuso'].sum()) if not data_usosuelopredios.empty and 'preaterre_precuso' in data_usosuelopredios else 2500
        
        if predirecc is not None:
            if chip_referencia is None: 
                chip_referencia = data_predios[data_predios['predirecc']==predirecc]['prechip'].iloc[0]
            
            if isinstance(chip_referencia,str) and chip_referencia!='':
                data_predios     = data_predios[data_predios['prechip']==chip_referencia]      if not data_predios.empty and 'prechip' in data_predios else pd.DataFrame(columns=['barmanpre', 'predirecc', 'precuso', 'prechip', 'precedcata', 'preaconst', 'preaterre', 'matriculainmobiliaria', 'usosuelo'])
                data_prediales   = data_prediales[data_prediales['chip']==chip_referencia]     if not data_prediales.empty and 'chip' in data_prediales else pd.DataFrame(columns=['chip', 'direccion', 'matriculainmobiliaria', 'cedula_catastral', 'avaluo_catastral', 'tarifa', 'excencion', 'exclusion_parcial', 'impuesto_predial', 'descuento', 'impuesto_ajustado', 'url', 'year', 'tipo', 'identificacion', 'nombre', 'copropiedad', 'calidad', 'direccion_notificacion', 'impuesto_total', 'preaconst', 'preaterre', 'precuso', 'barmanpre', 'indPago', 'fechaPresentacion', 'nomBanco'])
                data_anotaciones = data_anotaciones[data_anotaciones['chip']==chip_referencia] if not data_anotaciones.empty and 'chip' in data_anotaciones else pd.DataFrame(columns=['docid', 'chip', 'codigo', 'cuantia', 'entidad', 'fecha_documento_publico', 'nombre', 'numero_documento_publico', 'oficina', 'preaconst', 'preaterre', 'precuso', 'predirecc', 'tipo_documento_publico', 'titular', 'email', 'tipo', 'nrodocumento', 'grupo', 'barmanpre'])
                data_usosuelopredios = data_usosuelopredios[data_usosuelopredios['precuso'].isin(data_predios['precuso'])] if not data_usosuelopredios.empty and 'precuso' in data_usosuelopredios else pd.DataFrame(columns=['formato_direccion', 'precuso', 'predios_precuso', 'preaconst_precuso', 'preaconst_precusomin', 'preaconst_precusomax', 'preaterre_precuso', 'preaterre_precusomin', 'preaterre_precusomax', 'barmanpre', 'usosuelo'])
                
        #---------------------------------------------------------------------#
        # Buscar nuevo predial
        
        notlastpredial = False
        if not data_prediales.empty:
            datapaso = data_prediales[data_prediales['year']>=datetime.now().year]
            idd      = datapaso['url'].isnull()
            if sum(idd)==len(datapaso):
                notlastpredial = True
            else: 
                urlref = datapaso[datapaso['url'].notnull()]['url'].iloc[0]
                if isinstance(urlref,str) and urlref!='': 
                    idd = (data_prediales['year']>=datetime.now().year) & (data_prediales['url'].isnull())
                    if sum(idd)>0:
                        data_prediales.loc[idd,'url'] = urlref
                
        c1 = col21
        c2 = col22
        if isinstance(chip_referencia,str) and chip_referencia!='' and notlastpredial:
            c1 = col11
            c2 = col12
            with col13:
                if st.button('Obtener el nuevo predial'):
                    datalastpredial = getlastpredial(chip=chip_referencia, data_prediales=data_prediales, data_anotaciones=data_anotaciones, year=2025)
                    if not datalastpredial.empty:
                        datalastpredial = mergedata(data=datalastpredial, data_predios=data_predios, chip_referencia=chip_referencia)
                        data_prediales  = pd.concat([datalastpredial,data_prediales])
                else:
                    datalastpredial = check_predial(chip=chip_referencia, year=2025, check_propietarios=True)
                    if not datalastpredial.empty:
                        datalastpredial = mergedata(data=datalastpredial, data_predios=data_predios, chip_referencia=chip_referencia)
                        data_prediales  = pd.concat([data_prediales,datalastpredial])
                        data_prediales  = data_prediales.sort_values(by=['chip','year','url'],ascending=False,na_position="last")
                        variables       = [x for x in ['chip','year','tipo','identificacion','nombre','tipoDocumento'] if x in data_prediales]
                        data_prediales  = data_prediales.drop_duplicates(subset=variables,keep='first')

        
        #---------------------------------------------------------------------#
        # Generar PDF
        PDFbyte  = False
        with c1:
            if st.button('Generar Reporte SINUPOT'):
                
                if barmanpre is None or pd.isna(barmanpre):
                    data2barmanpre = barmanpreFromgrupo(grupo=grupo)
                    barmanpre      = '|'.join(data2barmanpre['barmanpre'].unique()) if not data2barmanpre.empty and 'barmanpre' in data2barmanpre else None
                elif isinstance(barmanpre,list) and barmanpre!=[]:
                    try: barmanpre = '|'.join(barmanpre)
                    except: pass
                barmanpre = barmanpre if isinstance(barmanpre,str) and barmanpre!='' else None
                
                savesearch(st.session_state.token, barmanpre, '_descargar_sinupot', None)
                    
                PDFbyte = getsinupot(chip=chip_referencia,barmanpre=None,arealote=arealote)
        
        if PDFbyte:
            with c1:
                st.download_button(label="Descargar Reporte",
                                    data=PDFbyte,
                                    file_name=f"reporte-sinupot-{chip_referencia}.pdf",
                                    mime='application/octet-stream')
        st.markdown("<div style='margin-top: 100px;'></div>", unsafe_allow_html=True)
        
        if not data_prediales.empty and 'tipoDocumento' in data_prediales and 'tipo' in data_prediales:
            data_prediales['tipoDocumento'] = data_prediales.apply(lambda row: row['tipo'] if (pd.isna(row['tipoDocumento']) and isinstance(row['tipo'], str)) else row['tipoDocumento'], axis=1)
        data_prediales['tipoPropietario'] = data_prediales.apply(asignar_tipo_propietario, axis=1)
        
        htmlrender = generar_html(data_predio=data_predios, data_prediales=data_prediales, data_transacciones=data_anotaciones, data_usosuelopredios=data_usosuelopredios)
        st.components.v1.html(htmlrender, height=10000, scrolling=True)
        
        with c2:
            if st.button('Generar PDF'):
                with st.spinner('Procesando PDF...'):
                    html_content = generar_html(data_predio=data_predios, data_prediales=data_prediales, data_transacciones=data_anotaciones, data_usosuelopredios=data_usosuelopredios, pdfversion=True)
                    pdf_bytes    = _principal_getpdf(html_content,seccion='_download_pdf_detalle_unidad')
                    
                    if pdf_bytes:
                        st.download_button(
                            label="Descargar PDF",
                            data=pdf_bytes,
                            file_name="reporte.pdf",
                            mime='application/pdf'
                        )
                    else:
                        st.error("Error al generar el PDF. Por favor intente nuevamente.")
                        
@st.cache_data(show_spinner=False)            
def mergedata(data=pd.DataFrame(),data_predios=pd.DataFrame(),chip_referencia=None):
    if not data.empty and not data_predios.empty:
        datamerge = data_predios[data_predios['prechip']==chip_referencia]
        datamerge = datamerge.sort_values(by='preaconst',ascending=False).drop_duplicates(subset='prechip',keep='first')
        
        variables_same = [x for x in list(datamerge) if x in list(data)] 
        if isinstance(variables_same,list) and variables_same!=[]:
            varrename = {}
            for i in variables_same:
                varrename.update({i:f'{i}_new'})
            datamerge.rename(columns=varrename,inplace=True)
        datamerge.rename(columns={'prechip':'chip'},inplace=True)
        data = data.merge(datamerge,how='left',validate='m:1')
    return data

def asignar_tipo_propietario(row):
    if pd.isna(row['tipoPropietario']) and isinstance(row['tipoDocumento'], str):
        tipo_doc = re.sub('[^a-zA-Z]', '', row['tipoDocumento']).upper()
        if tipo_doc in ['CC', 'TI', 'PA', 'CE']:
            return 'PERSONA NATURAL'
        elif tipo_doc in ['NIT', 'NI']:
            return 'PERSONA JURIDICA'
    return row['tipoPropietario']