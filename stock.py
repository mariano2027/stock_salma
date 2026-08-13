import streamlit as st
import pandas as pd
import io
import os
from datetime import datetime
import pytz

st.set_page_config(page_title="Filtro de Inventario - Stock Salma", layout="wide")
st.title("📦 Panel de Filtrado de Inventario - Stock Salma")

# Nombre del archivo fijo en la carpeta
ARCHIVO_FIJO = "inventario.xlsx"

# --- FUNCIÓN LOCAL PARA LEER LA FECHA REAL DEL ARCHIVO ---
def obtener_fecha_archivo_local(ruta):
    try:
        # Obtenemos la fecha de última modificación física del archivo en el servidor
        timestamp = os.path.getmtime(ruta)
        fecha_utc = datetime.fromtimestamp(timestamp, tz=pytz.utc)
        
        # Configuramos la zona horaria de Argentina
        zona_horaria = pytz.timezone('America/Buenos_Aires')
        fecha_local = fecha_utc.astimezone(zona_horaria)
        
        return fecha_local.strftime("%d/%m/%Y a las %H:%M hs")
    except Exception:
        return "Fecha no disponible"

# --- FUNCIÓN CON CACHÉ BASADO EN TIEMPO DE MODIFICACIÓN ---
# Si la fecha de modificación física en el disco cambia, el caché se rompe solo
try:
    mtime_clave = os.path.getmtime(ARCHIVO_FIJO)
except Exception:
    mtime_clave = None

@st.cache_data(ttl=10)
def cargar_inventario(ruta_archivo, hash_modificacion=None):
    return pd.read_excel(ruta_archivo)

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
        # Cargamos pasando el mtime_clave para asegurar actualización inmediata al reemplazar
        df = cargar_inventario(ARCHIVO_FIJO, hash_modificacion=mtime_clave)
        
        # Clonamos el DataFrame para no modificar el caché en memoria al normalizar columnas
        df = df.copy()
        df.columns = df.columns.str.strip()
        columnas_originales = list(df.columns)
        
        # Diccionario para mapear minúsculas con los nombres reales
        mapeo_columnas = {col.lower(): col for col in columnas_originales}
        
        # Validar columnas requeridas
        if 'producto' in mapeo_columnas and 'descripcion' in mapeo_columnas and 'stock' in mapeo_columnas:
            
            # --- MOSTRAR FECHA EXTRAÍDA DIRECTAMENTE DEL ARCHIVO LOCAL ---
            fecha_act = obtener_fecha_archivo_local(ARCHIVO_FIJO)
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

