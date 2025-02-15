import streamlit as st
import geopandas as gpd
import pandas as pd
import geojson
import numpy as np
from shapely.affinity import translate
from shapely.affinity import rotate
from shapely.geometry import Polygon
from shapely import wkt
from shapely.ops import unary_union
from area import area as areapolygon

from functions._principal_cabida_aislamiento import main as lote_aislamiento

@st.cache_data(show_spinner=False)
def main(grupo=None, aislamiento_frontal=0, aislamiento_posterior=0, aislamiento_lateral=0, reduccion_poligono=0, nblocks=1, blocks_dis=2, shape=None):
    
    #-----------------------------------------------------------------------------#
    # Orden de los poligonos cuadrados
    #-----------------------------------------------------------------------------#

    poligono_lote, allgrid, grid, border, data_andenes, data_vias, dataunion, esquinero = lote_aislamiento(grupo=grupo, aislamiento_frontal=aislamiento_frontal, aislamiento_posterior=aislamiento_posterior, aislamiento_lateral=aislamiento_lateral, reduccion_poligono=reduccion_poligono)

    areagrid = 0
    try:
        polygons   = grid['geometry'].to_list()
        polygons   = gpd.GeoDataFrame(geometry=[unary_union(polygons)])
        polygons   = polygons.explode()
        polygons['area'] = polygons['geometry'].apply(lambda x: getareapolygon(x))
        areagrid         = polygons['area'].sum()
    except: pass
        
    #-----------------------------------------------------------------------------#
    # Orden de los poligonos cuadrados
    #-----------------------------------------------------------------------------#
    grid.index      = range(len(grid))
    grid['idmerge'] = range(len(grid))
    
    for tipo in ['col','fila']:
        
        grid[f'{tipo}_new'] = None
        conteo              = 0
        df                  = grid[grid[tipo]<0]
        lista               = list(df.sort_values(by=tipo,ascending=False)[tipo].unique())
        for i in lista:
            conteo += 1
            idd     = grid[tipo]==i
            grid.loc[idd,f'{tipo}_new'] = conteo
            
        df    = grid[grid[tipo]>0]
        lista = list(df.sort_values(by=tipo,ascending=False)[tipo].unique())
        for i in lista:
            conteo += 1
            idd     = grid[tipo]==i
            grid.loc[idd,f'{tipo}_new'] = conteo
        
    grid.drop(columns=['fila','col'],inplace=True)
    grid.rename(columns={'fila_new':'fila','col_new':'col'},inplace=True)
        
    #-----------------------------------------------------------------------------#
    # Poligonos cuadrados mas grandes cuando el lote es mas grande
    #-----------------------------------------------------------------------------#
    
    if not grid.empty and len(grid)>1000:
        grid['geometry'] = grid['geometry'].apply(lambda x: x.wkt)
        grid             = pd.DataFrame(grid)
        # target_area=10
        target_area      = int(np.ceil(len(grid)/700))
        grid = _adjusted_grid(poligono_lote.wkt, grid_target=grid.copy(), target_area=target_area)

    grid['fila'] = grid['fila'].rank(method='dense', ascending=True).astype(int)
    grid['col']  = grid['col'].rank(method='dense', ascending=True).astype(int)
    

    #-----------------------------------------------------------------------------#
    # Shape
    #-----------------------------------------------------------------------------#
    building_shape_grid = pd.DataFrame()
    if isinstance(shape,str) and 'rectangulo' in shape and nblocks==1:
        building_shape_grid = rectangulo(grid)
        
    elif isinstance(shape,str) and 'cuadrado' in shape and nblocks==1:
        building_shape_grid = cuadrado(grid)
        
    elif isinstance(shape,str) and 'L' in shape and nblocks==1:
        building_shape_grid = L(grid)

    elif isinstance(shape,str) and 'U' in shape and nblocks==1:
        building_shape_grid = U(grid)
     
    elif shape is None or (isinstance(shape,str) and 'multiple_matriz' in shape) or (isinstance(shape,str) and shape==''):
        areamaxbuilding = 1500
        areaminbuilding = 1000
        if areagrid>areamaxbuilding:
            blocks_dis = 2 if blocks_dis is None or (isinstance(blocks_dis,int) and blocks_dis==0) else blocks_dis
            building_shape_grid = bloques_matriz(grid, blocks_dis=blocks_dis, areamaxbuilding=areamaxbuilding, areaminbuilding=areaminbuilding)
        else:
            building_shape_grid = grid.copy()


    if not building_shape_grid.empty:
        building_shape_grid = gpd.GeoDataFrame(building_shape_grid, crs="EPSG:4326", geometry='geometry')

    #-------------------------------------------------------------------------#
    # Poligonos Building
    #-------------------------------------------------------------------------#
    building_shape_geometry = pd.DataFrame()
    areabuilding = 0
    if not building_shape_grid.empty:
        building_shape_geometry             = building_shape_grid.copy()
        building_shape_geometry['geometry'] = building_shape_geometry['geometry'].apply(lambda x: x.buffer(0.0000001))
        unified                             = unary_union(building_shape_geometry['geometry'].to_list())
        building_shape_geometry             = gpd.GeoDataFrame(geometry=[unified])
        building_shape_geometry             = building_shape_geometry.explode()
        building_shape_geometry['area']     = building_shape_geometry['geometry'].apply(lambda x: getareapolygon(x))
        areabuilding                        = building_shape_geometry['area'].sum()
    
    return building_shape_grid, building_shape_geometry, areabuilding, poligono_lote, allgrid, grid, border, data_andenes, data_vias, dataunion, esquinero

#-----------------------------------------------------------------------------#
# Rectangulo:
#-----------------------------------------------------------------------------#
def rectangulo_optimizador(grid,fstart,cstart,posicion='h'):  #   posicion: 'h' | 'v'   ['horizontal'|'vertical']
    
    blocks    = 0
    nblocks   = 0
    terminado = 0
    while terminado==0:
        blocks     += 1
        if 'v' in posicion:
            idd = (grid['fila'].isin(list(range(fstart,fstart+blocks*2)))) & (grid['col'].isin(list(range(cstart,cstart+blocks))))
        elif 'h' in posicion:
            idd = (grid['fila'].isin(list(range(fstart,fstart+blocks)))) & (grid['col'].isin(list(range(cstart,cstart+blocks*2))))
        
        nblockspaso = sum(idd)
        if sum(idd)==(blocks**2)*2 and nblockspaso>nblocks:
            nblocks = nblockspaso
        else:
            terminado = 1
    return nblocks

def rectangulo_shape(grid,fstart,cstart,posicion='h'):  #   posicion: 'h' | 'v'   ['horizontal'|'vertical']
    blocks    = 0
    nblocks   = 0
    terminado = 0
    resultado = gpd.GeoDataFrame()
    while terminado==0:
        blocks     += 1
        if 'v' in posicion:
            idd = (grid['fila'].isin(list(range(fstart,fstart+blocks*2)))) & (grid['col'].isin(list(range(cstart,cstart+blocks))))
        elif 'h' in posicion:
            idd = (grid['fila'].isin(list(range(fstart,fstart+blocks)))) & (grid['col'].isin(list(range(cstart,cstart+blocks*2))))
        
        nblockspaso = sum(idd)
        if sum(idd)==(blocks**2)*2 and nblockspaso>nblocks:
            nblocks   = nblockspaso
            resultado = grid[idd]
        else:
            terminado = 1
    return resultado

def rectangulo(grid):
    dataresult            = gpd.GeoDataFrame()
    datagrid              = grid.copy()
    datagrid['nblocks_h'] = datagrid.apply(lambda x: rectangulo_optimizador(grid.copy(),x['fila'],x['col'],posicion='h'),axis=1)
    datagrid['nblocks_v'] = datagrid.apply(lambda x: rectangulo_optimizador(grid.copy(),x['fila'],x['col'],posicion='v'),axis=1)
    
    datagrid['area_h'] = datagrid.apply(lambda x: getArea(rectangulo_shape(grid.copy(), x['fila'], x['col'], posicion='h')),axis=1)
    datagrid['area_v'] = datagrid.apply(lambda x: getArea(rectangulo_shape(grid.copy(), x['fila'], x['col'], posicion='v')),axis=1)

    if datagrid['area_h'].max()>=datagrid['area_v'].max():
        datagrid         = datagrid[datagrid['area_h']==datagrid['area_h'].max()]
        datagrid.index   = range(len(datagrid))
        datagrid         = datagrid.sort_values(by=['fila','col'],ascending=True)
        dataresult       = rectangulo_shape(grid.copy(),datagrid['fila'].iloc[0],datagrid['col'].iloc[0],posicion='h')

    else:
        datagrid         = datagrid[datagrid['area_v']==datagrid['area_v'].max()]
        datagrid.index   = range(len(datagrid))
        datagrid         = datagrid.sort_values(by=['fila','col'],ascending=True)
        dataresult       = rectangulo_shape(grid.copy(),datagrid['fila'].iloc[0],datagrid['col'].iloc[0],posicion='v')
    
    return dataresult



#-----------------------------------------------------------------------------#
# Cuadrado:
#-----------------------------------------------------------------------------#
def cuadrado_optimizador(grid,fstart,cstart):
    blocks    = 0
    nblocks   = 0
    terminado = 0
    while terminado==0:
        blocks     += 1
        idd         = (grid['fila'].isin(list(range(fstart,fstart+blocks)))) & (grid['col'].isin(list(range(cstart,cstart+blocks))))
        nblockspaso = sum(idd)
        if sum(idd)==(blocks**2) and nblockspaso>nblocks:
            nblocks = nblockspaso
        else:
            terminado = 1
    return nblocks

def cuadrado_shape(grid,fstart,cstart):
    blocks    = 0
    nblocks   = 0
    terminado = 0
    resultado = gpd.GeoDataFrame()
    while terminado==0:
        blocks     += 1
        idd         = (grid['fila'].isin(list(range(fstart,fstart+blocks)))) & (grid['col'].isin(list(range(cstart,cstart+blocks))))
        nblockspaso = sum(idd)
        if sum(idd)==(blocks**2) and nblockspaso>nblocks:
            nblocks   = nblockspaso
            resultado = grid[idd]
        else:
            terminado = 1
    return resultado

def cuadrado(grid):
    dataresult          = gpd.GeoDataFrame()
    datagrid            = grid.copy()
    datagrid['nblocks'] = datagrid.apply(lambda x: cuadrado_optimizador(grid.copy(),x['fila'],x['col']),axis=1)
    datagrid            = datagrid[datagrid['nblocks']==datagrid['nblocks'].max()]
    
    datagrid['area']    = datagrid.apply(lambda x: getArea(cuadrado_shape(grid.copy(), x['fila'], x['col'])),axis=1)
    datagrid            = datagrid[datagrid['area']==datagrid['area'].max()]
    datagrid.index      = range(len(datagrid))
    datagrid            = datagrid.sort_values(by=['fila','col'],ascending=True)
    dataresult          = cuadrado_shape(grid.copy(),datagrid['fila'].iloc[0],datagrid['col'].iloc[0])

    return dataresult


#-----------------------------------------------------------------------------#
# forma de L:
#-----------------------------------------------------------------------------#
def L_optimizador(grid, fstart, cstart, posicion='h', rotacion=1, tipo_resultado = 'nblocks'):  #   posicion: 'h' | 'v'   ['horizontal'|'vertical'], tipo_resultado 'nblocks' | 'shape'
    
    blocks    = 0
    nblocks   = 0
    terminado = 0
    
    if 'nblocks' in tipo_resultado: 
        resultado = 0
    elif 'shape' in tipo_resultado: 
        resultado = gpd.GeoDataFrame()
        
    while terminado==0:
        blocks     += 1
        
        if 'v' in posicion:
            
            if rotacion==1:
                # L
                lista  = list(range(fstart,fstart+blocks*2))
                idd_v  = (grid['fila'].isin(lista)) & (grid['col'].isin(list(range(cstart,cstart+blocks))))
                fnew   = max(lista)+1
                idd_h  = (grid['fila'].isin(list(range(fnew,fnew+blocks)))) & (grid['col'].isin(list(range(cstart,cstart+blocks*2))))
    
            elif rotacion==2:
                # L inversa
                lista  = list(range(cstart,cstart+blocks*2))
                idd_h  = (grid['fila'].isin(list(range(fstart,fstart+blocks)))) & (grid['col'].isin(lista))
                fnew   = fstart+blocks
                lista  = list(range(fnew,fnew+blocks*2))
                idd_v  = (grid['fila'].isin(lista)) & (grid['col'].isin(list(range(cstart,cstart+blocks))))

            elif rotacion==3:
                # 
                lista  = list(range(cstart,cstart+blocks*2))
                idd_h  = (grid['fila'].isin(list(range(fstart,fstart+blocks)))) & (grid['col'].isin(lista))
                fnew   = fstart+blocks
                cnew   = cstart+blocks
                lista  = list(range(fnew,fnew+blocks*2))
                idd_v  = (grid['fila'].isin(lista)) & (grid['col'].isin(list(range(cnew,cnew+blocks))))

            elif rotacion==4:
                # 
                lista  = list(range(fstart,fstart+blocks*2))
                idd_v  = (grid['fila'].isin(lista)) & (grid['col'].isin(list(range(cstart,cstart+blocks))))
                fnew   = max(lista)+1
                cnew   = cstart-blocks
                idd_h  = (grid['fila'].isin(list(range(fnew,fnew+blocks)))) & (grid['col'].isin(list(range(cnew,cnew+blocks*2))))

        elif 'h' in posicion:
            
            if rotacion==1:
                lista  = list(range(cstart,cstart+blocks*2))
                idd_h  = (grid['fila'].isin(list(range(fstart,fstart+blocks)))) & (grid['col'].isin(lista))
                cnew   = max(lista)+1
                idd_v  = (grid['fila'].isin(list(range(fstart,fstart+blocks*2)))) & (grid['col'].isin(list(range(cnew,cnew+blocks))))
                
            elif rotacion==2:
                lista  = list(range(cstart,cstart+blocks*2))
                idd_v  = (grid['fila'].isin(list(range(cstart,cstart+blocks)))) & (grid['col'].isin(lista))
                cnew   = max(lista)+1
                fnew   = fstart-blocks
                idd_h  = (grid['fila'].isin(list(range(fnew,fnew+blocks*2)))) & (grid['col'].isin(list(range(cnew,cnew+blocks))))

            elif rotacion==3:
                lista  = list(range(fstart,fstart+blocks*2))
                idd_h  = (grid['fila'].isin(lista)) & (grid['col'].isin(list(range(cstart,cstart+blocks))))
                cnew   = cstart+blocks
                lista  = list(range(cnew,cnew+blocks*2))
                idd_v  = (grid['fila'].isin(list(range(fstart,fstart+blocks)))) & (grid['col'].isin(lista))

            elif rotacion==4:
                lista  = list(range(fstart,fstart+blocks*2))
                idd_h  = (grid['fila'].isin(lista)) & (grid['col'].isin(list(range(fstart,fstart+blocks))))
                fnew   = fstart+blocks
                cnew   = cstart+blocks
                lista  = list(range(cnew,cnew+blocks*2))
                idd_v  = (grid['fila'].isin(list(range(fnew,fnew+blocks)))) & (grid['col'].isin(lista))


        nblockspaso = sum(idd_v)+sum(idd_h)
        if nblockspaso==(blocks**2)*4 and nblockspaso>nblocks:
            nblocks = nblockspaso
            if 'shape' in tipo_resultado: 
                resultado = pd.concat([grid[idd_v],grid[idd_h]])
        else:
            terminado = 1
            
    if 'nblocks' in tipo_resultado: 
        resultado = nblocks
    
    return resultado

def L(grid):
    
    dataresult  = gpd.GeoDataFrame()
    r_posicion  = None
    r_rotacion  = None
    r_blocks    = 0
    
    for rotacion in [1,2,3,4]:
        for posicion in ['h','v']:
            datagrid            = grid.copy()
            datagrid['nblocks'] = datagrid.apply(lambda x: L_optimizador(grid.copy(), x['fila'], x['col'], posicion=posicion, rotacion=rotacion, tipo_resultado='nblocks'),axis=1)
            
            nblocks = datagrid['nblocks'].max()
            if nblocks>r_blocks:
                r_blocks   = nblocks
                r_posicion = posicion
                r_rotacion = rotacion
                
    datagrid            = grid.copy()
    datagrid['nblocks'] = datagrid.apply(lambda x: L_optimizador(grid.copy(), x['fila'], x['col'], posicion=r_posicion, rotacion=r_rotacion, tipo_resultado='nblocks'),axis=1)
    datagrid            = datagrid[datagrid['nblocks']==datagrid['nblocks'].max()]
    datagrid['area']    = datagrid.apply(lambda x: getArea(L_optimizador(grid.copy(), x['fila'], x['col'], posicion=r_posicion, rotacion=r_rotacion, tipo_resultado='shape')),axis=1)
    datagrid            = datagrid[datagrid['area']==datagrid['area'].max()]
    datagrid.index      = range(len(datagrid))
    datagrid            = datagrid.sort_values(by=['fila','col'],ascending=True)
    dataresult          = L_optimizador(grid.copy(), datagrid['fila'].iloc[0], datagrid['col'].iloc[0], posicion=r_posicion, rotacion=r_rotacion, tipo_resultado='shape')

    return dataresult
    
#-----------------------------------------------------------------------------#
# forma de U:
#-----------------------------------------------------------------------------#
def U_optimizador(grid, fstart, cstart, posicion='h', rotacion=1, tipo_resultado = 'nblocks'):  #   posicion: 'h' | 'v'   ['horizontal'|'vertical'], tipo_resultado 'nblocks' | 'shape'
    
    blocks    = 0
    nblocks   = 0
    terminado = 0
    
    if 'nblocks' in tipo_resultado: 
        resultado = 0
    elif 'shape' in tipo_resultado: 
        resultado = gpd.GeoDataFrame()
        
    while terminado==0:
        blocks     += 1
        
        if 'v' in posicion:
            
            if rotacion==1:
                # U 
                lista  = list(range(fstart,fstart+blocks*2))
                idd_1  = (grid['fila'].isin(lista)) & (grid['col'].isin(list(range(cstart,cstart+blocks))))
                fnew   = fstart
                idd_2  = (grid['fila'].isin(list(range(fnew,fnew+blocks)))) & (grid['col'].isin(list(range(cstart,cstart+blocks*2))))
                fnew   = max(lista)+1
                idd_3  = (grid['fila'].isin(list(range(fnew,fnew+blocks)))) & (grid['col'].isin(list(range(cstart,cstart+blocks*2))))
    
            elif rotacion==2:
                # U inversa
                lista  = list(range(fstart,fstart+blocks*2))
                idd_1  = (grid['fila'].isin(lista)) & (grid['col'].isin(list(range(cstart+blocks,cstart+blocks*2))))
                fnew   = fstart
                idd_2  = (grid['fila'].isin(list(range(fnew,fnew+blocks)))) & (grid['col'].isin(list(range(cstart,cstart+blocks*2))))
                fnew   = max(lista)+1
                idd_3  = (grid['fila'].isin(list(range(fnew,fnew+blocks)))) & (grid['col'].isin(list(range(cstart,cstart+blocks*2))))
    
        elif 'h' in posicion:
            
            if rotacion==1:
                # U inversa
                lista  = list(range(fstart,fstart+blocks*2))
                idd_1  = (grid['fila'].isin(lista)) & (grid['col'].isin(list(range(cstart,cstart+blocks))))
                
                lista  = list(range(cstart,cstart+blocks*2))
                idd_2  = (grid['fila'].isin(list(range(fstart,fstart+blocks)))) & (grid['col'].isin(lista))
                
                cnew   = max(lista)+1
                idd_3  = (grid['fila'].isin(list(range(fstart,fstart+blocks*2)))) & (grid['col'].isin(list(range(cnew,cnew+blocks))))

            elif rotacion==2:
                # U inversa
                lista  = list(range(fstart,fstart+blocks*2))
                idd_1  = (grid['fila'].isin(lista)) & (grid['col'].isin(list(range(cstart,cstart+blocks))))
                
                lista  = list(range(cstart,cstart+blocks*2))
                fnew   = fstart+blocks
                idd_2  = (grid['fila'].isin(list(range(fnew,fnew+blocks)))) & (grid['col'].isin(lista))
                
                cnew   = max(lista)+1
                idd_3  = (grid['fila'].isin(list(range(fstart,fstart+blocks*2)))) & (grid['col'].isin(list(range(cnew,cnew+blocks))))

        nblockspaso = sum(idd_1)+sum(idd_2)+sum(idd_3)
        if nblockspaso==(blocks**2)*6 and nblockspaso>nblocks:
            nblocks = nblockspaso
            if 'shape' in tipo_resultado: 
                resultado = pd.concat([grid[idd_1],grid[idd_2],grid[idd_3]])
        else:
            terminado = 1
            
    if 'nblocks' in tipo_resultado: 
        resultado = nblocks
    
    return resultado

def U(grid):
    
    dataresult  = gpd.GeoDataFrame()
    r_posicion  = None
    r_rotacion  = None
    r_blocks    = 0
    
    for rotacion in [1,2]:
        for posicion in ['h','v']:
            datagrid            = grid.copy()
            datagrid['nblocks'] = datagrid.apply(lambda x: U_optimizador(grid.copy(), x['fila'], x['col'], posicion=posicion, rotacion=rotacion, tipo_resultado='nblocks'),axis=1)
            
            nblocks = datagrid['nblocks'].max()
            if nblocks>r_blocks:
                r_blocks   = nblocks
                r_posicion = posicion
                r_rotacion = rotacion
                
    datagrid            = grid.copy()
    datagrid['nblocks'] = datagrid.apply(lambda x: U_optimizador(grid.copy(), x['fila'], x['col'], posicion=r_posicion, rotacion=r_rotacion, tipo_resultado='nblocks'),axis=1)
    datagrid            = datagrid[datagrid['nblocks']==datagrid['nblocks'].max()]
    datagrid['area']    = datagrid.apply(lambda x: getArea(U_optimizador(grid.copy(), x['fila'], x['col'], posicion=r_posicion, rotacion=r_rotacion, tipo_resultado='shape')),axis=1)
    datagrid            = datagrid[datagrid['area']==datagrid['area'].max()]
    datagrid.index      = range(len(datagrid))
    datagrid            = datagrid.sort_values(by=['fila','col'],ascending=True)
    dataresult          = U_optimizador(grid.copy(), datagrid['fila'].iloc[0], datagrid['col'].iloc[0], posicion=r_posicion, rotacion=r_rotacion, tipo_resultado='shape')

    return dataresult

    
#-----------------------------------------------------------------------------#
# Bloques en linea (vertical u horizontal):
#-----------------------------------------------------------------------------#
def bloques_optimizador(grid, fstart, cstart, posicion='h', nbigblocks=2, blocks_dis=1, tipo_resultado='nblocks'):
    blocks    = 0
    nblocks   = 0
    terminado = 0
    
    if 'nblocks' in tipo_resultado: 
        resultado = 0
    elif 'shape' in tipo_resultado: 
        resultado = gpd.GeoDataFrame()
        
    resultado = gpd.GeoDataFrame()
    while terminado==0:
        blocks     += 1
        
        if 'v' in posicion:
            lista    = list(range(fstart,fstart+blocks))
            idd      = (grid['fila'].isin(lista)) & (grid['col'].isin(list(range(cstart,cstart+blocks))))
    
            for i in range(1,nbigblocks):
                fnew     = max(lista)+1+blocks_dis
                lista    = list(range(fnew,fnew+blocks))
                iddj     = (grid['fila'].isin(lista)) & (grid['col'].isin(list(range(cstart,cstart+blocks))))
                idd      = (idd) | (iddj)
                
        elif 'h' in posicion:
            lista    = list(range(cstart,cstart+blocks))
            idd      = (grid['fila'].isin(list(range(fstart,fstart+blocks)))) & (grid['col'].isin(lista))

            for i in range(1,nbigblocks):
                cnew     = max(lista)+1+blocks_dis
                lista    = list(range(cnew,cnew+blocks))
                iddj     = (grid['fila'].isin(list(range(fstart,fstart+blocks)))) & (grid['col'].isin(lista))
                idd      = (idd) | (iddj)
            
        nblockspaso = sum(idd)
        if sum(idd)==(blocks**2)*nbigblocks and nblockspaso>nblocks:
            nblocks   = nblockspaso
            if 'shape' in tipo_resultado: 
                resultado = grid[idd]
        else:
            terminado = 1
            
    if 'nblocks' in tipo_resultado: 
        resultado = nblocks
    
    return resultado

def bloques(grid, nbigblocks=2, blocks_dis=2):
    
    dataresult  = gpd.GeoDataFrame()
    r_posicion  = None
    r_blocks    = 0
    
    for posicion in ['h','v']:
        datagrid            = grid.copy()
        datagrid['nblocks'] = datagrid.apply(lambda x: bloques_optimizador(grid.copy(), x['fila'], x['col'], posicion=posicion, nbigblocks=nbigblocks, blocks_dis=blocks_dis, tipo_resultado='nblocks'),axis=1)
        
        nblocks = datagrid['nblocks'].max()
        if nblocks>r_blocks:
            r_blocks   = nblocks
            r_posicion = posicion
                
    datagrid            = grid.copy()
    datagrid['nblocks'] = datagrid.apply(lambda x: bloques_optimizador(grid.copy(), x['fila'], x['col'], posicion=r_posicion, nbigblocks=nbigblocks, blocks_dis=blocks_dis, tipo_resultado='nblocks'),axis=1)
    datagrid            = datagrid[datagrid['nblocks']==datagrid['nblocks'].max()]
    datagrid            = datagrid.sort_values(by=['fila','col'],ascending=True)
    dataresult          = bloques_optimizador(grid.copy(), datagrid['fila'].iloc[0], datagrid['col'].iloc[0], posicion=r_posicion, nbigblocks=nbigblocks, blocks_dis=blocks_dis, tipo_resultado='shape')

    return dataresult

#-----------------------------------------------------------------------------#
# Bloques en matriz:
#-----------------------------------------------------------------------------#
def bloques_matriz_optimizador(grid, fstart, cstart, blocks, blocks_dis=1, tipo_resultado='areabuilding'):

    areabuilding = 0
    if 'areabuilding' in tipo_resultado: 
        resultado = 0
    elif 'shape' in tipo_resultado: 
        resultado = gpd.GeoDataFrame()

    fvector   = []
    fvector.append(fstart)
    lista     = list(range(fstart,fstart+blocks))
    terminado = 0
    idd       = (grid['fila'].isin(lista)) & (grid['col'].isin(list(range(cstart,cstart+blocks))))

    if sum(idd)>0 and sum(idd)==(blocks**2):

        while terminado==0:
            fnew     = max(lista)+1+blocks_dis
            fvector.append(fnew)
            lista    = list(range(fnew,fnew+blocks))
            iddj     = (grid['fila'].isin(lista)) & (grid['col'].isin(list(range(cstart,cstart+blocks))))
            if sum(iddj)>0 and sum(iddj)==(blocks**2):
                idd  = (idd) | (iddj)
            else:
                terminado = 1

    else: 
        datagrid       = grid.copy()
        datagrid.index = range(len(datagrid))
        idd            =  datagrid.index<0

    if isinstance(fvector,list) and fvector!=[]:

        for fnew in fvector:

            lista = list(range(cstart,cstart+blocks))
            iddj  = (grid['fila'].isin(list(range(fnew,fnew+blocks)))) & (grid['col'].isin(lista))
            if sum(iddj)>0 and sum(iddj)==(blocks**2):
                idd       = (idd) | (iddj)
                terminado = 0

                while terminado==0:
                    cnew     = max(lista)+1+blocks_dis
                    lista    = list(range(cnew,cnew+blocks))
                    iddj     = (grid['fila'].isin(list(range(fnew,fnew+blocks)))) & (grid['col'].isin(lista))
                    if sum(iddj)>0 and sum(iddj)==(blocks**2):
                        idd  = (idd) | (iddj)
                    else:
                        terminado=1

    if sum(idd)>0:
        resultado    = grid[idd]
        resultado    = resultado.drop_duplicates(subset=['col', 'fila'],keep='first')
        areabuilding = UnifyPolygonArea(resultado)

    if 'areabuilding' in tipo_resultado: 
        resultado = areabuilding

    return resultado

def bloques_matriz(grid, blocks_dis=1, areamaxbuilding=1400, areaminbuilding=500):

    dataresult = gpd.GeoDataFrame()    
    blocks     = 0
    minblocks  = 0
    if not grid.empty:
        p         = grid['geometry'].apply(lambda x: getareapolygon(x)).max()
        blocks    = int(np.ceil(np.sqrt(areamaxbuilding/p)))  # El edificio maximo es de 1,400 mt2
        minblocks = int(np.floor(np.sqrt(areaminbuilding/p)))  # No se puede tener edificios de menor de 400 mt2
        minblocks = max(0,minblocks)

    if blocks>0:
        datagrid = pd.DataFrame()
        for blocks in range(minblocks,blocks+1):
            datapaso           = grid.copy()
            datapaso['blocks'] = blocks
            datagrid           = pd.concat([datagrid,datapaso])

        datagrid['area'] = datagrid.apply(lambda x: bloques_matriz_optimizador(grid.copy(), x['fila'], x['col'], x['blocks'], blocks_dis=blocks_dis, tipo_resultado='areabuilding'),axis=1)     
        datagrid         = datagrid[datagrid['area']==datagrid['area'].max()]
        datagrid.index   = range(len(datagrid))
        datagrid         = datagrid.sort_values(by=['fila','col'],ascending=True)
        dataresult       = bloques_matriz_optimizador(grid.copy(), datagrid['fila'].iloc[0], datagrid['col'].iloc[0], datagrid['blocks'].iloc[0] , blocks_dis=blocks_dis, tipo_resultado='shape') 
    return dataresult


def getareapolygon(polygon):
    try:
        geojson_polygon = geojson.dumps(polygon)
        return areapolygon(geojson_polygon)
    except: return None
    
#-----------------------------------------------------------------------------#
# Grid Interno (aislamiento) mas grande para lotes mas grandes
#-----------------------------------------------------------------------------#
@st.cache_data(show_spinner=False)
def _adjusted_grid(poligono_lote, grid_target=pd.DataFrame(), target_area=1):
    
    poligono_lote = wkt.loads(poligono_lote)

    if not grid_target.empty:
        grid_target['geometry'] = gpd.GeoSeries.from_wkt(grid_target['geometry'])
        grid_target             = gpd.GeoDataFrame(grid_target, geometry='geometry')
    
    # Calcular la inclinación
    rotating_rectangle = poligono_lote.minimum_rotated_rectangle
    coords             = list(rotating_rectangle.exterior.coords)
    dx                 = coords[1][0] - coords[0][0]
    dy                 = coords[1][1] - coords[0][1]
    inclinacion_actual = np.degrees(np.arctan2(dy, dx))

    # Información del polígono original
    gdf = gpd.GeoDataFrame(geometry=[poligono_lote])
    minx, miny, maxx, maxy = gdf.total_bounds
    
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
            gridpaso             = gpd.sjoin(gridpaso, gdf_original, how="left", predicate="intersects")
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
        
        
    # Recortar los polígonos que no están completamente dentro
    def clip_or_keep(geom, reference):
        if geom.within(reference):
            return geom  # Dejar tal cual si está completamente dentro
        else:
            return geom.intersection(reference)  # Recortar si no está completamente dentro


    gridpaso             = grid_target.copy()
    gridpaso['geometry'] = gridpaso['geometry'].apply(lambda x: x.buffer(0.0000001))
    unified              = unary_union(gridpaso['geometry'].to_list())
    idd                  = grid['geometry'].apply(lambda x: x.intersects(unified))
    grid                 = grid[idd]
    grid['geometry']     = grid['geometry'].apply(lambda x: clip_or_keep(x, unified))
    
    return grid

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


#-----------------------------------------------------------------------------#
# Encuentra el area total construida de los edificios
#-----------------------------------------------------------------------------#
def UnifyPolygonArea(building_shape_grid):
    
    if not building_shape_grid.empty:
        building_shape_grid = gpd.GeoDataFrame(building_shape_grid, crs="EPSG:4326", geometry='geometry')

    #-------------------------------------------------------------------------#
    # Poligonos Building
    #-------------------------------------------------------------------------#
    areabuilding = 0
    if not building_shape_grid.empty:
        try:
            building_shape_geometry             = building_shape_grid.copy()
            building_shape_geometry['geometry'] = building_shape_geometry['geometry'].apply(lambda x: x.buffer(0.0000001))
            unified                             = unary_union(building_shape_geometry['geometry'].to_list())
            building_shape_geometry             = gpd.GeoDataFrame(geometry=[unified])
            building_shape_geometry             = building_shape_geometry.explode(index_parts=True)
            building_shape_geometry['area']     = building_shape_geometry['geometry'].apply(lambda x: getareapolygon(x))
            areabuilding                        = building_shape_geometry['area'].sum()
        except: pass
    
    return areabuilding

def getArea(x):
    try: return UnifyPolygonArea(x)
    except: return 0