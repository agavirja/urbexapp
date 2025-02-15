import streamlit as st
import geopandas as gpd
import pandas as pd
import geojson
import numpy as np
from itertools import product
from shapely.affinity import translate
from shapely.affinity import rotate
from shapely.geometry import MultiPolygon,Polygon
from shapely import wkt
from pyproj import CRS
from shapely.ops import unary_union
from shapely.affinity import scale
from area import area as areapolygon

from functions.circle_polygon import circle_polygon
from data._principal_vias_anden import main as get_vias_andenes
from data._principal_lotes import datalote

crs = CRS.from_epsg(4326)

@st.cache_data(show_spinner=False)
def main(grupo=None, aislamiento_frontal=0, aislamiento_posterior=0, aislamiento_lateral=0, reduccion_poligono=0):

    data_lote     = datalote(grupo)
    poligono_lote = None
    
    if not data_lote.empty and 'wkt' in data_lote:
        data_lote['geometry'] = gpd.GeoSeries.from_wkt(data_lote['wkt'])
    
    if len(data_lote)>1:
        data_lote['geometry'] = data_lote['geometry'].apply(lambda x: x.buffer(0.00000001))
        polygon_ref           = data_lote['geometry'].to_list()
        polygon_ref           = unary_union(polygon_ref)
        if isinstance(polygon_ref,MultiPolygon):
            df            = gpd.GeoDataFrame(geometry=[polygon_ref])
            df            = df.explode()
            df['area']    = df['geometry'].apply(lambda x: getareapolygon(x))
            df            = df.sort_values(by='area',ascending=False)
            poligono_lote = df['geometry'].iloc[0]
            
        elif isinstance(polygon_ref,Polygon):
            poligono_lote = polygon_ref
            
    else: 
        poligono_lote = data_lote['geometry'].iloc[0]
        

    #-----------------------------------------------------------------------------#
    # 2. Vias y andenes 
    data_andenes,data_vias,dataunion,esquinero = get_vias_andenes(poligono_lote.wkt)

    #-----------------------------------------------------------------------------#
    # 3. Grid
    pgrid         = _grid(poligono_lote.wkt, target_area=1)
    pgrid         = transform_fila_column(pgrid, column_name='fila')
    pgrid         = transform_fila_column(pgrid, column_name='col')
    pgridoriginal = pgrid.copy()
    
    #-----------------------------------------------------------------------------#
    # 4. Grid de borde
    pborder  = getBorderGrid(pgrid)
    areagrid = getareapolygon(pgrid['geometry'].iloc[0])
    
    #-----------------------------------------------------------------------------#
    # 5. Reduccion de lote (si aplica)
    if reduccion_poligono>0 and reduccion_poligono<1:
        
        aislamiento_frontal   = 0
        aislamiento_posterior = 0
        aislamiento_lateral   = 0
            
        areainicial = getareapolygon(poligono_lote)
        datapaso    = pgrid.copy()
        success     = False
        maxcount    = 20
        conteo      = 0
        terminado   = 0
        while terminado==0:
            conteo += 1
            pborderpaso          = getBorderGrid(datapaso)
            idd                  = datapaso['id'].isin(pborderpaso['id'])
            datapaso             = datapaso[~idd]
            datapaso['geometry'] = datapaso['geometry'].apply(lambda x: x.buffer(0.00000001))
            polygon_ref          = datapaso['geometry'].to_list()
            polygon_ref          = unary_union(polygon_ref)
            areanueva            = getareapolygon(polygon_ref)
            
            if areanueva/areainicial<=reduccion_poligono and terminado==0:
                pgrid     = datapaso.copy()
                terminado = 1
                success   = True    
            if conteo>maxcount:
                terminado = 1
        if not success:
            polygon_analisis = scale(poligono_lote, xfact=reduccion_poligono, yfact=reduccion_poligono, origin=(poligono_lote.centroid.x, poligono_lote.centroid.y))
            pgrid            = _grid(polygon_analisis.wkt, target_area=1)
            pgrid            = transform_fila_column(pgrid, column_name='fila')
            pgrid            = transform_fila_column(pgrid, column_name='col')
            areagrid         = getareapolygon(pgrid['geometry'].iloc[0])


    #-----------------------------------------------------------------------------#
    # 6. Colindan con via / anden [antejardin]
    dataradio             = pborder.copy()
    dataradio['latitud']  = dataradio['geometry'].apply(lambda x: x.centroid.y)
    dataradio['longitud'] = dataradio['geometry'].apply(lambda x: x.centroid.x)
    
    result       = pd.DataFrame()
    initialradio = 1
    terminado    = 0
    while terminado==0:
        initialradio         += 0.5
        dataradio['geometry'] = dataradio.apply(lambda x: circle_polygon(np.sqrt(areagrid)*initialradio,x['latitud'],x['longitud']),axis=1)
        dataradio             = gpd.GeoDataFrame(dataradio, geometry='geometry')
        result                = gpd.sjoin(dataunion, dataradio, how='inner')
        panden                = pborder[pborder['id'].isin(result['id'])]
        if not panden.empty or initialradio>=10: 
            terminado = 1

    #-----------------------------------------------------------------------------#
    # 7. Columnas y filas que colindan con calle
    if not result.empty and 'calancho' in result and 'fila' in result and 'col' in result:
        
        df1         = result.groupby(['fila','calancho'])['id'].count().reset_index()
        df1.columns = ['identificador','calancho','conteo']
        df1['tipo'] = 'fila'
        df2         = result.groupby(['col','calancho'])['id'].count().reset_index()
        df2.columns = ['identificador','calancho','conteo']
        df2['tipo'] = 'col'
        df          = pd.concat([df1,df2])
        df          = df[df['conteo']>2]

    #-----------------------------------------------------------------------------#
    # 8. Aislamiento laterales
    pborder.index = range(len(pborder))
    signofun      = lambda x: (x > 0) - (x < 0)

    if aislamiento_lateral>0:
        conteo    = 0
        terminado = 0
        datatotal = pborder.copy()
        signofun                = lambda x: (x > 0) - (x < 0)
        datatotal['signo_fila'] = datatotal['fila'].apply(lambda x: signofun(x))
        datatotal['signo_col']  = datatotal['col'].apply(lambda x: signofun(x))
        datatotal['fila']       = datatotal['fila'].apply(lambda x: abs(x))
        datatotal['col']        = datatotal['col'].apply(lambda x: abs(x))
        
        dataresult = datatotal.copy()
        while terminado==0:
            conteo += 1
            
            if conteo>=aislamiento_lateral:
                terminado = 1
                
            else:
                datapaso         = datatotal.copy()
                datapaso['fila'] = datapaso['fila']+conteo
                dataresult       = pd.concat([dataresult,datapaso])
                
                datapaso         = datatotal.copy()
                datapaso['col']  = datapaso['col']+conteo
                dataresult       = pd.concat([dataresult,datapaso])

        if not dataresult.empty:
            dataresult['fila'] = dataresult['fila']*dataresult['signo_fila'] 
            dataresult['col']  = dataresult['col']*dataresult['signo_col'] 
            dataresult         = dataresult[['fila','col']]
            dataresult         = dataresult.drop_duplicates()
            dataresult['asilamiento'] = 1
        
            pgrid = pgrid.merge(dataresult,on=['fila','col'],how='left',validate='m:1')
            idd   = pgrid['asilamiento']==1
            pgrid = pgrid[~idd]

    #-----------------------------------------------------------------------------#
    # 9. Remover aislamiento frontal [antejardin]
    if aislamiento_frontal>0:
        
        for _,j in df.iterrows():
            
            tipo          = j['tipo']
            identificador = j['identificador']
            signofun      = lambda x: (x > 0) - (x < 0)
            signo         = signofun(identificador)
            
            conteo    = 0
            terminado = 0
            while terminado==0:
                pgrid.index = range(len(pgrid))
                idd = pgrid.index>=0
                if signo>0:
                    idd = pgrid[tipo]==identificador+conteo
                elif signo<0:
                    idd = pgrid[tipo]==identificador-conteo
                    
                pgrid   = pgrid[~idd]
                conteo += 1
                if conteo>=aislamiento_frontal:
                    terminado = 1

    #-----------------------------------------------------------------------------#
    # 10. Remover aislamiento posterior [No esquineros]
    if not esquinero and aislamiento_posterior>0: 
        
        for _,j in df.iterrows():
            
            tipo          = j['tipo']
            identificador = j['identificador']*(-1)
            signofun      = lambda x: (x > 0) - (x < 0)
            signo         = signofun(identificador)
            
            if signo<0:   identificador = -1
            elif signo>0: identificador = 1
     
            conteo    = 0
            terminado = 0
            while terminado==0:
                pgrid.index = range(len(pgrid))
                idd = pgrid.index>=0
                if signo>0:
                    idd = pgrid[tipo]==identificador+conteo
                elif signo<0:
                    idd = pgrid[tipo]==identificador-conteo
                    
                pgrid   = pgrid[~idd]
                conteo += 1
                if conteo>=aislamiento_posterior:
                    terminado = 1
            
    return poligono_lote, pgridoriginal, pgrid, pborder, data_andenes, data_vias, dataunion, esquinero

#-----------------------------------------------------------------------------#
# GRID
#-----------------------------------------------------------------------------#
@st.cache_data(show_spinner=False)
def _grid(poligono_lote, target_area=1):
    
    poligono_lote = wkt.loads(poligono_lote)

    # Calcular la inclinación
    rotating_rectangle = poligono_lote.minimum_rotated_rectangle
    coords             = list(rotating_rectangle.exterior.coords)
    dx                 = coords[1][0] - coords[0][0]
    dy                 = coords[1][1] - coords[0][1]
    inclinacion_actual = np.degrees(np.arctan2(dy, dx))

    # Información del polígono original
    gdf = gpd.GeoDataFrame(geometry=[poligono_lote])
    minx, miny, maxx, maxy = gdf.total_bounds
    
    # Parámetros de la cuadrícula
    #cell_size = 0.005/1000  # Ajusta según necesidad
    
    cell_size = find_cell_size(minx, miny, target_area=target_area)
    cols      = int((maxx - minx) / cell_size) + 1
    rows      = int((maxy - miny) / cell_size) + 1
    centroid  = poligono_lote.centroid
    
    # Algoritmo
    result_grid          = gpd.GeoDataFrame()
    reference_grid       = gpd.GeoDataFrame()
    maxgrid              = 0
    gdf_original         = gpd.GeoDataFrame(geometry=[poligono_lote])
    gdf_original['isin'] = True
    vector               = list(np.arange(0.0001, 0.0011, 0.0001)) + list(np.arange(0.001, 0.01, 0.001))
    
    for angulo in [0,-45,-90,-180]: #[-180, -90, -45, 0]
        angulo_rotacion = inclinacion_actual+angulo
        
        # Generar cuadrícula
        grid    = []
        refgrid = []
        conteo  = 0
        for i in range(cols):
            for j in range(rows):
                conteo  += 1
                # Calcular coordenadas base
                x = minx + i * cell_size
                y = miny + j * cell_size
                
                # Crear polígono
                poly = Polygon([
                    (x, y),
                    (x + cell_size, y),
                    (x + cell_size, y + cell_size),
                    (x, y + cell_size)
                ])
                
                # Rotar alrededor del centroide del lote original
                rotated_poly = rotate(poly, angulo_rotacion, origin=centroid)
                grid.append({'geometry':rotated_poly,'id':conteo})
                refgrid.append({'geometry':poly,'id':conteo})
        grid = gpd.GeoDataFrame(grid)
        grid = gpd.GeoDataFrame(grid, crs="EPSG:4326", geometry='geometry')
            
        for rmove in vector:
            xoff                 = rmove/1000
            gridpaso             = grid.copy()
            gridpaso['geometry'] = gridpaso['geometry'].apply(lambda geom: translate(geom, xoff=xoff, yoff=0))
            gridpaso             = gpd.sjoin(gridpaso, gdf_original, how="left", predicate="within")
            gridpaso['id']       = range(len(gridpaso))
            gridpaso             = gridpaso[gridpaso['isin']==True]
            gridpaso.index       = range(len(gridpaso))
    
            if len(gridpaso)>maxgrid:
                result_grid    = gridpaso.copy()
                maxgrid        = len(gridpaso)
                reference_grid = gpd.GeoDataFrame(refgrid)
                reference_grid = gpd.GeoDataFrame(reference_grid, crs="EPSG:4326", geometry='geometry')

    reference_grid       = reference_grid[reference_grid['id'].isin(result_grid['id'])]
    reference_grid['x']  = reference_grid.geometry.centroid.x
    reference_grid['y']  = reference_grid.geometry.centroid.y
    reference_grid       = reference_grid.sort_values(by=['y', 'x'], ascending=[False, True])

    reference_grid['fila'] = reference_grid['y'].apply(lambda x: np.round(x,7))
    reference_grid['fila'] = reference_grid['fila'].rank(method='dense', ascending=False).astype(int)
    reference_grid['col']  = reference_grid['x'].apply(lambda x: np.round(x,7))
    reference_grid['col']  = reference_grid['col'].rank(method='dense', ascending=True).astype(int)

    grid = result_grid.merge(reference_grid[['fila','col','id']],on='id',how='left',validate='1:1')

    variables = [x for x in ['index_right', 'isin'] if x in grid]
    if variables!=[]:
        grid.drop(columns=variables,inplace=True)
        
    return grid

#-----------------------------------------------------------------------------#
# Border Grid
#-----------------------------------------------------------------------------#
def getBorderGrid(datagrid):
    
    data = gpd.GeoDataFrame()
    if not datagrid.empty:
        areagrid              = getareapolygon(datagrid['geometry'].iloc[0])
        dataradio             = datagrid.copy()
        dataradio             = dataradio[['geometry','id']]
        dataradio['latitud']  = dataradio['geometry'].apply(lambda x: x.centroid.y)
        dataradio['longitud'] = dataradio['geometry'].apply(lambda x: x.centroid.x)
        dataradio['geometry'] = dataradio.apply(lambda x: circle_polygon(np.sqrt(areagrid),x['latitud'],x['longitud']),axis=1)
        dataradio             = gpd.GeoDataFrame(dataradio, geometry='geometry')
        dataradio.rename(columns={'id':'id_origen'},inplace=True)
    
        result  = gpd.sjoin(datagrid, dataradio, how='inner')
        v       = result['id'].value_counts().reset_index()
        v       = v[v['count']<8]
        data    = datagrid[datagrid['id'].isin(v['id'])]
    return data


#-----------------------------------------------------------------------------#
# Transformar la columna col y fila, que vaya de 1,2,3,...-3,-2,-1 
#-----------------------------------------------------------------------------#
def transform_fila_column(df, column_name='fila'):

    max_value = df[column_name].max()
    def map_fila(x):
        if x <= max_value / 2:
            return x  # Mantener los valores originales hasta la mitad
        else:
            return x - max_value - 1  # Mapear los valores superiores a negativos

    df_transformed = df.copy()
    df_transformed[column_name] = df_transformed[column_name].apply(map_fila)    
    return df_transformed

#-----------------------------------------------------------------------------#
# Area del poligono en metros cuadrados
#-----------------------------------------------------------------------------#
def getareapolygon(polygon):
    try:
        geojson_polygon = geojson.dumps(polygon)
        return areapolygon(geojson_polygon)
    except: return None
    
#-----------------------------------------------------------------------------#
# Encuentra el cell size para un grid (cuadrado) de una dimension cercana al target
#-----------------------------------------------------------------------------#
def find_cell_size(minx, miny, initial_cell_size=0.0001/1000, step=0.001/1000, target_area=1):
    cell_size = initial_cell_size
    while True:
        # Coordenadas para el polígono
        x = minx + cell_size
        y = miny + cell_size
        poly = Polygon([
            (x, y),
            (x + cell_size, y),
            (x + cell_size, y + cell_size),
            (x, y + cell_size)
        ])
        areagrid = getareapolygon(poly)
        if areagrid >= target_area:
            break
        cell_size += step
    
    return cell_size
