import folium
import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import shapely.wkt as wkt
from streamlit_js_eval import streamlit_js_eval
from streamlit_vertical_slider import vertical_slider
from sqlalchemy import create_engine 
from datetime import datetime
from streamlit_folium import st_folium
from shapely.geometry import mapping,Point
from bs4 import BeautifulSoup

from data.circle_polygon import circle_polygon
from data.getdatalotes import main as getdatalotes
from data.getdataTransactions import main as getdataTransactions
from data.getuso_destino import getuso_destino
from data.datadane import main as censodane
from data.data_listings import listingsBypolygon

from display.stylefunctions  import style_function_geojson

def main(code=None,polygon=None,latitud=None,longitud=None,precuso=None,metros_default=500):
    
    #-------------------------------------------------------------------------#
    # Tamano de la pantalla 
    screensize = 1920
    mapw = int(screensize*0.8)
    maph = int(screensize*0.3)
    try:
        screensize = streamlit_js_eval(js_expressions='screen.width', key = 'SCR')
        mapw  = int(screensize*0.8)
        maph  = int(screensize*0.3)
    except: pass

    #-------------------------------------------------------------------------#
    # Latitud y longitud
    
    datalotes    = pd.DataFrame()
    tipoconsulta = None
    if isinstance(polygon, str):
        if latitud is None or longitud is None:
            try:
                latitud  = wkt.loads(polygon).centroid.y
                longitud = wkt.loads(polygon).centroid.x
            except: pass
        inputvar =  {
            'polygon':polygon,
            'latitud':latitud,
            'longitud':longitud,
            }
        tipoconsulta = 'polygon'
        
    else:
        if latitud is None and longitud is None and code is not None: 
            latitud, longitud, precuso = latlngFrombarmanpre(code)
                    
        if (isinstance(latitud, float) or isinstance(latitud, int)) or (isinstance(longitud, float) or isinstance(longitud, int)):
            polygon  = str(circle_polygon(500,latitud,longitud))
            inputvar =  {
                'polygon':polygon,
                'latitud':latitud,
                'longitud':longitud,
                }
            tipoconsulta = 'radio'
            
    cols1,cols2 = st.columns(2,gap='large')
    colm1,colm2 = st.columns([0.05,0.95])
    coll1,coll2 = st.columns([0.2,0.8])
    if isinstance(polygon, str):
        with st.spinner('Buscando información (puede durar unos minutos)'):
            datalotes                      = getdatalotes(inputvar)
            datacatastro,datatransacciones = builddata(polygon=polygon)
            #-------------------------------------------------------------------------#
            # Slider
            if isinstance(tipoconsulta, str) and 'radio' in tipoconsulta:
                with colm1:
                    st.write('')
                    st.write('')
                    st.write('')
                    st.write('')
                    st.write('')
                    st.write('')
                    metros  = vertical_slider(
                        key = "vert_01" ,
                        height = int(maph*0.7), 
                        thumb_shape = "circle",
                        step = 100,
                        default_value=metros_default,
                        min_value= 100,
                        max_value= 500, 
                        track_color = "#9c9c9c",
                        slider_color = '#6EA4EE',
                        thumb_color= "#828DEE", 
                    )
                    
                if metros is not None and not datalotes.empty and 'distance' in datalotes:
                    datalotes         = datalotes[datalotes['distance']<=metros]
                    datacatastro      = datacatastro[datacatastro['barmanpre'].isin(datalotes['barmanpre'])]
                    datatransacciones = datatransacciones[datatransacciones['prechip'].isin(datacatastro['prechip'])]

    if isinstance(tipoconsulta, str):
        if 'radio' in tipoconsulta:
            polygon = circle_polygon(metros,latitud,longitud)
        elif 'polygon' in tipoconsulta:
            polygon = wkt.loads(polygon)

    #-------------------------------------------------------------------------#
    # Filtros
    if not datacatastro.empty:
        with cols1:
            options = sorted(list(datacatastro[datacatastro['destino'].notnull()]['destino'].unique()))
            options = ['Todos'] + options
            tipodestino  = st.selectbox('Filtro por tipo de destino:',options=options)
            if 'todo' not in tipodestino.lower():
                datacatastro      = datacatastro[datacatastro['destino']==tipodestino]
                datalotes         = datalotes[datalotes['barmanpre'].isin(datacatastro['barmanpre'])]
                datatransacciones = datatransacciones[datatransacciones['prechip'].isin(datacatastro['prechip'])]
                
        with cols2:
            options = sorted(list(datacatastro[datacatastro['usosuelo'].notnull()]['usosuelo'].unique()))
            options = ['Todos'] + options
            tipouso = st.selectbox('Filtro por de uso del suelo:',options=options) 
            if 'todo' not in tipouso.lower():
                datacatastro      = datacatastro[datacatastro['usosuelo']==tipouso]
                datalotes         = datalotes[datalotes['barmanpre'].isin(datacatastro['barmanpre'])]
                datatransacciones = datatransacciones[datatransacciones['prechip'].isin(datacatastro['prechip'])]

        with cols1:
            tipotrans = st.selectbox('Filtro de transacciones:',options=['Todos','Los que tienen transacciones']) 
            if 'Los que tienen transacciones' in tipotrans and not datatransacciones.empty:
                datacatastro = datacatastro[datacatastro['prechip'].isin(datatransacciones['prechip'])]
                datalotes    = datalotes[datalotes['barmanpre'].isin(datacatastro['barmanpre'])]
         
        with cols2:
            tiposelected = st.selectbox('Filtro de las graficas por:', options=['Destino','Uso del suelo'])
            if 'Destino' in tiposelected: 
                tiposelected = 'destino'
                titulo       = 'Destino'
            elif 'Uso del suelo' in tiposelected: 
                tiposelected = 'usosuelo'
                titulo       = 'Uso del Suelo'

        with cols1:
            areamin = st.number_input('Filtro por área privada mínima:',min_value=0,value=0,step=1)
            if areamin>0: 
                datacatastro      = datacatastro[datacatastro['preaconst']>=areamin]
                datalotes         = datalotes[datalotes['barmanpre'].isin(datacatastro['barmanpre'])]
                datatransacciones = datatransacciones[datatransacciones['prechip'].isin(datacatastro['prechip'])]

        with cols2:
            areamax = st.number_input('Filtro por área privada máxima:',min_value=0,value=0,step=1)
            if areamax>0: 
                datacatastro      = datacatastro[datacatastro['preaconst']<=areamax]
                datalotes         = datalotes[datalotes['barmanpre'].isin(datacatastro['barmanpre'])]
                datatransacciones = datatransacciones[datatransacciones['prechip'].isin(datacatastro['prechip'])]

        with cols1:
            minyear         = 1940
            antiguedaddesde = st.number_input('Antigüedad desde:',min_value=minyear,value=minyear,max_value=datetime.now().year,step=1)
            if antiguedaddesde>0: 
                datacatastro      = datacatastro[datacatastro['prevetustz']>=antiguedaddesde]
                datalotes         = datalotes[datalotes['barmanpre'].isin(datacatastro['barmanpre'])]
                datatransacciones = datatransacciones[datatransacciones['prechip'].isin(datacatastro['prechip'])]

        with cols2:
            antiguedadhasta = st.number_input('Antigüedad hasta:',min_value=minyear,value=datetime.now().year,max_value=datetime.now().year,step=1)
            if antiguedadhasta>0: 
                datacatastro      = datacatastro[datacatastro['prevetustz']<=antiguedadhasta]
                datalotes         = datalotes[datalotes['barmanpre'].isin(datacatastro['barmanpre'])]
                datatransacciones = datatransacciones[datatransacciones['prechip'].isin(datacatastro['prechip'])]
                
    
    #-------------------------------------------------------------------------#
    # Mapa
    if not datalotes.empty and (isinstance(latitud, float) or isinstance(latitud, int)) or (isinstance(longitud, float) or isinstance(longitud, int)):
        
        m = folium.Map(location=[latitud, longitud], zoom_start=16,tiles="cartodbpositron")
        folium.GeoJson(mapping(polygon), style_function=style_function_color).add_to(m)
        
        geopoints = TransactionMarker(datatransacciones.copy(),datacatastro.copy(),datalotes.copy())
        if '{}' not in geopoints:
            marker = folium.Circle(radius=4)
            folium.GeoJson(geopoints,style_function=style_function_geojson,marker=marker).add_to(m)
            
        if not datalotes.empty:
            geojson = data2geopandas(datalotes,barmanpreref=code)
            popup   = folium.GeoJsonPopup(
                fields=["popup"],
                aliases=[""],
                localize=True,
                labels=True,
            )
            folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)
            
        with colm2:
            st.write('')
            titulo = 'Mapa de comparables'
            html   = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Título Centrado</title></head><body><section style="text-align: center;"><h1 style="color: #A16CFF; font-size: 20px; font-family: Arial, sans-serif;font-weight: bold;">{titulo}</h1><p style="font-size: 12px; color: #A16CFF;">(Haz click en los lotes)</p></section></body></html>"""
            texto  = BeautifulSoup(html, 'html.parser')
            st.markdown(texto, unsafe_allow_html=True)

            st_map = st_folium(m,width=mapw,height=maph)
        
        if '{}' not in geopoints:
            with colm2:
                st.image('https://iconsapp.nyc3.digitaloceanspaces.com/Lotes_con_transacciones_positivo.png',width=150)

    #-------------------------------------------------------------------------#
    # Graficas: Estadisticas
    #-------------------------------------------------------------------------#

        #---------------------------------------------------------------------#
        # Transacciones
    cols1,cols2 = st.columns(2,gap='large')
    if not datatransacciones.empty:
    
        df = datatransacciones.groupby('fecha_documento_publico').agg({'valormt2_transacciones':['count','median']}).reset_index()
        df.columns = ['fecha','count','value']
        df.index = range(len(df))
        if not df.empty:
            fig = px.bar(df, x="fecha", y="count", text="count", title='Número de transacciones')
            fig.update_traces(texttemplate='%{y:,.0f}', textposition='inside', marker_color='#68c8ed', textfont=dict(color='black'))
            fig.update_xaxes(tickmode='linear', dtick=1)
            fig.update_layout(title_x=0.3,height=350, xaxis_title=None, yaxis_title=None)
            fig.update_layout({
                'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                'title_font':dict(color='black'),
                'legend':dict(bgcolor='black'),
            })    
            fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
            fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
            with cols1:
                st.plotly_chart(fig, use_container_width=True,sharing="streamlit", theme="streamlit")
                
            fig = px.bar(df, x="fecha", y="value", text="value", title='Valor promedio de las transacciones por m²')
            fig.update_traces(texttemplate='$%{y:,.0f}', textposition='inside', marker_color='#68c8ed', textfont=dict(color='black'))
            fig.update_layout(title_x=0.3,height=350, xaxis_title=None, yaxis_title=None)
            fig.update_layout({
                'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                'title_font':dict(color='black'),
            })
            fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
            fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
            with cols2:
                st.plotly_chart(fig, use_container_width=True,sharing="streamlit", theme="streamlit")
        
        #---------------------------------------------------------------------#
        # Destino<>uso del suelo + Transacciones
    if not datacatastro.empty:
        df = datacatastro.groupby(tiposelected)['prechip'].count().reset_index()
        df.columns = ['variable','value']
        df.index = range(len(df))
        
        color_sequence = ["#66CCFF", "#99EEFF", "#FFEE99", "#FFCC66", "#FF9933"]
        if not df.empty:
            graphtit = f'Número de matrículas por {titulo}'
            color_sequence=px.colors.sequential.RdBu[::-1]
            # color_sequence=px.colors.sequential.Purples[::-1]
            fig      = px.pie(df,  values="value", names="variable", title=graphtit,color_discrete_sequence=color_sequence,height=500)
            fig.update_layout(title_x=0.3,height=350, xaxis_title=None, yaxis_title=None)
            fig.update_layout({
                'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                'title_font':dict(color='black'),
            })
            fig.update_traces(textinfo='percent+label', textfont_color='white',textposition='inside',)
            fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
            fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
            fig.update_layout(legend=dict(font=dict(color='black')))
            with cols1:
                st.plotly_chart(fig, use_container_width=True,sharing="streamlit", theme="streamlit")

    if not datatransacciones.empty:
        df         = datatransacciones.groupby(tiposelected).agg({'valormt2_transacciones':['median']}).reset_index()
        df.columns = ['variable','value']
        df         = df[(df['value']>0) & (df['value']<100000000)]
        df         = df.sort_values(by='value',ascending=True)
        df.index   = range(len(df))
        if not df.empty:
            graphtit = f'Transacciones por {titulo}'
            fig = px.bar(df, x="value", y="variable", text="value", title=graphtit,orientation='h')
            fig.update_traces(texttemplate='$%{x:,.0f}', textposition='inside', marker_color='#68c8ed', textfont=dict(color='black'))
            fig.update_layout(title_x=0.3,height=350, xaxis_title=None, yaxis_title=None)
            fig.update_layout({
                'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                'title_font':dict(color='black'),
            })
            fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
            fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
            with cols2:
                st.plotly_chart(fig, use_container_width=True,sharing="streamlit", theme="streamlit")

        #---------------------------------------------------------------------#
        # Avaluo catastral y predial
    if not datacatastro.empty:
    
        df = datacatastro.groupby(tiposelected).agg({'avaluomt2':['median']}).reset_index()
        df.columns = ['variable','value']
        df         = df[(df['value']>0) & (df['value']<100000000)]
        df         = df.sort_values(by='value',ascending=True)
        df.index   = range(len(df))
        if not df.empty:
            df  = df[df['value'].notnull()]
            fig = px.bar(df, x="value", y="variable", text="value", title='Avalúo catastral promedio por m²',orientation='h')
            fig.update_traces(texttemplate='$%{x:,.0f}', textposition='inside', marker_color='#68c8ed', textfont=dict(color='black'))
            fig.update_layout(title_x=0.3,height=350, xaxis_title=None, yaxis_title=None)
            fig.update_layout({
                'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                'title_font':dict(color='black'),
            })    
            fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
            fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
            with cols1:
                st.plotly_chart(fig, use_container_width=True,sharing="streamlit", theme="streamlit")
                
        df         = datacatastro.groupby(tiposelected).agg({'predialmt2':['median']}).reset_index()
        df.columns = ['variable','value']
        df         = df[(df['value']>0) & (df['value']<500000)]
        df         = df.sort_values(by='value',ascending=True)
        df.index   = range(len(df))
        if not df.empty:
            df  = df[df['value'].notnull()]
            fig = px.bar(df, x="value", y="variable", text="value", title='Predial promedio por m²',orientation='h')
            fig.update_traces(texttemplate='$%{x:,.0f}', textposition='inside', marker_color='#68c8ed', textfont=dict(color='black'))
            fig.update_layout(title_x=0.3,height=350, xaxis_title=None, yaxis_title=None)
            fig.update_layout({
                'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                'title_font':dict(color='black'),
            })    
            fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
            fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
            with cols2:
                st.plotly_chart(fig, use_container_width=True,sharing="streamlit", theme="streamlit")
                
        #---------------------------------------------------------------------#
        # Analisis demografico
    
    datacensodane = pd.DataFrame()
    if not datalotes.empty or not datacatastro.empty:
        with st.spinner('Buscando data demográfica'):
            datacensodane = censodane(str(polygon))
    if not datacensodane.empty:
        variables = [x for x in ['Total personas','Total viviendas','Hogares','Hombres','Mujeres'] if x in datacensodane]
        df = datacensodane[variables].copy()
        df = df.T.reset_index()
        df.columns = ['name','value']
        df.index = range(len(df))
        fig      = px.bar(df, x="name", y="value", text="value", title="Análisis Demográfico (censo del DANE)")
        fig.update_traces(texttemplate='%{y:,.0f}', textposition='inside', marker_color='#68c8ed', textfont=dict(color='black'))
        fig.update_xaxes(tickmode='linear', dtick=1)
        fig.update_layout(title_x=0.3,height=350, xaxis_title=None, yaxis_title=None)
        fig.update_layout({
            'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
            'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
            'title_font':dict(color='black'),
        })
        fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
        fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
        fig.update_yaxes(showgrid=False, zeroline=False)
        with cols1:
            st.plotly_chart(fig, use_container_width=True,sharing="streamlit", theme="streamlit")
        
        variables = [x for x in ['0 a 9 años', '10 a 19 años', '20 a 29 años', '30 a 39 años', '40 a 49 años', '50 a 59 años', '60 a 69 años', '70 a 79 años', '80 años o más'] if x in datacensodane]
        df = datacensodane[variables].copy()
        df = df.T.reset_index()
        df.columns = ['name','value']
        df.index = range(len(df))
        fig      = px.bar(df, x="name", y="value", text="value", title="Edades (censo del DANE)")
        fig.update_traces(texttemplate='%{y:,.0f}', textposition='inside', marker_color='#68c8ed', textfont=dict(color='black'))
        fig.update_xaxes(tickmode='linear', dtick=1)
        fig.update_layout(title_x=0.3,height=350, xaxis_title=None, yaxis_title=None)
        fig.update_layout({
            'plot_bgcolor': 'rgba(0, 0, 0, 0)',
            'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
            'title_font':dict(color='black'),
        })    
        fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
        fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
        with cols2:
            st.plotly_chart(fig, use_container_width=True,sharing="streamlit", theme="streamlit")
        
        #---------------------------------------------------------------------#
        # Tipologia de los inmuebles
    df  = pd.DataFrame()
    col = [cols1,cols2]
    s   = 0
    if not datacatastro.empty:
        formato = [{'variable':'preaconst','titulo':'Diferenciación por Área Privada'},
                   {'variable':'prevetustz','titulo':'Diferenciación por Antigüedad'},]
        for iiter in formato:
            variable = iiter['variable']
            titulo   = iiter['titulo']
            df         = datacatastro.copy()
            df         = df[df[variable]>0]
            
            if not df.empty:
                q1         = df.groupby(tiposelected)[variable].quantile(0.25).reset_index()
                q1.columns = [tiposelected,'q1']
                q3         = df.groupby(tiposelected)[variable].quantile(0.75).reset_index()
                q3.columns = [tiposelected,'q3']
                
                # Remover outliers
                w         = q1.merge(q3,on=tiposelected,how='outer')
                w['iqr']  = w['q3']-w['q1']
                w['linf'] = w['q1'] - 1.5*w['iqr']
                w['lsup'] = w['q3'] + 1.5*w['iqr']
                df        = df.merge(w[[tiposelected,'linf','lsup']],on=tiposelected,how='left',validate='m:1')
                df        = df[(df[variable]>=df['linf']) & (df[variable]<=df['lsup'])]
                
                w         = df.groupby(tiposelected)['prechip'].count().reset_index() 
                w.columns = [tiposelected,'count']
                df        = df.merge(w,on=tiposelected,how='left',validate='m:1')
                df        = df[df['count']>2]
        
            if not df.empty:
                fig = px.box(df,x=tiposelected,y=variable,title=titulo,color_discrete_sequence=['#68c8ed'])
                fig.update_layout(title_x=0.3,height=500, xaxis_title=None, yaxis_title=None)
                fig.update_layout({
                    'plot_bgcolor': 'rgba(0, 0, 0, 0)',
                    'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                    'title_font':dict(color='black'),
                })    
                fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                fig.update_traces(boxpoints=False)
                with col[s]:
                    st.plotly_chart(fig, use_container_width=True,sharing="streamlit", theme="streamlit")
                s+=1
    
        #---------------------------------------------------------------------#
        # Listings
    with st.spinner('Buscando data listings'):
        datalistingsactivos,datalistingshistoricos = listingsBypolygon(str(polygon),precuso=None)
    #datalistingshistoricos['fecha_inicial'] = datalistingshistoricos['fecha_inicial'].dt.strftime('%Y')
    #datalistingshistoricos = datalistingshistoricos[datalistingshistoricos['fecha_inicial']>'2022']
    col = [cols1,cols2]
    s   = 0
    if not datalistingsactivos.empty:
    
        df = datalistingsactivos.groupby(['tiponegocio','tipoinmueble']).agg({'valormt2':['count','median']}).reset_index()
        df.columns = ['tiponegocio','tipoinmueble','count','value']
        df.index = range(len(df))
        for tiponegocio in ['Venta','Arriendo']:
            dfiter = df[df['tiponegocio']==tiponegocio]
            dfiter = dfiter.sort_values(by='value',ascending=True)
            if not dfiter.empty:
                fig = px.bar(dfiter, x="value", y="tipoinmueble", text="value", title=f'Valor de {tiponegocio.lower()} por m² (listings activos)',orientation='h')
                fig.update_traces(texttemplate='$%{x:,.0f}', textposition='inside', marker_color='#68c8ed', textfont=dict(color='black'))
                fig.update_layout(title_x=0.3,height=350, xaxis_title=None, yaxis_title=None)
                fig.update_layout({
                    'plot_bgcolor': 'rgba(0, 0, 0, 0)',  
                    'paper_bgcolor': 'rgba(200, 200, 200, 0.1)',
                    'title_font':dict(color='black'),
                })    
                fig.update_xaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                fig.update_yaxes(showgrid=False, zeroline=False,tickfont=dict(color='black'))
                with col[s]:
                    st.plotly_chart(fig, use_container_width=True,sharing="streamlit", theme="streamlit")
                s +=1
                
                
@st.cache_data(show_spinner=False)
def builddata(polygon=None):
    
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        
    datacatastro               = pd.DataFrame()
    datatransacciones          = pd.DataFrame()
    dataprecuso,dataprecdestin = getuso_destino()
    dataprecuso.rename(columns={'codigo':'precuso','tipo':'usosuelo','descripcion':'desc_usosuelo'},inplace=True)
    dataprecdestin.rename(columns={'codigo':'precdestin','tipo':'destino','descripcion':'desc_destino'},inplace=True)

    if isinstance(polygon, str):
        datacatastro      = pd.read_sql_query(f"""SELECT barmanpre,precuso,precdestin,prechip,preaterre,preaconst,prevetustz FROM bigdata.data_bogota_catastro WHERE ST_CONTAINS(ST_GEOMFROMTEXT("{polygon}"), POINT(longitud, latitud))""" , engine)
        datatransacciones = getdataTransactions(polygon=polygon)
    
    if not datacatastro.empty:
        datacatastro = datacatastro.merge(dataprecuso,on='precuso',how='left',validate='m:1')
        datacatastro = datacatastro.merge(dataprecdestin,on='precdestin',how='left',validate='m:1')

    #-------------------------------------------------------------------------#
    # Transacciones
    if not datatransacciones.empty:
        datatransacciones['fecha_documento_publico_original'] = datatransacciones['fecha_documento_publico'].copy()
        datatransacciones['fecha_documento_publico'] = pd.to_datetime(datatransacciones['fecha_documento_publico'])
        datatransacciones['fecha_documento_publico'] = datatransacciones['fecha_documento_publico'].dt.strftime('%Y')
        datatransacciones = datatransacciones[datatransacciones['fecha_documento_publico']>'2018']
        datatransacciones = datatransacciones[datatransacciones['codigo'].isin(['125','126','168','169','0125','0126','0168','0169'])]
        
    if not datatransacciones.empty:
        datapaso          = datatransacciones.groupby(['docid']).agg({'cuantia':'max','preaconst':'max'}).reset_index()
        datapaso.columns  = ['docid','cuantia','areaconstruida']
        datapaso['valormt2_transacciones'] = datapaso['cuantia']/datapaso['areaconstruida']
        datapaso          = datapaso[ (datapaso['valormt2_transacciones']>100000) & (datapaso['valormt2_transacciones']<80000000)]
        datatransacciones = datatransacciones.merge(datapaso[['docid','valormt2_transacciones']],on='docid',how='left',validate='m:1')
        idd = (datatransacciones['valormt2_transacciones'].isnull()) & (datatransacciones['cuantia']>0) & (datatransacciones['preaconst']>0)
        if sum(idd)>0:
            datatransacciones.loc[idd,'valormt2_transacciones']  = datatransacciones.loc[idd,'cuantia'] /datatransacciones.loc[idd,'preaconst']
        datatransacciones = datatransacciones.merge(dataprecuso,on='precuso',how='left',validate='m:1')

        if not datacatastro.empty and 'destino' in datacatastro:
            datamerge         = datacatastro.drop_duplicates(subset=['prechip'],keep='first')
            datatransacciones = datatransacciones.merge(datamerge[['prechip','destino']],on='prechip',how='left',validate='m:1')

    #-------------------------------------------------------------------------#
    # Avaluo catastral
    if not datacatastro.empty:
        lista       = "','".join(datacatastro['prechip'].unique())
        query       = f" chip IN ('{lista}')"
        datapredial = pd.read_sql_query(f"SELECT chip,avaluo_catastral,impuesto_ajustado FROM  bigdata.data_bogota_shd_2024 WHERE {query}" , engine)
        
        if not datapredial.empty:
            datamerge    = datapredial.drop_duplicates(subset='chip')
            datamerge.rename(columns={'chip':'prechip'},inplace=True)
            datacatastro = datacatastro.merge(datamerge,on='prechip',how='left',validate='m:1')
            datacatastro['avaluomt2']  = datacatastro['avaluo_catastral']/datacatastro['preaconst']
            datacatastro['predialmt2'] = datacatastro['impuesto_ajustado']/datacatastro['preaconst']
            
    return datacatastro,datatransacciones
    
@st.cache_data(show_spinner=False)
def latlngFrombarmanpre(barmanpre):
    user     = st.secrets["user_bigdata"]
    password = st.secrets["password_bigdata"]
    host     = st.secrets["host_bigdata_lectura"]
    schema   = st.secrets["schema_bigdata"]
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    
    latitud  = None
    longitud = None
    precuso  = None
    
    if isinstance(barmanpre, str) and len(barmanpre)>10:
        datacatastro = pd.read_sql_query(f"SELECT latitud,longitud FROM  bigdata.data_bogota_catastro WHERE barmanpre='{barmanpre}' LIMIT 1" , engine)
        if not datacatastro.empty:
            latitud  = datacatastro['latitud'].iloc[0]
            longitud = datacatastro['longitud'].iloc[0]

        dataprecuso = pd.read_sql_query(f"SELECT precuso FROM  bigdata.bogota_catastro_compacta_precuso WHERE barmanpre='{barmanpre}'" , engine)
        if not dataprecuso.empty:
            precuso = list(dataprecuso['precuso'].unique())
            
    return latitud,longitud,precuso

@st.cache_data(show_spinner=False)
def data2geopandas(data,barmanpreref=None):
    
    urlexport = "http://www.urbex.com.co/Busqueda_avanzada"
    geojson   = pd.DataFrame().to_json()
    if 'wkt' in data: 
        data = data[data['wkt'].notnull()]
        
    lista = []
    if barmanpreref is not None and isinstance(barmanpreref,str) and barmanpreref!="":
        lista = barmanpreref.split('|')
        
    if not data.empty:
        data['geometry'] = gpd.GeoSeries.from_wkt(data['wkt'])
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['color']    = '#5A189A' #'#003F2D'
        data['popup']    = None
        data.index       = range(len(data))
        idd              = data['barmanpre'].isin(lista)
        if sum(idd)>0:
            data.loc[idd,'color'] ='#003F2D'
            
        for idd,items in data.iterrows():

            infoprecuso = ""
            urllink     = ""
            barmanpre   = items['barmanpre'] if 'barmanpre' in items and isinstance(items['barmanpre'], str) else None
            if barmanpre is not None:
                urllink = urlexport+f"?type=predio&code={barmanpre}&vartype=barmanpre&token={st.session_state.token}"

            if 'infoByprecuso' in items: 
                itemsu      = items['infoByprecuso'][0]
                infoprecuso = ""
                try:    infoprecuso += f"""<b> Dirección:</b> {itemsu['formato_direccion']}<br>"""
                except: pass
                try:    infoprecuso += f"""<b> Barrio:</b> {itemsu['prenbarrio']}<br>  """
                except: pass
                try:    infoprecuso += f"""<b> Área construida total:</b> {round(itemsu['preaconst_total'],2)}<br>"""
                except: pass
                try:    infoprecuso += f"""<b> Área de terreno:</b> {round(itemsu['preaterre_total'],2)}<br> """
                except: pass
                try:    infoprecuso += f"""<b> Estrato:</b> {int(itemsu['estrato'])}<br> """
                except: pass
                try:    infoprecuso += f"""<b> Pisos:</b> {int(itemsu['connpisos'])}<br> """
                except: pass
                try:    infoprecuso += f"""<b> Antiguedad:</b> {int(itemsu['prevetustzmin'])}<br>"""
                except: pass            
                try:    infoprecuso += f"""<b> Total de matriculas:</b> {int(itemsu['predios_total'])}<br> """
                except: pass                    

                for witer in items['infoByprecuso']:
                    hmtl_paso = ""
                    if witer['usosuelo'] is not None and not pd.isnull(witer['usosuelo']):
                        hmtl_paso += f"<b> Uso del suelo:</b> {witer['usosuelo']}<br>"
                    if witer['predios_precuso'] is not None and not pd.isnull(witer['predios_precuso']):
                        hmtl_paso += f"<b> Predios:</b> {witer['predios_precuso']}<br> "
                    
                    if hmtl_paso!="":
                        infoprecuso += f"""
                        <b><br>
                        {hmtl_paso}
                        """
                    try:
                        infoprecuso += f"""
                        <b> Área: </b>{witer['preaconst_precuso']/witer['preaconst_total']:,.1%}<br>
                        """
                    except: pass
            
            popup_content =  f'''
            <!DOCTYPE html>
            <html>
                <body>
                    <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;font-size: 12px;">
                        <a href="{urllink}" target="_blank" style="color: black;">
                            {infoprecuso}
                        </a>
                    </div>
                </body>
            </html>
            '''
            data.loc[idd,'popup'] = popup_content
        geojson = data.to_json()
    return geojson

    
@st.cache_data(show_spinner=False)
def TransactionMarker(datatransacciones,datacatastro,datalotes):

    geojson = pd.DataFrame().to_json()
    if not datalotes.empty and 'wkt' in datalotes:
        datacatastro          = datacatastro[datacatastro['prechip'].isin(datatransacciones['prechip'])]
        datalotes             = datalotes[datalotes['barmanpre'].isin(datacatastro['barmanpre'])]
        datalotes['latitud']  = datalotes['wkt'].apply(lambda x: wkt.loads(x).centroid.y)
        datalotes['longitud'] = datalotes['wkt'].apply(lambda x: wkt.loads(x).centroid.x)
        datalotes             = datalotes.drop_duplicates(subset='barmanpre',keep='first')
    
    if not datalotes.empty and 'latitud' in datalotes and 'longitud' in datalotes:
        datalotes = datalotes[(datalotes['latitud'].notnull()) & (datalotes['longitud'].notnull())]
    if not datalotes.empty:
        datalotes['geometry'] = datalotes.apply(lambda x: Point(x['longitud'],x['latitud']),axis=1)
        datalotes             = gpd.GeoDataFrame(datalotes, geometry='geometry')
        datalotes             = datalotes[['geometry']]
        datalotes['color']    = 'blue'
        geojson               = datalotes.to_json()

    return geojson

def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }
