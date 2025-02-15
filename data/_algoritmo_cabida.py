import streamlit as st
import geopandas as gpd
import math
import geojson
import numpy as np
from shapely.affinity import rotate
from shapely.geometry import Polygon,Point,mapping,shape,box
from shapely import wkt
from geopy.distance import geodesic
from pyproj import CRS
from shapely.ops import unary_union
from area import area as areapolygon

crs = CRS.from_epsg(4326)

def getareapolygon(polygon):
    try:
        geojson_polygon = geojson.dumps(polygon)
        return areapolygon(geojson_polygon)
    except: return None
    
    
# Arma el grid
def _grid(poligono_lote):
    
    gdf_original         = gpd.GeoDataFrame(geometry=[poligono_lote])
    gdf_original['isin'] = True
    polygonarea          = getareapolygon(poligono_lote)
    
    #mt  = 0.01
    mt  = (polygonarea/100000)
    mt  = math.floor(mt * 1000) / 1000
    gdf = gpd.GeoDataFrame(geometry=[poligono_lote])
    minx, miny, maxx, maxy = gdf.total_bounds
    cell_size = mt/1000
    cols      = int((maxx - minx) / cell_size)
    rows      = int((maxy - miny) / cell_size)
    grid      = []
    for i in range(cols):
        for j in range(rows):
            poly = Polygon([(minx + i*cell_size, miny + j*cell_size),
                            (minx + (i+1)*cell_size, miny + j*cell_size),
                            (minx + (i+1)*cell_size, miny + (j+1)*cell_size),
                            (minx + i*cell_size, miny + (j+1)*cell_size)])
            grid.append(poly)
    grid       = gpd.GeoDataFrame(geometry=grid)
    grid       = gpd.sjoin(grid, gdf_original, how="left", op="within")
    grid['id'] = range(len(grid))
    grid       = grid[grid['isin']==True]
    grid.index = range(len(grid))

    # Ordenar primero por NOROCCIDENTE
    grid['x']  = grid.geometry.centroid.x
    grid['y']  = grid.geometry.centroid.y
    grid       = grid.sort_values(by=['y', 'x'], ascending=[False, True])
    grid['id'] = range(len(grid))
    
    # columnas y filas
    w         = grid['y'].value_counts().reset_index().sort_values(by='y',ascending=False)
    w.index   = range(len(w))
    w['fila'] = range(1,len(w)+1)
    grid      = grid.merge(w[['y','fila']],on='y',how='left',validate='m:1')
    
    w         = grid['x'].value_counts().reset_index().sort_values(by='x',ascending=True)
    w.index   = range(len(w))
    w['col']  = range(1,len(w)+1)
    grid      = grid.merge(w[['x','col']],on='x',how='left',validate='m:1')
    grid      = grid.drop(columns=['x', 'y'])
    
    variables = [x for x in ['index_right', 'isin'] if x in grid]
    if variables!=[]:
        grid.drop(columns=variables,inplace=True)
    return grid

# Arma un solo cuadrado grande
def build_larger_square(first_square, n):
    width        = first_square.bounds[2] - first_square.bounds[0]
    height       = first_square.bounds[3] - first_square.bounds[1]
    minx, maxy   = first_square.bounds[0], first_square.bounds[3]
    maxx         = minx + (width * n)
    miny         = maxy - (height * n)
    large_square = box(minx, miny, maxx, maxy)
    return large_square

# Forma de rectangulo
def build_rectangulo(first_square, n):
    large_square = build_larger_square(first_square, n)
    minx, miny, maxx, maxy = large_square.bounds
    width = maxx - minx
    height = maxy - miny
    
    # Crear los dos bloques para el rectángulo
    block1 = large_square  # Bloque superior (cuadrado completo)
    block2 = box(minx, miny - height/2, maxx, miny)  # Medio bloque abajo
    
    # Unir los bloques para formar el rectángulo
    rectangulo = unary_union([block1, block2])
    
    return rectangulo

# Forma de L
def build_L(first_square, n):
    large_square = build_larger_square(first_square, n)
    minx, miny, maxx, maxy = large_square.bounds
    width = maxx - minx
    height = maxy - miny
    
    # Crear los cuatro bloques para la forma L
    block1 = large_square  # Bloque de referencia
    block2 = box(minx, miny - height, maxx, miny)  # Bloque abajo
    block3 = box(minx, miny - 2*height, maxx, miny - height)  # Bloque más abajo
    block4 = box(maxx, miny - 2*height, maxx + width, miny - height)  # Bloque a la derecha
    
    # Unir los bloques para formar la L
    L_shape = unary_union([block1, block2, block3, block4])
    
    return L_shape

# Forma de U
def build_U(first_square, n):
    large_square = build_larger_square(first_square, n)
    minx, miny, maxx, maxy = large_square.bounds
    width = maxx - minx
    height = maxy - miny
    
    # Crear los cinco bloques para la forma U
    block1 = large_square  # Bloque de referencia
    block2 = box(minx, miny - height, maxx, miny)  # Bloque abajo
    block3 = box(maxx, miny - height, maxx + width, miny)  # Bloque a la derecha
    block4 = box(maxx + width, miny - height, maxx + 2*width, miny)  # Bloque más a la derecha
    block5 = box(maxx + width, miny, maxx + 2*width, miny + height)  # Bloque arriba
    
    # Unir los bloques para formar la U
    U_shape = unary_union([block1, block2, block3, block4, block5])
    
    return U_shape

# Forma de L inversa
def build_L_I(first_square, n):
    large_square = build_larger_square(first_square, n)
    minx, miny, maxx, maxy = large_square.bounds
    width = maxx - minx
    height = maxy - miny
    
    # Crear los cuatro bloques para la forma L invertida
    block1 = large_square  # Bloque de referencia
    block2 = box(minx, miny - height, maxx, miny)  # Bloque abajo
    block3 = box(minx, miny - 2*height, maxx, miny - height)  # Bloque más abajo
    block4 = box(minx - width, miny - 2*height, minx, miny - height)  # Bloque a la izquierda
    
    # Unir los bloques para formar la L invertida
    L_I_shape = unary_union([block1, block2, block3, block4])
    
    return L_I_shape

# Forma de U inversa
def build_U_I(first_square, n):
    large_square = build_larger_square(first_square, n)
    minx, miny, maxx, maxy = large_square.bounds
    width = maxx - minx
    height = maxy - miny
    
    # Crear los cinco bloques para la forma U invertida
    block1 = large_square  # Bloque de referencia
    block2 = box(minx, maxy, maxx, maxy + height)  # Bloque arriba
    block3 = box(maxx, maxy, maxx + width, maxy + height)  # Bloque a la derecha
    block4 = box(maxx + width, maxy, maxx + 2*width, maxy + height)  # Bloque más a la derecha
    block5 = box(maxx + width, miny, maxx + 2*width, maxy)  # Bloque abajo
    
    # Unir los bloques para formar la U invertida
    U_I_shape = unary_union([block1, block2, block3, block4, block5])
    
    return U_I_shape

# Varios cuadrados o rectangulos pero en la medida que hay mas de 3 los va organizando en una cuadricula
def build_multiple_block_square(first_square, n, num_blocks, forma='cuadrado'):

    if 'cuadrado' in forma:
        large_square = build_larger_square(first_square, n)
    elif 'rectangulo' in forma:
        large_square = build_rectangulo(first_square, n)

    minx, miny, maxx, maxy = large_square.bounds
    width = maxx - minx
    height = maxy - miny

    first_minx, first_miny, first_maxx, first_maxy = first_square.bounds
    first_width = first_maxx - first_minx  # Ancho de first_square
    first_height = first_maxy - first_miny  # Alto de first_square

    blocks = []
    num_cols = math.ceil(math.sqrt(num_blocks))  # Número de columnas
    num_rows = math.ceil(num_blocks / num_cols)  # Número de filas
    
    for i in range(num_blocks):
        row = i // num_cols  # Determina la fila
        col = i % num_cols   # Determina la columna
        block_minx = minx + col * (width + 2*first_width)  # Desplazamiento horizontal (a la derecha)
        block_miny = miny - row * (height + 2*first_height)  # Desplazamiento vertical (hacia abajo)
        block_maxx = block_minx + width
        block_maxy = block_miny + height
        
        new_block = box(block_minx, block_miny, block_maxx, block_maxy)
        blocks.append(new_block)

    shape = unary_union(blocks)
    
    return shape

# Varios cuadrados o rectangulos que se van anadiendo en fila
def build_multiple_block_row(first_square, n, num_blocks, forma='cuadrado'):

    if 'cuadrado' in forma:
        large_square = build_larger_square(first_square, n)
    elif 'rectangulo' in forma:
        large_square = build_rectangulo(first_square, n)
    
    minx, miny, maxx, maxy = large_square.bounds
    width  = maxx - minx
    height = maxy - miny
    
    first_minx, first_miny, first_maxx, first_maxy = first_square.bounds
    first_height = first_maxy - first_miny
    
    blocks = [large_square]
    
    for i in range(1, num_blocks):
        new_block = box(minx, miny - (height + first_height) * i, maxx, miny - (height + first_height) * i + height)
        blocks.append(new_block)

    shape = unary_union(blocks)
    
    return shape


# Maximo numero de cuadrados
def getmaxcuadrados(grid,area_objetivo):
    area_cuadrado   = getareapolygon(grid['geometry'].iloc[0])
    total_cuadrados = len(grid)

    areasuma      = 0
    max_cuadrados = 0
    for i in range(total_cuadrados):
        areasuma += area_cuadrado
        if areasuma>area_objetivo:
            break
        else:
            max_cuadrados += 1
    return max_cuadrados
            
# Numero maximo de cuadrados que utilziar segun la forma
def maxN(max_cuadrados,forma,num_buildings):
        
    # Si son bloques de cuadrados o rectangulos entonces tienen que partir
    #   de un maxN menor para optimziar tiempo del algoritmo, o sino empezaria de
    #   un maxN grande y tiene que ir bajando paso a paso
    if not isinstance(num_buildings,int):
        num_buildings = 1
    if num_buildings==1:
        nbuild = 1
    elif 2 <= num_buildings <= 6:
        nbuild = 2
    elif 7 <= num_buildings <= 12:
        nbuild = 3
    else:
        nbuild = 4

    if 'cuadrado' in forma:
        return int(np.floor(np.sqrt(max_cuadrados)/nbuild))
    elif 'cuadrado-I' in forma:
        return int(np.floor(np.sqrt(max_cuadrados)/nbuild))
    elif 'rectangulo' in forma:
        return int(np.floor(np.sqrt(max_cuadrados/1.5)/nbuild))
    elif 'rectangulo-I' in forma:
        return int(np.floor(np.sqrt(max_cuadrados/1.5)/nbuild))
    elif 'L' in forma:
        return int(np.floor(np.sqrt(max_cuadrados/4)/nbuild))
    elif 'L-I' in forma:
        return int(np.floor(np.sqrt(max_cuadrados/4)/nbuild))
    elif 'U' in forma:
        return int(np.floor(np.sqrt(max_cuadrados/5)/nbuild))
    elif 'U-I' in forma:
        return int(np.floor(np.sqrt(max_cuadrados/5)/nbuild))

# Metros de aislamiento
def getAislamiento(poligono_lote,metrosmin=0):
    
    resultado = poligono_lote
    if metrosmin>0:
        numbuffer = 0.00000001
        terminado = False
        
        while not terminado:
            polygon = poligono_lote.buffer(-numbuffer)
            
            # Extraer puntos
            puntos_poligono_1 = [Point(x, y) for x, y in poligono_lote.exterior.coords]
            puntos_poligono_2 = [Point(x, y) for x, y in polygon.exterior.coords]
            
            distancia_minima = float('inf')  # Inicializa la distancia mínima
        
            # Calcula la distancia entre cada par de puntos de los dos polígonos
            for punto1 in puntos_poligono_1:
                for punto2 in puntos_poligono_2:
                    distancia_actual = geodesic((punto1.y, punto1.x), (punto2.y, punto2.x)).meters
                    if distancia_actual < distancia_minima:
                        distancia_minima = distancia_actual
        
            # Condición de terminación
            if distancia_minima >= metrosmin:
                terminado = True
                resultado = polygon
            else:
                # Ajusta el incremento
                if numbuffer < 0.01:  # Si el buffer es pequeño, aumenta más rápido
                    numbuffer *= 1.1
                else:  # Si el buffer es mayor, usa un incremento más pequeño
                    numbuffer += 0.00000001  # Aumentar en un valor constante
        
    return resultado

@st.cache_data(show_spinner=False)
def algoritmo(poligono_lote,metrosmin=0,porcentaje=0.7,num_buildings=1,forma='rectangulo',adding='block'):
    
    poligono_lote = wkt.loads(poligono_lote)
    #-------------------------------------------------------------------------#
    # Inputs
    poligono_lote_origen = poligono_lote
    area_lote            = getareapolygon(poligono_lote_origen)
    adding               = 'block' # adding: 'block' | 'row'   cuando hay miltiples edificios entonces 
    
    # Si el lote es grande se deben poner 2 o mas edificios 
    if num_buildings==1 and area_lote>1000: 
        num_buildings = int(np.ceil(area_lote/1000))
        adding        = 'block' # adding: 'block' | 'row'   cuando hay miltiples edificios entonces 
    
    # Aislamiento:
    poligono_lote = getAislamiento( poligono_lote, metrosmin=metrosmin)
    
    if metrosmin==0:
        if num_buildings>1:
            porcentaje = 1 # Cuando hay mas de un edificio por lote por simplicidad tomamos todo el area del lote (reduciendo aislamiento) ya que entre edificio y edificio se deja zona libre
        area_objetivo = area_lote*porcentaje
    else:
        area_objetivo = getareapolygon(poligono_lote)
    
    grid          = _grid(poligono_lote)
    max_cuadrados =  getmaxcuadrados(grid,area_objetivo)


    #-------------------------------------------------------------------------#
    # Inputs
    grid.index = range(len(grid))
    conteo     = -1
    terminado  = 0
    while terminado==0:
        conteo    += 1
        max_n     = maxN(max_cuadrados,forma,num_buildings)
        max_n    -= conteo 
        resultado = None
        for i in range(len(grid)):
            first_square = grid['geometry'].iloc[i]
            
            if num_buildings==1:
                if 'cuadrado' in forma or 'cuadrado-I' in forma:
                    block = build_larger_square(first_square, max_n)
                elif 'rectangulo' in forma or 'rectangulo-I' in forma:
                    block = build_rectangulo(first_square, max_n)
                elif 'L' in forma:
                    block = build_L(first_square, max_n)
                elif 'L-I' in forma:
                    block = build_L_I(first_square, max_n)
                elif 'U' in forma:
                    block = build_U(first_square, max_n)
                elif 'U-I' in forma:
                    block = build_U_I(first_square, max_n)

            if num_buildings>1:
                if not any([x for x in ['cuadrado','rectangulo'] if forma in x]):
                    forma = 'rectangulo'
                if any([x for x in ['cuadrado','rectangulo'] if forma in x]):
                    if 'block' in adding:
                        block = build_multiple_block_square(first_square, max_n, num_buildings, forma=forma) # 'rectangulo' , 'cuadrado'
                    elif 'row' in adding:
                        block = build_multiple_block_row(first_square, max_n, num_buildings, forma=forma) # 'rectangulo' , 'cuadrado'
            
            noroeste_point = max(first_square.exterior.coords, key=lambda coord: (coord[0], -coord[1]))
            lista          = list(range(0, 95, 5)) + list(range(-85, 0, 5))
            for grados in lista:
                polygon_new = rotate(block, grados, origin=noroeste_point, use_radians=False)
                if poligono_lote.contains(polygon_new):
                    resultado = polygon_new
                    terminado = 1
                    break
                
            if resultado is not None:
                terminado = 1
                break
        
        if max_n<1:
            terminado = 1
            
    return resultado