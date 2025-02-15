import streamlit as st
import pandas as pd
import re
import hashlib
from datetime import datetime

from functions._principal_getunidades import main as getadataunidades
from display._principal_propietarios import main as generar_html

from data.barmanpreFromgrupo import barmanpreFromgrupo
from data.tracking import savesearch

def main(grupo=None,barmanpre=None):
    #-------------------------------------------------------------------------#
    # Variables
    formato = {
               'token':None,
               'access':False,
               'id_consulta':None,
               'favorito':False,
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
    #-------------------------------------------------------------------------#

    # grupo =  610954
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)

    if grupo is not None:
        data_predios, data_usosuelopredios, data_prediales, data_anotaciones, datapropietarios  = getadataunidades(grupo=grupo)


        if not data_prediales.empty:
            data_prediales['link']            = data_prediales['url'] if not data_prediales.empty and 'url' in data_prediales else None
            data_prediales['tipoDocumento']   = data_prediales.apply(lambda row: row['tipo'] if (pd.isna(row['tipoDocumento']) and isinstance(row['tipo'], str)) else row['tipoDocumento'], axis=1)
            data_prediales['tipoPropietario'] = data_prediales.apply(asignar_tipo_propietario, axis=1)
            idd = (data_prediales['tipo'].isnull()) & (data_prediales['tipoDocumento'].notnull()) if 'tipo' in data_prediales and 'tipoDocumento' in data_prediales else 0
            if sum(idd)>0:
                data_prediales.loc[idd,'tipo'] = data_prediales.loc[idd,'tipoDocumento'].apply( lambda x: re.sub('[^a-zA-Z]','',x) if isinstance(x,str) and x!='' else None)
            
            datagroup         = data_prediales.groupby(['chip'])['year'].max().reset_index()
            datagroup.columns = ['chip','yearmax']
            if 'yearmax' in data_prediales: del data_prediales['yearmax']
            data_prediales = data_prediales.merge(datagroup,on='chip',how='left',validate='m:1')
            data_prediales = data_prediales[data_prediales['year']==data_prediales['yearmax']]
            
        if not data_prediales.empty:
            col1,col2,col3 = st.columns([0.7,0.2,0.1])
            with col2:
                if st.button('Descargar Excel'):
                    
                    if barmanpre is None or pd.isna(barmanpre):
                        data2barmanpre = barmanpreFromgrupo(grupo=grupo)
                        barmanpre      = '|'.join(data2barmanpre['barmanpre'].unique()) if not data2barmanpre.empty and 'barmanpre' in data2barmanpre else None
                    elif isinstance(barmanpre,list) and barmanpre!=[]:
                        try: barmanpre = '|'.join(barmanpre)
                        except: pass
                    barmanpre = barmanpre if isinstance(barmanpre,str) and barmanpre!='' else None
                    
                    savesearch(st.session_state.token, barmanpre, '_descargar_pdf', None)
                    
                    variables = ['link','direccion','year','avaluo_catastral','impuesto_predial','copropiedad','preaconst','preaterre','matriculainmobiliaria','chip','tipoPropietario','tipoDocumento','identificacion','nombre','telefonos','email']
                    variables = [x for x in variables if x in data_prediales]
                    dataexport = data_prediales[variables]
                    
                    try:
                        dataexport['email'] = dataexport['email'].str.split('|')
                        dataexport          = dataexport.explode('email')
                        dataexport['email'] = dataexport['email'].str.strip()
                        dataexport          = dataexport[dataexport['email'].notnull()]
                        dataexport          = dataexport.sort_values(by='tipoPropietario',ascending=False)
                        
                        variables = [x for x in ['fechaDocumento','precuso',] if x in dataexport]
                        if variables!=[]: 
                            dataexport.drop(columns=variables,inplace=True)
                            
                        try:
                            idd = (dataexport['email'].astype(str).str.contains('.')) & (dataexport['email'].astype(str).str.contains('@'))
                            dataexport  = dataexport[idd]
                            idd = dataexport['email'].astype(str).str.lower().contains('notaria')
                            dataexport  = dataexport[~idd]
                        except: pass
                            
                        encriptar = True
                        if encriptar:
                            dataexport["email"]          = dataexport["email"].apply(hash_email) if 'email' in dataexport else None
                            dataexport["nombre"]         = dataexport["nombre"].apply(anonymize_text)  if 'nombre' in dataexport else None
                            dataexport["identificacion"] = dataexport["identificacion"].astype(str).apply(anonymize_text)  if 'identificacion' in dataexport else None
                            dataexport["telefonos"]      = dataexport["telefonos"].astype(str).apply(anonymize_phone)  if 'telefonos' in dataexport else None

                        
                        maxlen     = len(dataexport)
                        dataexport = dataexport.iloc[0:1000,:]
                        if maxlen>1000:
                            with col1:
                                st.write('Por políticas de manejo de la información se permite bajar un máximo de 1,000 registros, si necesita más información por favor ponerse en contacto con un comercial de Urbex')

                    except: pass
                    
                    dataexport.rename(columns={'link': 'Link', 'direccion': 'Dirección', 'chip': 'Chip', 'avaluo_catastral': 'Avalúo Catastral', 'impuesto_predial': 'Impuesto Predial', 'copropiedad': 'Copropiedad', 'preaconst': 'Área construida', 'preaterre': 'Área de terreno', 'tipoPropietario': 'Tipo de Propietario', 'tipoDocumento': 'Tipo de Documento', 'identificacion': 'Identificación', 'nombre': 'Nombre', 'telefonos': 'Teléfonos', 'email': 'Correo Electrónico', 'matriculainmobiliaria': 'Matrícula inmobiliaria', 'cedula_catastral': 'Cédula catastral', 'year': 'Año', 'tipo': 'Tipo de documento'},inplace=True)
                    download_excel(dataexport)

        htmlrender = generar_html(data_propietarios=data_prediales)
        st.components.v1.html(htmlrender, height=10000)
        
def download_excel(df):
    excel_file = df.to_excel('data_property.xlsx', index=False)
    with open('data_property.xlsx', 'rb') as f:
        data = f.read()
    st.download_button(
        label="Haz clic aquí para descargar",
        data=data,
        file_name='data_property.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
            
def asignar_tipo_propietario(row):
    if pd.isna(row['tipoPropietario']) and isinstance(row['tipoDocumento'], str):
        tipo_doc = re.sub('[^a-zA-Z]', '', row['tipoDocumento']).upper()
        if tipo_doc in ['CC', 'TI', 'PA', 'CE']:
            return 'PERSONA NATURAL'
        elif tipo_doc in ['NIT', 'NI']:
            return 'PERSONA JURIDICA'
    return row['tipoPropietario']

def hash_email(email):
    if pd.isna(email) or email == "":
        return ""
    email = email.strip().lower()  # Estandarizar (el hashing es sensible a mayúsculas/minúsculas)
    return hashlib.sha256(email.encode()).hexdigest()

# Función para anonimizar nombres y documentos
def anonymize_text(text):
    if pd.isna(text) or text == "":
        return ""
    words = text.split()
    masked_words = []
    for word in words:
        if len(word) > 3:
            masked_words.append(word[:3] + "*" * (len(word) - 3))
        else:
            masked_words.append(word)  # Si la palabra tiene 3 caracteres o menos, se deja igual
    return " ".join(masked_words)

# Función para anonimizar números de teléfono
def anonymize_phone(phone):
    if pd.isna(phone) or phone == "":
        return ""
    phones = phone.split(" | ")
    masked_phones = [p[:3] + "***" if len(p) > 3 else p for p in phones]
    return " | ".join(masked_phones)