import streamlit as st
import folium
import pandas as pd
import geopandas as gpd
import random
from streamlit_folium import st_folium,folium_static
from folium.plugins import Draw
from shapely.geometry import Polygon,Point,mapping,shape
from streamlit_js_eval import streamlit_js_eval
from datetime import datetime

from display.stylefunctions  import style_function,style_function_geojson

from data._principal_listings import data_listings_polygon as datalistings

def main(screensize=1920):

    try:    mapwidth = int(screensize)
    except: mapwidth = 1920

    #-------------------------------------------------------------------------#
    # Variables 
    formato = {
               'polygon_mls':None,
               'data_mls':pd.DataFrame(),
               'zoom_start_mls':12,
               'latitud_mls':4.652652, 
               'longitud_mls':-74.077899,
               'reporte_mls':False,          

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
    col1,col2,col3 = st.columns([1,1,3])
    
    tipoinmueble    = None
    tiponegocio     = None
    areamin         = 0
    areamax         = 0
    valormin        = 0
    valormax        = 0
    habitacionesmin = 0
    habitacionesmax = 0
    banosmin        = 0
    banosmax        = 0
    garajesmin      = 0
    garajesmax      = 0

    with col1:
        tipoinmueble = st.selectbox('Tipo de inmueble', options=['Apartamento', 'Bodega', 'Casa', 'Consultorio', 'Edificio', 'Hotel', 'Local', 'Oficina'])
    with col2:
        tiponegocio = st.selectbox('Tipo de negocio',options=['Venta', 'Arriendo'])
    with col1:
        areamin = st.number_input('Área mínima',value=0,min_value=0)
    with col2:
        areamax = st.number_input('Área máxima',value=0,min_value=0)
    with col1:
        valormin = st.number_input('Valor mínimo',value=0,min_value=0)
    with col2:
        valormax = st.number_input('Valor máximo',value=0,min_value=0)
            
    habitacionesmin,habitacionesmax,banosmin,banosmax,garajesmin,garajesmax = [0]*6
        
    if any([x for x in ['Apartamento','Casa'] if x in tipoinmueble]):
        with col1:
            habitacionesmin = st.selectbox('Habitaciones mínimas',options=[1,2,3,4,5,6],index=0)
        with col2:
            habitacionesmax = st.selectbox('Habitaciones máximas',options=[1,2,3,4,5,6],index=5)
        with col1:
            banosmin = st.selectbox('Baños mínimos',options=[1,2,3,4,5,6],index=0)
        with col2:
            banosmax = st.selectbox('Baños máximos',options=[1,2,3,4,5,6],index=5)       
        with col1:
            garajesmin = st.selectbox('Garajes mínimos',options=[0,1,2,3,4],index=0)
        with col2:
            garajesmax = st.selectbox('Garajes máximos',options=[0,1,2,3,4,5,6],index=6)

    #-------------------------------------------------------------------------#
    # Mapa
    with col3:
        
        m  = folium.Map(location=[st.session_state.latitud_mls, st.session_state.longitud_mls], zoom_start=st.session_state.zoom_start_mls,tiles="cartodbpositron")
        
        if st.session_state.data_mls.empty:
            draw = Draw(
                        draw_options={"polyline": False,"marker": False,"circlemarker":False,"rectangle":False,"circle":False},
                        edit_options={"poly": {"allowIntersection": False}}
                        )
            draw.add_to(m)
        
        if st.session_state.polygon_mls is not None:
            folium.GeoJson(mapping(st.session_state.polygon_mls), style_function=style_function).add_to(m)
    
        if not st.session_state.data_mls.empty:
            geojson = data2geopandas(st.session_state.data_mls,tiponegocio=tiponegocio)
            popup   = folium.GeoJsonPopup(
                fields=["popup"],
                aliases=[""],
                localize=True,
                labels=True,
            )
            folium.GeoJson(geojson,style_function=style_function_geojson,popup=popup).add_to(m)
        
        if st.session_state.data_mls.empty:
        
            st_map = st_folium(m,width=int(mapwidth*0.6),height=600)
    
            polygonType = ''
            if 'all_drawings' in st_map and st_map['all_drawings'] is not None:
                if st_map['all_drawings']!=[]:
                    if 'geometry' in st_map['all_drawings'][0] and 'type' in st_map['all_drawings'][0]['geometry']:
                        polygonType = st_map['all_drawings'][0]['geometry']['type']
                
            if 'polygon' in polygonType.lower():
                coordenadas                     = st_map['all_drawings'][0]['geometry']['coordinates']
                st.session_state.polygon_mls    = Polygon(coordenadas[0])
                geojson_data_mls                = mapping(st.session_state.polygon_mls)
                polygon_shape                   = shape(geojson_data_mls)
                centroid                        = polygon_shape.centroid
                st.session_state.latitud_mls    = centroid.y
                st.session_state.longitud_mls   = centroid.x
                st.session_state.zoom_start_mls = 16
                st.rerun()
                
        if not st.session_state.data_mls.empty:
            folium_static(m,width=int(mapwidth*0.6),height=600)
    
        if st.session_state.polygon_mls is not None:        
            with col2:
                if st.button('Buscar'):
                    inputvar = {
                        'tipoinmueble':[tipoinmueble],
                        'tiponegocio':[tiponegocio],
                        'areamin': areamin,
                        'areamax': areamax,
                        'valormin': valormin,
                        'valormax': valormax,
                        'habitacionesmin': habitacionesmin,
                        'habitacionesmax': habitacionesmax,
                        'banosmin': banosmin,
                        'banosmax': banosmax,
                        'garajesmin': garajesmin,
                        'garajesmax': garajesmax,
                        }
                    st.session_state.data_mls = datalistings(polygon=str(st.session_state.polygon_mls),inputvar=inputvar)
                    st.session_state.reporte_mls = True
                    st.rerun()
    
            with col1:
                if st.button('Resetear búsqueda'):
                    for key,value in formato.items():
                        del st.session_state[key]
                    st.rerun()
                
        
    if st.session_state.reporte_mls:
        showlistings(st.session_state.data_mls)


def style_function_color(feature):
    return {
        'fillColor': '#828DEE',
        'color':'#828DEE',
        'weight': 1,
    }

@st.cache_data(show_spinner=False)
def data2geopandas(data,tiponegocio=None):
    
    urlexport = "http://www.urbex.com.co/Ficha"
    geojson   = pd.DataFrame().to_json()
    if 'latitud' in data and 'longitud' in data:
        data = data[(data['latitud'].notnull()) & (data['longitud'].notnull())]
    if not data.empty:
        data['geometry'] = data.apply(lambda x: Point(x['longitud'],x['latitud']),axis=1)
        data             = gpd.GeoDataFrame(data, geometry='geometry')
        data['popup']    = ''
        img_style = '''
                <style>               
                    .property-image{
                      flex: 1;
                    }
                    img{
                        width:200px;
                        height:120px;
                        object-fit: cover;
                        margin-bottom: 2px; 
                    }
                </style>
                '''
        for idd,items in data.iterrows():
            urllink = urlexport+f"?code={items['code']}&tiponegocio={items['tiponegocio'].lower()}&tipoinmueble={items['tipoinmueble'].lower()}"
    
            imagen_principal = items['url_img'].split('|')[0].strip() if 'url_img' in items and isinstance(items['url_img'], str) else "https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png"
            precio           = f"<b> Precio:</b> ${items['valor']:,.0f}<br>" if 'valor' in items and (isinstance(items['valor'], float) or isinstance(items['valor'], int)) else ''
            direccion        = f"<b> Dirección:</b> {items['direccion']}<br>" if 'direccion' in items and isinstance(items['direccion'], str) else ''
            valormt2         = f"<b> Valor m²:</b> ${items['valormt2']:,.0f} m²<br>" if 'valormt2' in items and (isinstance(items['valormt2'], float) or isinstance(items['valormt2'], int)) else ''
            tiponegocio      = f"<b> Tipo de negocio:</b> {items['tiponegocio']}<br>" if 'tiponegocio' in items and isinstance(items['tiponegocio'], str) else ''
            tipoinmueble     = items['tipoinmueble'] if 'tipoinmueble' in items and isinstance(items['tipoinmueble'], str) else None
            caracteristicas  = f"<b> Área construida:</b> {items['areaconstruida']}<br>" if 'areaconstruida' in items and (isinstance(items['areaconstruida'], float) or isinstance(items['areaconstruida'], int)) else ''
            barrio           = f"<b> Barrio:</b> {items['scanombre']}<br>"  if 'scanombre' in items and isinstance(items['scanombre'], str) else ''
            
            if any([x for x in ['apartamento','casa'] if x in tipoinmueble.lower()]):
                if all([x for x in ['habitaciones','banos','garajes'] if x in items]):
                    try:    caracteristicas = f"{items['areaconstruida']} m<sup>2</sup> | {int(float(items['habitaciones']))} H | {int(float(items['banos']))} B | {int(float(items['garajes']))} G <br>"
                    except: caracteristicas = "" 
            tipoinmueble = f"<b> Tipo de inmueble:</b> {items['tipoinmueble']}<br>" if 'tipoinmueble' in items and isinstance(items['tipoinmueble'], str) else ''

            popup_content = f'''
            <!DOCTYPE html>
            <html>
              <head>
                {img_style}
              </head>
              <body>
                <div id="popupContent" style="cursor:pointer; display: flex; flex-direction: column; flex: 1;width:200px;">
                    <a href="{urllink}" target="_blank" style="color: black;">
                        <div class="property-image">
                          <img src="{imagen_principal}"  alt="property image" onerror="this.src='https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png';">
                        </div>
                        {tiponegocio}
                        {tipoinmueble}
                        {precio}
                        {valormt2}
                        {caracteristicas}
                        {direccion}
                        {barrio}
                    </a>
                </div>
              </body>
            </html>
            '''
            data.loc[idd,'popup'] = popup_content
            
        data          = data[['popup','geometry']]
        data['color'] = 'blue'
        geojson       = data.to_json()
    return geojson


@st.cache_data(show_spinner=False)
def showlistings(data_listings):
    #-------------------------------------------------------------------------#
    # Listings 
    #-------------------------------------------------------------------------#
    listings_html = ""
    if not data_listings.empty:
        listings_html += '''
        <div class="urbex-container">
            <div class="urbex-row urbex-p-5" id="listings-container">
        '''
        
        # Generar todos los listings pero inicialmente ocultos
        for idx, items in data_listings.iterrows():
            urllink = f"http://www.urbex.com.co/Ficha?code={items['code']}&tiponegocio={items['tiponegocio'].lower()}&tipoinmueble={items['tipoinmueble'].lower()}"
            imagen_principal = items['url_img'].split('|')[0].strip() if 'url_img' in items and isinstance(items['url_img'], str) else "https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png"
            
            listings_html += f'''
            <div class="listing-item urbex-col-12 urbex-col-md-4 urbex-p-2" data-index="{idx}">
                <div class="urbex-h-100 urbex-d-flex urbex-flex-column urbex-p-3" id="box_shadow">
                    <a href="{urllink}" target="_blank">
                        <img src="{imagen_principal}" alt="property image" style="height: 250px;width: 100%;margin-bottom: 10px;"
                             onerror="this.src='https://personal-data-bucket-online.s3.us-east-2.amazonaws.com/sin_imagen.png';">
                    </a>
                    <div class="urbex-table-responsive urbex-flex-grow-1" style="line-height: 0.4;font-size: 14px;">
                        <table class="urbex-table urbex-table-borderless">
                            <tbody>
            '''
            
            if 'valor' in items and (isinstance(items['valor'], float) or isinstance(items['valor'], int)):
                listings_html += f'''
                <tr>
                    <td id="firstcoltable-1"><span id="label_inside_listing">Precio:</span></td>
                    <td><span id="value_inside_listing">${items['valor']:,.0f}</span></td>
                </tr>
                '''
            if 'valormt2' in items and (isinstance(items['valormt2'], float) or isinstance(items['valormt2'], int)):
                listings_html += f'''
                <tr>
                    <td id="firstcoltable-1"><span id="label_inside_listing">Valor m²:</span></td>
                    <td><span id="value_inside_listing">${items['valormt2']:,.0f} m²</span></td>
                </tr>
                '''
            if 'direccion' in items and isinstance(items['direccion'], str):
                listings_html += f'''
                <tr>
                    <td id="firstcoltable-1"><span id="label_inside_listing">Dirección:</span></td>
                    <td><span id="value_inside_listing">{items['direccion']}</span></td>
                </tr>
                '''
            if 'tiponegocio' in items and isinstance(items['tiponegocio'], str):
                listings_html += f'''
                <tr>
                    <td id="firstcoltable-1"><span id="label_inside_listing">Tipo de negocio:</span></td>
                    <td><span id="value_inside_listing">{items['tiponegocio']}</span></td>
                </tr>
                '''
            if 'tipoinmueble' in items and isinstance(items['tipoinmueble'], str):
                listings_html += f'''
                <tr>
                    <td id="firstcoltable-1"><span id="label_inside_listing">Tipo de inmueble:</span></td>
                    <td><span id="value_inside_listing">{items['tipoinmueble']}</span></td>
                </tr>
                '''
            
            if 'tipoinmueble' in items and isinstance(items['tipoinmueble'], str):
                tipoinmueble = items['tipoinmueble'].lower()
                if any(x in tipoinmueble for x in ['apartamento', 'casa']):
                    if all(x in items for x in ['habitaciones', 'banos', 'garajes', 'areaconstruida']):
                        try:
                            listings_html += f'''
                            <tr>
                                <td id="firstcoltable-1"><span id="label_inside_listing">Características:</span></td>
                                <td><span id="value_inside_listing">{items['areaconstruida']} m² | {int(float(items['habitaciones']))} H | {int(float(items['banos']))} B | {int(float(items['garajes']))} G</span></td>
                            </tr>
                            '''
                        except:
                            pass
            
            listings_html += '''
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            '''
        
        listings_html += '''
            </div>
        </div>
        '''
        
    #-------------------------------------------------------------------------#
    # CSS y HTML final con JavaScript para paginación
    #-------------------------------------------------------------------------#
    css = '''
    <link href="https://iconsapp.nyc3.digitaloceanspaces.com/estilo_detalle_predio/prefixed_bootstrap.min.css" rel="stylesheet"/>
    <link href="https://iconsapp.nyc3.digitaloceanspaces.com/estilo_detalle_predio/prefixed_styles.css" rel="stylesheet"/>
    <style>
        .urbex-table th, .urbex-table td {
            white-space: nowrap;
            min-width: fit-content;
            padding: 0.5rem !important;
        }
        
        .urbex-table-wrapper {
            overflow-x: auto;
            width: 100%;
        }

        .urbex-table thead {
            position: sticky;
            top: 0;
            z-index: 1;
        }
        
        /* Estilos para paginación */
        .pagination-controls {
            background-color: #f8f9fa;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .pagination-btn {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        
        .pagination-btn:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
        }
        
        .pagination-btn:hover:not(:disabled) {
            background-color: #0056b3;
        }
        
        #pagination-info {
            color: #666;
            font-size: 0.9rem;
        }
        
        .listing-item {
            display: none;
        }
        
        .listing-item.active {
            display: block;
        }
        
        #page-numbers {
            font-weight: bold;
            color: #333;
        }
    </style>
    '''

    javascript = '''
    <script>
    const ITEMS_PER_PAGE = 50;
    let currentPage = 1;
    let totalItems = 0;
    let totalPages = 1;
    let currentItems = [];
    
    // Función para ordenar los items
    function sortItems(criteria) {
        const items = Array.from(document.querySelectorAll('.listing-item'));
        
        items.sort((a, b) => {
            switch(criteria) {
                case 'precio-desc':
                    const precioA = parseFloat(a.querySelector('[id="value_inside_listing"]').textContent.replace('$', '').replace(/,/g, ''));
                    const precioB = parseFloat(b.querySelector('[id="value_inside_listing"]').textContent.replace('$', '').replace(/,/g, ''));
                    return precioB - precioA;
                case 'area-desc':
                    const areaA = parseFloat(a.querySelector('[id="value_inside_listing"]').textContent.split('|')[0].trim().split(' ')[0]);
                    const areaB = parseFloat(b.querySelector('[id="value_inside_listing"]').textContent.split('|')[0].trim().split(' ')[0]);
                    return areaB - areaA;
                case 'habitaciones-desc':
                    const habA = parseInt(a.querySelector('[id="value_inside_listing"]').textContent.split('|')[1].trim().split(' ')[0]);
                    const habB = parseInt(b.querySelector('[id="value_inside_listing"]').textContent.split('|')[1].trim().split(' ')[0]);
                    return habB - habA;
                default:
                    return 0;
            }
        });
    
        const container = document.getElementById('listings-container');
        items.forEach(item => container.appendChild(item));
        currentItems = items;
        showPage(1);
    }
    
    function createPaginationControls(isTop) {
        const controls = document.createElement('div');
        controls.className = 'pagination-controls urbex-p-3';
        controls.innerHTML = `
            <div class="urbex-row align-items-center">
                <div class="urbex-col-md-3">
                    <span id="pagination-info-${isTop ? 'top' : 'bottom'}"></span>
                </div>
                <div class="urbex-col-md-6">
                    <div class="sorting-controls text-center">
                        <select class="sort-select" onchange="sortItems(this.value)">
                            <option value="">Ordenar por...</option>
                            <option value="precio-desc">Mayor Precio</option>
                            <option value="area-desc">Mayor Área</option>
                            <option value="habitaciones-desc">Más Habitaciones</option>
                        </select>
                    </div>
                </div>
                <div class="urbex-col-md-3 text-end">
                    <button onclick="previousPage()" class="pagination-btn" id="btn-prev-${isTop ? 'top' : 'bottom'}">Anterior</button>
                    <span id="page-numbers" class="mx-3">
                        Página <span id="current-page-${isTop ? 'top' : 'bottom'}">1</span> de <span id="total-pages-${isTop ? 'top' : 'bottom'}">1</span>
                    </span>
                    <button onclick="nextPage()" class="pagination-btn" id="btn-next-${isTop ? 'top' : 'bottom'}">Siguiente</button>
                </div>
            </div>
        `;
        return controls;
    }
    
    function initPagination() {
        const items = document.querySelectorAll('.listing-item');
        currentItems = Array.from(items);
        totalItems = items.length;
        totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE);
        
        // Agregar controles de paginación superior
        const container = document.querySelector('.urbex-container');
        const topControls = createPaginationControls(true);
        container.insertBefore(topControls, container.firstChild);
        
        // Agregar controles de paginación inferior
        const bottomControls = createPaginationControls(false);
        container.appendChild(bottomControls);
        
        // Actualizar información de la paginación
        updatePaginationInfo();
        
        // Mostrar primera página
        showPage(1);
    }
    
    function showPage(pageNum) {
        const startIndex = (pageNum - 1) * ITEMS_PER_PAGE;
        const endIndex = Math.min(startIndex + ITEMS_PER_PAGE, totalItems);
        
        // Ocultar todos los items
        currentItems.forEach(item => {
            item.classList.remove('active');
        });
        
        // Mostrar items de la página actual
        for (let i = startIndex; i < endIndex; i++) {
            currentItems[i].classList.add('active');
        }
        
        // Actualizar controles
        currentPage = pageNum;
        updatePaginationInfo();
        
        // Actualizar estado de los botones
        ['top', 'bottom'].forEach(position => {
            document.getElementById(`current-page-${position}`).textContent = currentPage;
            document.getElementById(`total-pages-${position}`).textContent = totalPages;
            document.getElementById(`btn-prev-${position}`).disabled = currentPage === 1;
            document.getElementById(`btn-next-${position}`).disabled = currentPage === totalPages;
        });
    
        // Hacer scroll suave al inicio de la página
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    
    function updatePaginationInfo() {
        const startIndex = ((currentPage - 1) * ITEMS_PER_PAGE) + 1;
        const endIndex = Math.min(currentPage * ITEMS_PER_PAGE, totalItems);
        
        ['top', 'bottom'].forEach(position => {
            document.getElementById(`pagination-info-${position}`).textContent = 
                `Mostrando ${startIndex}-${endIndex} de ${totalItems} propiedades`;
        });
    }
    
    function previousPage() {
        if (currentPage > 1) {
            showPage(currentPage - 1);
        }
    }
    
    function nextPage() {
        if (currentPage < totalPages) {
            showPage(currentPage + 1);
        }
    }
    
    // Inicializar paginación cuando el documento esté cargado
    document.addEventListener('DOMContentLoaded', initPagination);
    </script>
    '''

    html_content = f'''
    <!DOCTYPE html>
    <html data-bs-theme="light" lang="en">
    <head>
        <meta charset="utf-8"/>
        <meta content="width=device-width, initial-scale=1.0, shrink-to-fit=no" name="viewport"/>
        <title>Listings</title>
        {css}
    </head>
    <body>
        {listings_html}
        <script src="https://iconsapp.nyc3.digitaloceanspaces.com/estilo_detalle_predio/bootstrap.min.js"></script>
        {javascript}
    </body>
    </html>
    '''
    st.components.v1.html(html_content, height=5000, scrolling=True)      

    return html_content
