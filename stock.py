import streamlit as st
import pandas as pd
import io
import requests
from datetime import datetime
import pytz

st.set_page_config(page_title="Filtro de Inventario - Stock Salma", layout="wide")
st.title("📦 Panel de Filtrado de Inventario - Stock Salma")

# --- CONEXIÓN DIRECTA A TU GOOGLE SHEETS ---
ID_PLANILLA = "1HeuyCFLjANNG7huXZHSWJ9iKAGiqlWvBeMYXk06iSZ0"
LINK_EXCEL = f"https://docs.google.com/spreadsheets/d/{ID_PLANILLA}/export?format=xlsx"

# --- FUNCIÓN PARA OBTENER LA FECHA DE ACTUALIZACIÓN DESDE GOOGLE DRIVE ---
def obtener_fecha_sheets(id_doc):
    # Usamos la API pública de Drive para ver la última modificación de la planilla
    api_url = f"https://googleapis.com{id_doc}?fields=modifiedTime"
    try:
        response = requests.get(api_url)
        if response.status_code == 200:
            fecha_iso = response.json().get("modifiedTime")
            if fecha_iso:
                # Quitamos la 'Z' final si existe y parseamos la fecha UTC
                fecha_clean = fecha_iso.replace("Z", "")
                fecha_utc = datetime.fromisoformat(fecha_clean[:19])
                
                # Configuramos la zona horaria de Argentina
                zona_horaria = pytz.timezone('America/Buenos_Aires')
                fecha_local = fecha_utc.replace(tzinfo=pytz.utc).astimezone(zona_horaria)
                return fecha_local.strftime("%d/%m/%Y a las %H:%M hs")
        return "Fecha no disponible"
    except Exception:
        return "Error al leer actualización"

# --- FUNCIÓN DE CARGA CON CACHÉ DE TIEMPO BAJO (10 SEGUNDOS) ---
@st.cache_data(ttl=10)
def cargar_inventario(url_planilla):
    return pd.read_excel(url_planilla)

# Inicializar estados para los filtros si no existen
if "prod_query" not in st.session_state:
    st.session_state.prod_query = ""
if "desc_query" not in st.session_state:
    st.session_state.desc_query = ""

# Función para limpiar los filtros
def limpiar_filtros():
    st.session_state.prod_query = ""
    st.session_state.desc_query = ""

try:
    # LLAMADO A LA FUNCIÓN EN VIVO
    df = cargar_inventario(LINK_EXCEL)
    
    # Clonamos el DataFrame para no modificar el caché en memoria al normalizar columnas
    df = df.copy()
    df.columns = df.columns.str.strip()
    columnas_originales = list(df.columns)
    
    # Diccionario para mapear minúsculas con los nombres reales
    mapeo_columnas = {col.lower(): col for col in columnas_originales}
    
    # Validar columnas requeridas
    if 'producto' in mapeo_columnas and 'descripcion' in mapeo_columnas and 'stock' in mapeo_columnas:
        
        # --- MOSTRAR FECHA AUTOMÁTICA EN TIEMPO REAL ---
        fecha_act = obtener_sheets_date = obtener_fecha_sheets(ID_PLANILLA)
        st.info(f"🕒 **Última actualización del stock:** {fecha_act} (Hora de Argentina)")
        
        # Crear tres columnas visuales para los inputs y el botón de reset
        col1, col2, col3 = st.columns(3)
        
        with col1:
            buscar_producto = st.text_input("Filtrar por Producto / Código:", key="prod_query")
        with col2:
            buscar_desc = st.text_input("Filtrar por Descripción:", key="desc_query")
        with col3:
            st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
            st.button("🔄 Resetear Filtros", on_click=limpiar_filtros, use_container_width=True)
        
        # Obtener los nombres reales de las columnas en el Excel
        col_prod_real = mapeo_columnas['producto']
        col_desc_real = mapeo_columnas['descripcion']
        
        # Aplicar filtros
        filtro_prod = df[col_prod_real].astype(str).str.contains(buscar_producto, case=False, na=False)
        filtro_desc = df[col_desc_real].astype(str).str.contains(buscar_desc, case=False, na=False)
        
        df_filtrado = df[filtro_prod & filtro_desc]
        
        # Mostrar métricas y la tabla de resultados
        st.subheader(f"Resultados encontrados: {len(df_filtrado)}")
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
        
        # --- Configuración de la Descarga ---
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_filtrado.to_excel(writer, index=False, sheet_name='Inventario Filtrado')
        
        buffer.seek(0)
        
        # Botón de descarga
        st.download_button(
            label="📥 Descargar Excel Filtrado",
            data=buffer,
            file_name="inventario_filtrado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=False
        )
        
    else:
        st.error("La planilla de Google debe contener las columnas: Producto, Descripcion y Stock.")
        
except Exception as e:
    st.error(f"Error al conectar con la planilla de Google: {e}")
