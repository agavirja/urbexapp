import streamlit as st
import time

from streamlit_cookies_controller import CookieController


v = st.selectbox('gasas',options=['A','B'])

if 'B' in v:
    controller = CookieController()
    controller.set('token','1223444444445566666')

controller = CookieController()
cookies    = controller.getAll()
st.write(cookies)


