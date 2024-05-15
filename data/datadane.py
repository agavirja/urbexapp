import streamlit as st
import pandas as pd
import re
import requests

@st.cache_data(show_spinner=False)
def main(polygon):
    try:
        # https://geoportal.dane.gov.co/geovisores/territorio/analisis-cnpv-2018/
        coordenadas = re.findall(r"(-?\d+\.\d+) (-?\d+\.\d+)", polygon)
        coordenadas = coordenadas[:-1]
        coordenadas = ",".join([f"{lon},{lat}" for lon, lat in coordenadas])
        url = f"https://geoportal.dane.gov.co/laboratorio/serviciosjson/poblacion/20221215-indicadordatospoligonos.php?coordendas={coordenadas}"
        r   = requests.get(url,verify=False, timeout=20).json()
        df  = pd.DataFrame(r)
        df.rename(columns={'V1': 'Total viviendas', 'V2': 'Uso mixto', 'V3': 'Unidad no residencial', 'V4': 'Lugar especial de alojamiento - LEA', 'V5': 'Industria (uso mixto)', 'V6': 'Comercio (uso mixto)', 'V7': 'Servicios (uso mixto)', 'V8': 'Agropecuario, agroindustrial, foresta (uso mixto)', 'V9': 'Sin información (uso mixto)', 'V10': 'Industria (uso no residencial)', 'V11': 'Comercio (uso no residencial)', 'V12': 'Servicios (uso no residencial)', 'V13': 'Agropecuario, Agroindustrial, Foresta (uso no residencial)', 'V14': 'Institucional (uso no residencial)', 'V15': 'Lote (Unidad sin construcción)', 'V16': 'Parque/ Zona Verde (uso no residencial)', 'V17': 'Minero-Energético (uso no residencial)', 'V18': 'Protección/ Conservación ambiental (uso no residencial)', 'V19': 'En Construcción (uso no residencial)', 'V20': 'Sin información (uso no residencial)', 'V21': 'Viviendas', 'V22': 'Casa', 'V23': 'Apartamento', 'V24': 'Tipo cuarto', 'V25': 'Vivienda tradicional indígena', 'V26': 'Vivienda tradicional étnica (Afrocolombiana, Isleña, Rom)', 'V27': 'Otro (contenedor, carpa, embarcación, vagón, cueva, refugio natural, etc.)', 'V28': 'Ocupada con personas presentes', 'V29': 'Ocupada con todas las personas ausentes', 'V30': 'Vivienda temporal (para vacaciones, trabajo, etc.)', 'V31': 'Desocupada', 'V32': 'Hogares', 'V33': 'A', 'V34': 'B', 'V35': 'Estrato 1', 'V36': 'Estrato 2', 'V37': 'Estrato 3', 'V38': 'Estrato 4', 'V39': 'Estrato 5', 'V40': 'Estrato 6', 'V41': 'No sabe o no tiene estrato', 'V42': 'C', 'V43': 'D', 'V44': 'E', 'V45': 'F', 'V46': 'G', 'V47': 'H', 'V48': 'J', 'V49': 'K', 'V50': 'L', 'V51': 'M', 'V52': 'N', 'V53': 'O', 'V54': 'P', 'V55': 'Q', 'V56': 'Total personas', 'V57': 'Hombres', 'V58': 'Mujeres', 'V59': '0 a 9 años', 'V60': '10 a 19 años', 'V61': '20 a 29 años', 'V62': '30 a 39 años', 'V63': '40 a 49 años', 'V64': '50 a 59 años', 'V65': '60 a 69 años', 'V66': '70 a 79 años', 'V67': '80 años o más', 'V68': 'Ninguno (Educacion)', 'V69': 'Sin Información (Educacion)', 'V70': 'Preescolar - Prejardin, Básica primaria 1 (Educacion)', 'V71': 'Básica secundaria 6, Media tecnica 10, Normalista 10 (Educacion)', 'V72': 'Técnica profesional 1 año, Tecnológica 1 año, Universitario 1 año (Educacion)', 'V73': 'Especialización 1 año, Maestria 1 año, Doctorado 1 año (Educacion)'},inplace=True)
    except: df = pd.DataFrame()
    return df
