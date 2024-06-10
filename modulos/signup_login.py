import streamlit as st
import pandas as pd
import boto3
import hashlib
from datetime import datetime
from sqlalchemy import create_engine
from streamlit_js_eval import streamlit_js_eval
from botocore.exceptions import ClientError
from streamlit_cookies_controller import CookieController

user     = st.secrets["user_bigdata"]
password = st.secrets["password_bigdata"]
host     = st.secrets["host_bigdata"]
schema   = 'urbex'

USER_POOL_ID = st.secrets["COGNITO_USER_POOL_ID"]
CLIENT_ID    = st.secrets["COGNITO_CLIENT_ID"]
client       = boto3.client('cognito-idp',region_name='us-east-2')

def main():
    
    wsize = None
    try:
        js_code     = """function getWindowSize() {return { width: window.innerWidth, height: window.innerHeight };}getWindowSize();"""
        window_size = streamlit_js_eval(js_expressions=js_code, key='window_size')
        wsize       = window_size['width']
    except: pass 

    #-------------------------------------------------------------------------#
    # Tamano de la pantalla 
    colorlogo  = "negativo"
    background = """
    .stApp {
        background-color: #fff;        
        opacity: 1;
        background-size: cover;
    }
    """
    housepng = 'https://iconsapp.nyc3.digitaloceanspaces.com/house-black.png'
    if wsize is not None:
        if wsize>1000:
            colorlogo  = "positivo"
            background = """
            .stApp {
                background: linear-gradient(to right, #000 50%, #FFF 50%);
            }
            """
            housepng = 'https://iconsapp.nyc3.digitaloceanspaces.com/house-white.png'
    style(background,housepng)
    
    #-------------------------------------------------------------------------#
    # Variables
    formato = {
                'login':True,
                'signin':False,
                'forgot':False,
                'access':False,
                'token':'',
                'signup_codigo':False,
                'forgot_codigo':False,
               }
    for key,value in formato.items():
        if key not in st.session_state: 
            st.session_state[key] = value
            
    if st.session_state.access is False:
        
        col1,col2,col3 = st.columns([0.5,0.25,0.25])
        with col1:
            st.markdown(f'<div class="centered-image"><img src="https://iconsapp.nyc3.digitaloceanspaces.com/urbex_{colorlogo}.png" width="350"></div>', unsafe_allow_html=True)
    
        if st.session_state.login:
            with col2:
                st.button('Registrarse',key='seccion_registro',on_click=button_signin)
            with col3:
                st.button('Cambiar o recuperar contraseña',on_click=button_forgot)

        if st.session_state.signin:
            with col2:
                st.button('Log in ',on_click=button_login)
            
        if st.session_state.forgot:
            with col2:
                st.button('Log in ',on_click=button_login)   
            with col3:
                st.button('Registrarse',key='seccion_registro',on_click=button_signin)

        col1, col2 = st.columns(2)
        colb1,colb2,colb3 = st.columns([0.5,0.25,0.25])
        if st.session_state.login:
            with col2:
                with st.form("login form"):
                    st.markdown("#### Log in")
                    email    = st.text_input("Email")
                    password = st.text_input("Password", type="password")
                    submit   = st.form_submit_button("Login")
                    
                if submit:
                    with st.spinner('Verificando'):
                        token,acceso_manual = datos_usuario(email)
                        controller = CookieController()
                        try: controller.remove("token")
                        except: pass
                        controller.set("token",f"{token}")

                        r = sign_in(email, password)
                        if r['status']==200 and acceso_manual:
                            st.success(r['message'])
                            st.session_state.access = True
                            st.session_state.login  = False
                            st.session_state.signin = False
                            st.session_state.forgot = False
                            st.rerun()
                        elif r['status']==200 and acceso_manual is False:
                            st.session_state.access = False
                            st.session_state.login  = True
                            st.session_state.signin = False
                            st.session_state.forgot = False
                            st.error('Usuario ya registrado pero sin acceso a Urbex, por favor ponerse en contacto con el equipo comercial')
                        else:
                            st.error(r['message'])

        if st.session_state.signin:
            with col2:
                with st.container():
                    st.markdown("#### Registro")
                    email    = st.text_input("Email").strip()
                    password = st.text_input("Password", type="password").strip()
                    nombre   = st.text_input("Nombre Completo").strip().title()
                    telefono = st.text_input("Celular",max_chars =10).strip()
                    
                    token = hashlib.md5()
                    token.update(email.encode('utf-8'))

                    if st.button("Registrarse",key='boton_registro'):
                        if isinstance(email, str) and email!='' and isinstance(password, str) and password!='':
                            r = sign_up(email, password)
                            if r['status']==200:
                                st.success(r['message'])
                                st.session_state.signup_codigo=True
                            else: 
                                st.error(r['message'])

                    codigo_verificacion = None
                    if st.session_state.signup_codigo:
                        codigo_verificacion = st.text_input("Código de verificación").strip()
                        
                    if isinstance(codigo_verificacion,str) and codigo_verificacion!='':
                        if st.button("Confirmar codigo"):
                            r = confirm_sign_up(email, codigo_verificacion)
                            if r['status']==200:
                                st.success(r['message'])
                                token    = token.hexdigest()
                                registro = pd.DataFrame([{'email':email,'nombre':nombre,'telefono':telefono,'token':token,'fecha_creacion':datetime.now().strftime('%Y-%m-%d'),'fecha_modificacion':datetime.now().strftime('%Y-%m-%d')}])
                                user_register(registro,email)
                                st.session_state.access = False
                                st.session_state.login  = True
                                st.session_state.signin = False
                                st.session_state.forgot = False
                                st.rerun()
                            else: 
                                st.error(r['message'])
              
        if st.session_state.forgot:
            with col2:
                email = st.text_input("Email")
                new_password = st.text_input("Nueva contraseña", type="password").strip()
                if st.button('Resetear contraseña'):
                    if isinstance(email, str) and email!='':
                        r = initiate_password_reset(email)
                        if r['status']==200:
                            st.success(r['message'])
                            st.session_state.forgot_codigo = True
                        else: 
                            st.error(r['message'])
                            
                codigo_verificacion = None
                if st.session_state.forgot_codigo:
                    codigo_verificacion = st.text_input("Código de verificación").strip()

                if isinstance(codigo_verificacion,str) and codigo_verificacion!='':
                    if st.button("Confirmar codigo"):
                        r = confirm_password_reset(email, codigo_verificacion, new_password)
                        if r['status']==200:
                            st.success(r['message'])
                            st.session_state.access = False
                            st.session_state.login  = True
                            st.session_state.signin = False
                            st.session_state.forgot = False
                            st.rerun()
                        else: 
                            st.error(r['message'])

def resend_code(email):
    try:
        response = client.resend_confirmation_code(
            ClientId=CLIENT_ID,
            Username=email
        )
        emailsend = response['CodeDeliveryDetails']['Destination']
        msn = f'Te enviamos a tu correo un código de verificación a {emailsend}!!!'
        status = 200
    except:
        msn = 'Hubo un problema para enviar el correo'
        status = 500
    return {'message': msn, 'status': status}

def sign_in(email, password):
    access = False
    try:
        client.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password
            }
        )
        access = True
        msn = 'Bienvenido a Urbex'
        status = 200
    except ClientError as e:
        if e.response['Error']['Code'] == 'UserNotConfirmedException':
            msn = 'Usuario registrado pero no confirmado, solicita un nuevo código para verificar'
            status = 403
        elif e.response['Error']['Code'] == 'NotAuthorizedException':
            msn = 'Contraseña incorrecta'
            status = 401
        elif e.response['Error']['Code'] == 'UserNotFoundException':
            msn = 'Usuario no encontrado'
            status = 404
        else:
            msn = 'Error desconocido'
            status = 500
    return {'access': access, 'message': msn, 'status': status}

def sign_up(email, password):
    try:
        response = client.sign_up(
            ClientId=CLIENT_ID,
            Username=email,
            Password=password,
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': email
                },
            ]
        )
        emailsend = response['CodeDeliveryDetails']['Destination']
        msn = f'Te enviamos a tu correo un código de verificación a {emailsend}!!!'
        status = 200
    except ClientError as e:
        if e.response['Error']['Code'] == 'UsernameExistsException':
            msn = 'Usuario ya registrado pero no confirmado, solicita un nuevo código para verificar'
            status = 403
        else:
            msn = 'Problema con el registro del usuario'
            status = 500
    return {'message': msn, 'status': status}

def confirm_sign_up(email, confirmation_code):
    try:
        client.confirm_sign_up(
            ClientId=CLIENT_ID,
            Username=email,
            ConfirmationCode=confirmation_code
        )
        msn = 'Código válido'
        status = 200
    except ClientError as e:
        if e.response['Error']['Code'] == 'CodeMismatchException':
            msn = 'Código no válido'
            status = 400
        elif e.response['Error']['Code'] == 'ExpiredCodeException':
            msn = 'El código ha expirado, solicita uno nuevo'
            status = 410
        else:
            msn = 'Usuario no encontrado'
            status = 404
    return {'message': msn, 'status': status}

def initiate_password_reset(email):
    try:
        response = client.forgot_password(
            ClientId=CLIENT_ID,
            Username=email
        )
        emailsend = response['CodeDeliveryDetails']['Destination']
        msn = f'Se envió un correo con el nuevo código a {emailsend}'
        status = 200
    except ClientError as e:
        if e.response['Error']['Code'] == 'UserNotFoundException':
            msn = 'Usuario no encontrado'
            status = 404
        else:
            msn = 'Problema para enviar el correo'
            status = 500
    return {'message': msn, 'status': status}

def confirm_password_reset(email, confirmation_code, new_password):
    try:
        client.confirm_forgot_password(
            ClientId=CLIENT_ID,
            Username=email,
            ConfirmationCode=confirmation_code,
            Password=new_password
        )
        msn = 'Se cambió la clave con éxito'
        status = 200
    except ClientError as e:
        if e.response['Error']['Code'] == 'CodeMismatchException':
            msn = 'Código no válido'
            status = 400
        elif e.response['Error']['Code'] == 'ExpiredCodeException':
            msn = 'El código ha expirado, solicita uno nuevo'
            status = 410
        else:
            msn = 'Problema para resetear la clave'
            status = 500
    return {'message': msn, 'status': status}
        
def user_register(data,email):
    engine   = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    df       = pd.read_sql_query(f"""SELECT * FROM {schema}.users WHERE email='{email}';""" , engine)
    if df.empty:
        try:
            data.to_sql('users', engine, if_exists='append', index=False, chunksize=1)
            response = 'Usuario registrado exitosamente'
            success  = True
        except:
            response = 'Por favor volver a registrarse'
            success  = False
    else:
        response = 'Usuario ya está registrado'
        success  = False
    engine.dispose()
    return response,success

def datos_usuario(email):
    token  = ""
    acceso = False
    engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{schema}')
    df     = pd.read_sql_query(f"""SELECT token,validate_email  FROM {schema}.users WHERE email='{email}';""" , engine)
    engine.dispose()
    if not df.empty:
        if df['validate_email'].iloc[0]==1:
            acceso = True
            token  = df['token'].iloc[0]
    return token,acceso
                    
def button_login():
    st.session_state.login  = True
    st.session_state.signin = False
    st.session_state.forgot = False

def button_signin():
    st.session_state.login  = False
    st.session_state.signin = True
    st.session_state.forgot = False
    
def button_forgot():
    st.session_state.login  = False
    st.session_state.signin = False
    st.session_state.forgot = True
  
def style(background,housepng):
    st.markdown(
        f"""
        <style>
        {background}             
        .centered-image {{
            display: flex;
            justify-content: center;
        }}   
        
        .stApp {{
            background-color: #fff;        
            opacity: 1;
            background-size: cover;
        }}
        
        div[data-testid="collapsedControl"] {{
            color: #000;
            }}
        
        div[data-testid="collapsedControl"] svg {{
            background-image: url('{housepng}');
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
        
        [data-testid="stMultiSelect"] {{
            border: 5px solid #F0F0F0;
            background-color: #F0F0F0;
            border-radius: 5px;
            padding: 5px; 
        }}
        
        [data-baseweb="select"] > div {{
            background-color: #fff;
        }}
        
        [data-testid="stTextInput"] {{
            border: 5px solid #F0F0F0;
            background-color: #F0F0F0;
            border-radius: 5px;
            padding: 5px; 
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
        }}
        
        [data-baseweb="input"] > div {{
            background-color: #fff;
        }}
        
        div[data-testid="stNumberInput-StepUp"]:hover {{
            background-color: #A16CFF;
        }}
        
        label[data-testid="stWidgetLabel"] p {{
            font-size: 14px;
            font-weight: bold;
            color: #3C3840;
            font-family: 'Aptos Narrow';
        }}
        
        </style>
        """,
        unsafe_allow_html=True
    )
    
if __name__ == "__main__":
    main()
