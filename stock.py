import streamlit as st
import pandas as pd
import io
import os
import time
from datetime import datetime
import pytz

st.set_page_config(page_title="Filtro de Inventario - Stock Salma", layout="wide")
st.title("📦 Panel de Filtrado de Inventario - Stock Salma")

# Nombre del archivo fijo en la carpeta
ARCHIVO_FIJO = "inventario.xlsx"

# --- FUNCIÓN LECTURA CON TRUCO DE CACHÉ FORZADO ---
@st.cache_data(ttl=5)
def cargar_inventario_seguro(ruta_archivo, marcador_tiempo):
    return pd.read_excel(ruta_archivo)

# Creamos un identificador único basado en la hora UTC actual para refrescar la memoria
marcador_actual = time.strftime("%Y%m%d-%H%M")

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
        # Cargamos el archivo inyectando el marcador único de tiempo
        df = cargar_inventario_seguro(ARCHIVO_FIJO, marcador_tiempo=marcador_actual)
        
        # Clonamos el DataFrame para no modificar el caché en memoria al normalizar columnas
        df = df.copy()
        df.columns = df.columns.str.strip()
        columnas_originales = list(df.columns)
        
        # Diccionario para mapear minúsculas con los nombres reales
        mapeo_columnas = {col.lower(): col for col in columnas_originales}
        
        # Validar columnas requeridas
        if 'producto' in mapeo_columnas and 'descripcion' in mapeo_columnas and 'stock' in mapeo_columnas:
            
            # --- CORRECCIÓN DE HORA EN VIVO (ZONA HORARIA ARGENTINA) ---
            zona_horaria = pytz.timezone('America/Argentina/Buenos_Aires')
            hora_local = datetime.now(zona_horaria)
            hora_formateada = hora_local.strftime("%d/%m/%Y a las %H:%M hs")
            
            st.info(f"🕒 **Panel conectado al Excel en vivo.** Información sincronizada al {hora_formateada} (Hora de Argentina).")
            
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

