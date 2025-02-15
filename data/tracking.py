import streamlit as st
import mysql.connector
import json
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine 

@st.cache_data(show_spinner=False)
def savesearch(token, barmanpre, seccion, inputvar, id_consulta_defaul=None):

    email = None
    if isinstance(token,str) and token!='':
        user     = st.secrets["user_bigdata"]
        password = st.secrets["password_bigdata"]
        host     = st.secrets["host_bigdata_lectura"]
        schema   = st.secrets["schema_bigdata"]
        engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
        data     = pd.read_sql_query(f"SELECT email FROM  urbex.users WHERE token='{token}'" , engine)
        engine.dispose()
        if not data.empty:
            email = data['email'].iloc[0]
        
    if token is not None or email is not None:
        user     = st.secrets["user_write_urbex"]
        password = st.secrets["password_write_urbex"]
        host     = st.secrets["host_write_urbex"]
        try:
            inputvar_str = None
            try:
                inputvar_str = pd.io.json.dumps(inputvar)
                if inputvar_str=='null': inputvar_str = None 
            except:
                try:
                    inputvar_str = json.dumps(inputvar) if isinstance(inputvar, dict) else None
                    if inputvar_str is None:
                        inputvar_str = inputvar if isinstance(inputvar, str) and inputvar!='' else None
                except: 
                    inputvar_str = None

            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            connection = mysql.connector.connect(
                user=user,
                password=password,
                host=host,
                database='app'
            )
            
            cursor = connection.cursor()
            insert_query = """
            INSERT INTO app.tracking 
            (token,email, seccion, barmanpre, inputvar, save, fecha_consulta, fecha_update)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
    
            values = (token,email,seccion,barmanpre,inputvar_str,0,current_time, current_time )
            
            cursor.execute(insert_query, values)
            connection.commit()
            inserted_id = cursor.lastrowid
            
            if id_consulta_defaul is None:
                id_consulta_defaul = inserted_id
                
            if isinstance(id_consulta_defaul,int):
                update_query = """UPDATE app.tracking SET id_consulta = %s WHERE id = %s"""
                cursor.execute(update_query, (id_consulta_defaul, inserted_id))
                connection.commit()
            
            cursor.close()
            connection.close()
            
            return True,inserted_id
            
        except:
            # Si hay una conexión abierta, cerrarla
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()
            return False,None
        
    else:
        return False, None
    
def update_save_status(id_consulta, token, value):

    user     = st.secrets["user_write_urbex"]
    password = st.secrets["password_write_urbex"]
    host     = st.secrets["host_write_urbex"]
    
    try:

        connection = mysql.connector.connect(
            user=user,
            password=password,
            host=host,
            database='app'
        )
        
        cursor = connection.cursor()
        
        verify_query = """
        SELECT id FROM tracking 
        WHERE id = %s AND token = %s
        """
        cursor.execute(verify_query, (id_consulta, token))
        result = cursor.fetchone()
        if not result:
            cursor.close()
            connection.close()
            return False
        
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        update_query = f"""
        UPDATE tracking 
        SET save = {value},
            fecha_update = %s
        WHERE id = %s AND token = %s
        """
        cursor.execute(update_query, (current_time, id_consulta, token))
        
        if cursor.rowcount == 0:
            connection.rollback()
            cursor.close()
            connection.close()
            return False
        
        connection.commit()
        cursor.close()
        connection.close()
        
        return True
        
    except:
        # Si hay una conexión abierta, cerrarla
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            
        return False
