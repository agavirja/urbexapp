import streamlit as st
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor

@st.cache_data(show_spinner=False)
def main(identificaciones=None):

    def fetch_data(identificacion):
        response_info = {}
        # Iterar sobre los posibles códigos de documento
        for coddoc in [4, 3, 5, 6, 1, 2, 7]:
            url = "https://oficinavirtual.shd.gov.co/ServiciosRITDQ/resources/contribuyente"
            data = {
                "codTId": coddoc,
                "nroId": f"{identificacion}"
            }
            try:
                response_info = requests.post(url, json=data, verify=False).json()
                if 'codigoError' in response_info and isinstance(response_info['codigoError'], str) and '0' in response_info['codigoError']:
                    break
            except:
                pass

        # Vehículos
        dataresult = pd.DataFrame()
        try:
            url = "https://oficinavirtual.shd.gov.co/ServiciosRITDQ/resources/consultas/vehiculos"
            data = {"idSujeto": response_info['contribuyente']['idSujeto']}
            response_vehiculos = requests.post(url, json=data, verify=False).json()
            dataresult = pd.DataFrame(response_vehiculos['vehiculos'])
            if not dataresult.empty:
                for j in ['carroceria', 'clase', 'linea', 'marca', 'tipoServicio']:
                    dataresult[j] = dataresult[j].apply(lambda x: getitem(x))
                dataresult['identificacion'] = identificacion  # Agregar identificación al DataFrame
        except:
            pass

        return dataresult
    
    with ThreadPoolExecutor() as executor:
        resultados = list(executor.map(fetch_data, identificaciones))

    datos_totales = pd.concat(resultados, ignore_index=True)
    return datos_totales

def getitem(x):
    try:
        return x['nombre'].strip()
    except:
        return x