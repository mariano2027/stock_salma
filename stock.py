import streamlit as st
import pandas as pd
import io
import os
import requests
from datetime import datetime
import pytz

st.set_page_config(page_title="Filtro de Inventario - Stock Salma", layout="wide")
st.title("📦 Panel de Filtrado de Inventario - Stock Salma")

# --- CONFIGURACIÓN DE GITHUB ---
USUARIO_GITHUB = "mariano2027"
REPOSITORIO_GITHUB = "stock_salma"
# --------------------------------------------------------

# Nombre del archivo fijo en la carpeta
ARCHIVO_FIJO = "inventario.xlsx"

# --- FUNCIÓN PARA OBTENER LA FECHA DE ACTUALIZACIÓN DESDE GITHUB ---
def obtener_fecha_actualizacion(owner, repo, path):
    api_url = f"https://github.com{owner}/{repo}/commits?path={path}&page=1&per_page=1"
    try:
        response = requests.get(api_url)
        if response.status_code == 200:
            datos = response.json()
            if datos:
                fecha_iso = datos['commit']['committer']['date']
                fecha_utc = datetime.strptime(fecha_iso, "%Y-%m-%dT%H:%M:%SZ")
                # Configuramos la zona horaria de Argentina
                zona_horaria = pytz.timezone('America/Buenos_Aires')
                fecha_local = fecha_utc.replace(tzinfo=pytz.utc).astimezone(zona_horaria)
                return fecha_local.strftime("%d/%m/%Y a las %H:%M hs")
        return "Fecha no disponible"
    except Exception:
        return "Error al conectar con GitHub"

# --- NUEVA FUNCIÓN CON CACHÉ INTELIGENTE ---
@st.cache_data(ttl=10)
def cargar_inventario(ruta_archivo, commit_hash=None):
    return pd.read_excel(ruta_archivo)
# ------------------------------------------

# Obtener los datos del último commit en GitHub para romper el caché si el archivo cambió
commit_actual = None
try:
    api_url_commit = f"https://github.com{USUARIO_GITHUB}/{REPOSITORIO_GITHUB}/commits?path={ARCHIVO_FIJO}&page=1&per_page=1"
    res = requests.get(api_url_commit)
    if res.status_code == 200 and res.json():
        commit_actual = res.json()['sha']
except Exception:
    pass

# Inicializar estados para los filtros si no existen
if "prod_query" not in st.session_state:
    st.session_state.prod_query = ""
if "desc_query" not in st.session_state:
    st.session_state.desc_query = ""

# Función para limpiar los filtros
def limpiar_filtros():
    st.session_state.prod_query = ""
    st.session_state.desc_query = ""

# Verificar si el archivo existe en la carpeta
if os.path.exists(ARCHIVO_FIJO):
    try:
        # LLAMADO A LA FUNCIÓN (Pasamos commit_actual para forzar la actualización si el archivo cambió)
        df = cargar_inventario(ARCHIVO_FIJO, commit_hash=commit_actual)
        
        # Clonamos el DataFrame para no modificar el caché en memoria al normalizar columnas
        df = df.copy()
        df.columns = df.columns.str.strip()
        columnas_originales = list(df.columns)
        
        # Diccionario para mapear minúsculas con los nombres reales
        mapeo_columnas = {col.lower(): col for col in columnas_originales}
        
        # Validar columnas requeridas
        if 'producto' in mapeo_columnas and 'descripcion' in mapeo_columnas and 'stock' in mapeo_columnas:
            
            # --- MOSTRAR FECHA DE ACTUALIZACIÓN ARRIBA DE LOS FILTROS ---
            fecha_act = obtener_fecha_actualizacion(USUARIO_GITHUB, REPOSITORIO_GITHUB, ARCHIVO_FIJO)
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
            st.error("El archivo 'inventario.xlsx' debe contener las columnas: producto, descripcion y stock.")
            
    except Exception as e:
        st.error(f"Error al procesar el archivo base: {e}")
else:
    st.error(f"⚠️ No se encontró el archivo '{ARCHIVO_FIJO}' en la carpeta del proyecto. Por favor, subilo a tu repositorio de GitHub junto con el código.")
