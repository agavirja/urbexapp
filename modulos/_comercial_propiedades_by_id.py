import streamlit as st
import re
import pandas as pd
import random
from datetime import datetime

from functions._principal_propietarios_id import main as _principal_propietarios
from functions.getuso_destino import usosuelo_class

from data._principal_getvehiculos import main as _principal_getvehiculos
from data.tracking import savesearch

from display._principal_generador_leads_byid import main as generar_html

def main():

    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'data_propertybyid_info':pd.DataFrame(),
               'data_propertybyid_shd_actual':pd.DataFrame(),
               'data_propertybyid_transacciones':pd.DataFrame(),
               'data_propertybyid_transacciones_nal':pd.DataFrame(),
               'data_shd_historico':pd.DataFrame(),
               'data_vehiculos':pd.DataFrame(),
               'zoom_start_data_propertybyid':12,
               'latitud_propertybyid':4.652652, 
               'longitud_propertybyid':-74.077899,
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
    # Formulario      
    col1,col2,col3 = st.columns(3,vertical_alignment='center')
    with col1: 
        tipodocumento = st.selectbox('Tipo de documento',options=['CC','NIT','CE','PA','TI'])
    with col2:
        numerodocumento = st.number_input('Número de documento',value=0,min_value=0)
    with col3:
        if st.button('Buscar'): 
            st.session_state.data_propertybyid_info , st.session_state.data_propertybyid_shd_actual, st.session_state.data_propertybyid_transacciones, st.session_state.data_propertybyid_transacciones_nal, st.session_state.data_shd_historico = _principal_propietarios(grupo=[re.sub('[^0-9]','',f'{numerodocumento}')])
            st.session_state.data_vehiculos  = _principal_getvehiculos(identificaciones=[f'{numerodocumento}'])
            
            # Guardar:
            inputvar = {'tipodocumento':tipodocumento,'numerodocumento':numerodocumento}
            _,st.session_state.id_consulta = savesearch(st.session_state.token, None, '_comercial_propiedades_by_id', inputvar)


    st.markdown("<div style='margin-bottom: 50px;'></div>", unsafe_allow_html=True)
    
    htmlrender = generar_html(dataresult=st.session_state.data_propertybyid_info.copy(), data_predios=st.session_state.data_propertybyid_shd_actual.copy(), data_transacciones=st.session_state.data_propertybyid_transacciones.copy(), data_transacciones_nal=st.session_state.data_propertybyid_transacciones_nal.copy(), data_shd_historico=st.session_state.data_shd_historico.copy(), data_vehiculos=st.session_state.data_vehiculos.copy())
    st.components.v1.html(htmlrender, height=5000, scrolling=True)

            
    #st.dataframe(st.session_state.data_propertybyid_info)
    #st.dataframe(st.session_state.data_propertybyid_shd_actual)
    #st.dataframe(st.session_state.data_propertybyid_transacciones)
    #st.dataframe(st.session_state.data_propertybyid_transacciones_nal)
    #st.dataframe(st.session_state.data_shd_historico)
    #st.dataframe(st.session_state.data_vehiculos)
    
def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }
