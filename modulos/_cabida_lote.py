import streamlit as st
import pandas as pd
import geopandas as gpd
from bs4 import BeautifulSoup

from functions._principal_getdatacabida import main as getdatacabida
from functions._principal_cabida_shape import main as cabida_inputs
from functions._principal_getpdf import main as _principal_getpdf

from display._principal_cabida import main as generar_html

def main(grupo=None):
    

    style_page()
    
    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'cabida_default':True,
               
               'building_shape_grid': gpd.GeoDataFrame(), 
               'building_shape_geometry': gpd.GeoDataFrame(), 
               'areabuilding': 0, 
               'poligono_lote': None, 
               'allgrid': gpd.GeoDataFrame(),
               'grid': gpd.GeoDataFrame(), 
               'border': gpd.GeoDataFrame(), 
               'data_andenes': gpd.GeoDataFrame(), 
               'data_vias': gpd.GeoDataFrame(), 
               'dataunion': gpd.GeoDataFrame(), 
               'esquinero': False,
               
               'toggle1':True,
               'toggle2':False,
               }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    # Se peude bajar el formulario  N px
    st.markdown(
    """
    <style>
    .margen {
        margin-top: 0px;  
    }
    .margen-1 {
        margin-top: 100px;  
    }
    </style>
    """, unsafe_allow_html=True
    )

    #-------------------------------------------------------------------------#
    # Data general lote(s)
    info_pot,info_terreno,latitud,longitud,polygon,data_precios_referencia, data_lotes, data_construcciones = getdatacabida(grupo=grupo)

    #-------------------------------------------------------------------------#
    # Inputs:
    aislamiento_frontal   = 0
    aislamiento_posterior = 0
    aislamiento_lateral   = 0
    reduccion_poligono    = 0
    

    colb1,colb2,colb3 = st.columns([6,1,1],vertical_alignment="center")
    col1,col2         = st.columns([0.25,0.75])
    with col1:

        #---------------------------------------------------------------------#
        # Formulario para la estructuracion del edificio
        #---------------------------------------------------------------------#
        st.markdown('<div class="margen"></div>', unsafe_allow_html=True)  # Espacio de 500px
        titulo = 'Variables para la simulación:'
        html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
        texto  = BeautifulSoup(html, 'html.parser')
        st.markdown(texto, unsafe_allow_html=True)

        # Pisos a silumar:
        pisos_default = info_pot['altura_index']-1 if 'altura_index' in info_pot and isinstance(info_pot['altura_index'],int) else 0
        numero_pisos  = st.selectbox('Número de pisos a simular:',options=range(1,31),index=pisos_default)
        
        # Altura de planta:
        alturapiso    = st.number_input('Altura de cada planta:',value=3.0,min_value=0.0,max_value=100.0)
        
        # Proporcion areas comunes:
        proporcion_areas_comunes = st.number_input('Porcentaje de uso de áreas comúnes:',value=20.0,min_value=0.0,max_value=100.0)
        proporcion_areas_comunes = proporcion_areas_comunes/100

        # Forma del edificio:
        options = ['optimizado','rectangulo','cuadrado','L','U']
        shape   = st.selectbox('Forma del edificio',options=options)
        if 'optimizado' in shape or shape=='':
            shape = 'multiple_matriz'
            
        blocks_dis = 0
        if isinstance(shape,str) and shape=='multiple_matriz':
            blocks_dis = st.number_input('Distancia entre edificios (metros)',value=2,min_value=0)
            
        # Aislamiento
        aislamiento           = st.checkbox("Aislamientos:",key="toggle1",on_change=toggle_button1)
        aislamiento_frontal   = st.number_input('Aislamiento frontal (metros)',value=aislamiento_frontal,min_value=0,disabled=False if aislamiento else True)
        aislamiento_posterior = st.number_input('Aislamiento posterior (metros)',value=aislamiento_posterior,min_value=0,disabled=False if aislamiento else True)
        aislamiento_lateral   = st.number_input('Aislamiento lateral (metros)',value=aislamiento_lateral,min_value=0,disabled=False if aislamiento else True)
                   
        
        # Reduccion:
        st.checkbox("Porcentaje del lote:",key="toggle2",on_change=toggle_button2)
        reduccion_poligono    = st.number_input('Porcentaje del lote para construir (%):',value=reduccion_poligono,min_value=0,max_value=100,disabled=True if aislamiento else False)
        if reduccion_poligono>0:
            reduccion_poligono = round(reduccion_poligono/100,2)
            
        if aislamiento:
            reduccion_poligono = 0
        else:
            aislamiento_frontal   = 0
            aislamiento_posterior = 0
            aislamiento_lateral   = 0
                    
            
        aislamiento_frontal   = int(round(aislamiento_frontal+0.49))
        aislamiento_posterior = int(round(aislamiento_posterior+0.49))
        aislamiento_lateral   = int(round(aislamiento_lateral+0.49))
        blocks_dis            = int(round(blocks_dis+0.49))


        if st.session_state.cabida_default: 
            st.session_state.building_shape_grid, st.session_state.building_shape_geometry, st.session_state.areabuilding, st.session_state.poligono_lote, st.session_state.allgrid, st.session_state.grid, st.session_state.border, st.session_state.data_andenes, st.session_state.data_vias, st.session_state.dataunion, st.session_state.esquinero = cabida_inputs(grupo=grupo, aislamiento_frontal=aislamiento_frontal, aislamiento_posterior=aislamiento_posterior, aislamiento_lateral=aislamiento_lateral, reduccion_poligono=reduccion_poligono, nblocks=1, blocks_dis=blocks_dis, shape=shape)
            st.session_state.cabida_default = False
            if st.session_state.building_shape_geometry.empty:
                st.session_state.building_shape_grid, st.session_state.building_shape_geometry, st.session_state.areabuilding, st.session_state.poligono_lote, st.session_state.allgrid, st.session_state.grid, st.session_state.border, st.session_state.data_andenes, st.session_state.data_vias, st.session_state.dataunion, st.session_state.esquinero = cabida_inputs(grupo=grupo, aislamiento_frontal=aislamiento_frontal, aislamiento_posterior=aislamiento_posterior, aislamiento_lateral=aislamiento_lateral, reduccion_poligono=reduccion_poligono, nblocks=1, blocks_dis=blocks_dis, shape='cuadrado')

                
        if not st.session_state.cabida_default: 
            if st.button('Simular'):
                with col2:
                    with st.spinner('Proceso de simulación del proyecto'):
                        st.session_state.building_shape_grid, st.session_state.building_shape_geometry, st.session_state.areabuilding, st.session_state.poligono_lote, st.session_state.allgrid, st.session_state.grid, st.session_state.border, st.session_state.data_andenes, st.session_state.data_vias, st.session_state.dataunion, st.session_state.esquinero = cabida_inputs(grupo=grupo, aislamiento_frontal=aislamiento_frontal, aislamiento_posterior=aislamiento_posterior, aislamiento_lateral=aislamiento_lateral, reduccion_poligono=reduccion_poligono, nblocks=1, blocks_dis=blocks_dis, shape=shape)
                        if st.session_state.building_shape_geometry.empty:
                            st.session_state.building_shape_grid, st.session_state.building_shape_geometry, st.session_state.areabuilding, st.session_state.poligono_lote, st.session_state.allgrid, st.session_state.grid, st.session_state.border, st.session_state.data_andenes, st.session_state.data_vias, st.session_state.dataunion, st.session_state.esquinero = cabida_inputs(grupo=grupo, aislamiento_frontal=aislamiento_frontal, aislamiento_posterior=aislamiento_posterior, aislamiento_lateral=aislamiento_lateral, reduccion_poligono=reduccion_poligono, nblocks=1, blocks_dis=blocks_dis, shape='cuadrado')                        
                        st.rerun()
            
        #---------------------------------------------------------------------#
        # Formulario para la configuracion del edificio
        #---------------------------------------------------------------------#
        st.markdown('<div class="margen-1"></div>', unsafe_allow_html=True)  # Espacio de 500px
        titulo = 'Configuración de plantas:'
        html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
        texto  = BeautifulSoup(html, 'html.parser')
        st.markdown(texto, unsafe_allow_html=True)
        
            #-------------------------------------------------------------#
            # Planta 1
        st.write('')
        st.write('Planta 1:')
        
        inputvar = []
        porcentajeacumulado = 0
        areaplantas         = st.session_state.areabuilding
        index = 1
    
        while porcentajeacumulado<1:
            colp1, colp2 = st.columns([0.6,0.4])
            with colp1:
                tipoinmueble = st.selectbox('Tipo de inmueble:', options=['Áreas comunes','Apartamento', 'Bodega', 'Casa', 'Local', 'Oficina'], key=f'tipoinmueble_1_{index}')
            with colp2:
                max_value = (1 - porcentajeacumulado) * 100.0
                porcentaje = st.number_input('Porcentaje:', value=max_value, min_value=0.0, max_value=max_value, key=f'porcentaje_1_{index}') / 100
                porcentajeacumulado += porcentaje
    
            areavendible = porcentaje * areaplantas*(1-proporcion_areas_comunes)
            inputvar.append({'planta':'1','pisomin': 1, 'pisomax': 1,'tipoinmueble': tipoinmueble, 'porcentaje': porcentaje, 'areavendible': areavendible})
            index += 1
    
        st.write('')
        st.write('Siguientes plantas:')
        index = 1
        if numero_pisos > 1:
            pisomax = 0
            while pisomax < numero_pisos:
                index += 1
                colp1, colp2 = st.columns(2)
                with colp1:
                    if pisomax == 0:
                        pisomin_options = [2]
                    else:
                        pisomin_options = [pisomax + 1]
                    pisomin = st.selectbox('Desde el piso:', options=pisomin_options, key=f'planta_2_min_{index}')
                
                with colp2:
                    if pisomin is not None:
                        options = list(range(pisomin, numero_pisos + 1))
                        pisomax = st.selectbox('Hasta el piso:', options=options, index=len(options) - 1, key=f'planta_2_max_{index}')
    
                tipoinmueble = st.selectbox('Tipo de inmueble:', options=['Apartamento', 'Oficina'], key=f'tipoinmueble_2_{index}')
                porcentaje = 100
                if pisomin is not None and pisomax is not None:
                    areavendible = (pisomax - pisomin + 1) * areaplantas*(1-proporcion_areas_comunes)
                else:
                    areavendible = 0 
                inputvar.append({'planta':'2+','pisomin': pisomin, 'pisomax': pisomax, 'tipoinmueble': tipoinmueble, 'porcentaje': porcentaje, 'areavendible': areavendible})
        
        #---------------------------------------------------------------------#
        # Precios de referencia
        #---------------------------------------------------------------------#
        datapricing  = pd.DataFrame(inputvar)
        if not datapricing.empty and 'tipoinmueble' in datapricing:
            idd      = datapricing['tipoinmueble'].str.contains('Áreas comunes')
            datapricing = datapricing[~idd]
            if not datapricing.empty:
                datapricing = datapricing.groupby('tipoinmueble')['areavendible'].sum().reset_index()
            
        if not datapricing.empty:
            titulo = 'Precios de referencia:'
            html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1></section></body></html>"""
            texto  = BeautifulSoup(html, 'html.parser')
            st.markdown(texto, unsafe_allow_html=True)
    
            datapricing.index      = range(len(datapricing))
            datapricing['precio']  = 0
            datapricing['recaudo'] = 0
            for i in range(len(datapricing)):
                tipoinmueble = datapricing['tipoinmueble'].iloc[i]
                st.write(tipoinmueble.title())
                
                valueref = 0
                if not data_precios_referencia.empty:
                    datapaso = data_precios_referencia[data_precios_referencia['tipoinmueble'].str.lower().str.contains(tipoinmueble.lower()[0:4])]
                    if not datapaso.empty:
                        valueref = int(datapaso['max'].iloc[0]) if all([x for x in ['tipo','max'] if x in data_precios_referencia]) and isinstance(datapaso['max'].iloc[0],(float,int)) else 0
                precio = st.number_input(f'Precio de referencia {tipoinmueble}:',min_value=0,value=valueref,key=f'precioref{tipoinmueble}')
                datapricing.loc[i,'precio']  = precio
                datapricing.loc[i,'recaudo'] = precio*datapricing.loc[i,'areavendible']
            
    #-------------------------------------------------------------------------#
    # Resaltar edificios
    #-------------------------------------------------------------------------#
    data_lotes['geometry']          = gpd.GeoSeries.from_wkt(data_lotes['wkt'])
    data_lotes                      = gpd.GeoDataFrame(data_lotes, geometry='geometry')
    data_construcciones['geometry'] = gpd.GeoSeries.from_wkt(data_construcciones['wkt'])
    data_construcciones             = gpd.GeoDataFrame(data_construcciones, geometry='geometry')

    if isinstance(grupo,str) and grupo!='':
        grupo = grupo.split('|')
    elif isinstance(grupo,(float,int)):
        grupo = [f'{grupo}']
    if isinstance(grupo,list) and grupo!=[]:
        grupo = list(map(str, grupo))
        
    # Quitar el 3D de(l) lote(s) bajo estudio
    listagrupo = [int(x) for x in grupo]
    idd        = data_construcciones['grupo'].isin(listagrupo)
    if sum(idd)>0:
        data_construcciones = data_construcciones[~idd]
        
    # Resaltar el lote 
    idd                = data_lotes['grupo'].isin(listagrupo)
    data_lotes['lote'] = False
    if sum(idd)>0:
        data_lotes = data_lotes[~idd]
    datappend         = gpd.GeoDataFrame(geometry=[st.session_state.poligono_lote])
    datappend['lote'] = True
    data_lotes        = pd.concat([data_lotes,datappend])
            
    with col2:
        tipoinmueble = [x.lower()[0:4] for x in datapricing['tipoinmueble'].unique() if isinstance(x,str)]
        if isinstance(tipoinmueble,list) and tipoinmueble!=[]:
            data_precios_referencia = data_precios_referencia[data_precios_referencia['tipoinmueble'].str.lower().str.contains('|'.join(tipoinmueble))]
        
        htmlrender = generar_html( info_pot, info_terreno, proporcion_areas_comunes, datapricing, data_precios_referencia, numero_pisos, alturapiso, latitud, longitud, data_lotes, data_construcciones, st.session_state.building_shape_geometry, st.session_state.poligono_lote, st.session_state.grid, st.session_state.data_andenes, st.session_state.data_vias)
        st.components.v1.html(htmlrender, height=2000, scrolling=True)
        
    with colb2:
        if st.button('Generar PDF'):
            with st.spinner('Procesando PDF...'):
                pdf_bytes    = _principal_getpdf(htmlrender,seccion='_download_pdf_cabida_lote')
                
                if pdf_bytes:
                    st.download_button(
                        label="Descargar PDF",
                        data=pdf_bytes,
                        file_name="reporte.pdf",
                        mime='application/pdf'
                    )
                else:
                    st.error("Error al generar el PDF. Por favor intente nuevamente.")
                    
def toggle_button1():
    
    formato = {
        'toggle1':True,
        'toggle2':False,
    }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    if st.session_state.toggle1:
        st.session_state.toggle2 = False

def toggle_button2():
    
    formato = {
        'toggle1':True,
        'toggle2':False,
    }
    
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    if st.session_state.toggle2:
        st.session_state.toggle1 = False
        
        
def style_page(maxwidth=None):
    letra_options = '0.75vw'
    letra_titulo  = '0.75vw'

    st.markdown(
        f"""
        <style>
    
        .stApp {{
            background-color: #fff;        
            opacity: 1;
            background-size: cover;
        }}
        
        div[data-testid="collapsedControl"] {{
            color: #000;
            }}
        
        div[data-testid="collapsedControl"] svg {{
            background-image: url('https://iconsapp.nyc3.digitaloceanspaces.com/house-black.png');
            background-size: cover;
            fill: transparent;
            width: 20px;
            height: 20px;
        }}
        
        div[data-testid="collapsedControl"] button {{
            background-color: transparent;
            border: none;
            cursor: pointer;
            padding: 0;
        }}

        div[data-testid="stToolbar"] {{
            visibility: hidden; 
            height: 0%; 
            position: fixed;
            }}
        div[data-testid="stDecoration"] {{
            visibility: hidden; 
            height: 0%; 
            position: fixed;
            }}
        div[data-testid="stStatusWidget"] {{
            visibility: hidden; 
            height: 0%; 
            position: fixed;
            }}
    
        #MainMenu {{
        visibility: hidden; 
        height: 0%;
        }}
        
        header {{
            visibility: hidden; 
            height:
                0%;
            }}
            
        footer {{
            visibility: hidden; 
            height: 0%;
            }}
        
        div[data-testid="stSpinner"] {{
            color: #000000;
            background-color: #F0F0F0; 
            padding: 10px; 
            border-radius: 5px;
            }}
        
        a[href="#responsive-table"] {{
            visibility: hidden; 
            height: 0%;
            }}
        
        a[href^="#"] {{
            /* Estilos para todos los elementos <a> con href que comienza con "#" */
            visibility: hidden; 
            height: 0%;
            overflow-y: hidden;
        }}

        div[class="table-scroll"] {{
            background-color: #a6c53b;
            visibility: hidden;
            overflow-x: hidden;
            }}
            
        button[data-testid="StyledFullScreenButton"] {{
            visibility: hidden; 
            height: 0%;
        }}
        
        .stButton button {{
                background-color: #A16CFF;
                font-weight: bold;
                width: 100%;
                border: 2px solid #A16CFF;
                color:white;
            }}
        
        .stButton button:hover {{
            background-color: #A16CFF;
            color: white;
            border: #A16CFF;
        }}
        
        .stButton button:active {{
            background-color: #FFF;
            color: #A16CFF;
            border: 2px solid #FFF;
            outline: none;
        }}
    
        [data-testid="stMultiSelect"] {{
            border: 5px solid #F0F0F0;
            background-color: #F0F0F0;
            border-radius: 5px;
            padding: 5px; 
        }}
        li[role="option"] > div {{
            font-size: {letra_options};
        }}
        div[data-testid="stMultiSelect"] div[data-baseweb="select"] span {{
            font-size: {letra_options};
        }}
        
        [data-baseweb="select"] > div {{
            background-color: #fff;
        }}
        
        [data-testid="stTextInput"] {{
            border: 5px solid #F0F0F0;
            background-color: #F0F0F0;
            border-radius: 5px;
            padding: 5px;
            font-size: {letra_options};
        }}
    
    
        [data-testid="stSelectbox"] {{
            border: 5px solid #F0F0F0;
            background-color: #F0F0F0;
            border-radius: 5px;
            padding: 5px;  
        }}
        
        button[data-testid="StyledFullScreenButton"] {{
            visibility: hidden; 
            height: 0%;
            
        }}

        [data-testid="stNumberInput"] {{
            border: 5px solid #F0F0F0;
            background-color: #F0F0F0;
            border-radius: 5px;
            padding: 5px;
            font-size: 5px;
        }}
        
        [data-baseweb="input"] > div {{
            background-color: #fff;
        }}
        
        div[data-testid="stNumberInput-StepUp"]:hover {{
            background-color: #A16CFF;
        }}
        
        label[data-testid="stWidgetLabel"] p {{
            font-size: {letra_titulo};
            font-weight: bold;
            color: #3C3840;
            font-family: 'Aptos Narrow';
        }}
        
        span[data-baseweb="tag"] {{
          background-color: #5F59EB;
        }}
        
        [data-testid="stDateInput"] {{
            border: 5px solid #F0F0F0;
            background-color: #F0F0F0;
            border-radius: 5px;
            padding: 5px; 
        }}
            
        .stDownloadButton button {{
            background-color: #DAE8D8;
            font-weight: bold;
            width: 100%;
            border: 2px solid #DAE8D8;
            color: black;
        }}
        
        .stDownloadButton button:hover {{
            background-color: #DAE8D8;
            color: black;
            border: #DAE8D8;
        }}        

        [data-testid="stNumberInput"] input,
        [data-testid="stNumberInput-Input"] {{
            font-size: {letra_options};
        }}
        
        </style>
        """,
        unsafe_allow_html=True
    )
