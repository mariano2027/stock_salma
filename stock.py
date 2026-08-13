import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Filtro de Inventario - Stock Salma", layout="wide")
st.title("📦 Panel de Filtrado de Inventario - Stock Salma")

# --- CONEXIÓN DIRECTA A TU GOOGLE SHEETS ---
ID_PLANILLA = "1HeuyCFLjANNG7huXZHSWJ9iKAGiqlWvBeMYXk06iSZ0"
LINK_EXCEL = f"https://google.com{ID_PLANILLA}/export?format=xlsx"

# --- FUNCIÓN DE CARGA GENERAL CON CACHÉ DE 10 SEGUNDOS ---
@st.cache_data(ttl=10)
def cargar_inventario_completo(url_planilla):
    return pd.read_excel(url_planilla)

try:
    # Traemos los datos completos desde la hoja de Google
    df_raw = cargar_inventario_completo(LINK_EXCEL)
    
    # Clonamos para manipulación de filtros
    df = df_raw.copy()
    df.columns = df.columns.str.strip()
    columnas_originales = list(df.columns)
    
    # Diccionario para mapear nombres reales de columnas en minúsculas
    mapeo_columnas = {col.lower(): col for col in columnas_originales}
    
    # Validar las columnas requeridas del stock
    if 'producto' in mapeo_columnas and 'descripcion' in mapeo_columnas and 'stock' in mapeo_columnas:
        
        # --- LECTURA INTELIGENTE DE FECHA (CELDA E2 / Fila 0, Columna 4) ---
        try:
            # Captura el valor que escribas en la celda E2 de tu Google Sheets
            fecha_act = str(df_raw.iloc[0, 4]).strip()
            if fecha_act == "nan" or fecha_act == "":
                fecha_act = "No especificada en planilla"
        except Exception:
            fecha_act = "Verificar celda E2 de la planilla"
            
        # Desplegar banner informativo con la fecha real ingresada
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
        
        # Filtrar stock (eliminando columnas extras de control como la E y la F si existieran)
        columnas_visibles = [mapeo_columnas['producto'], mapeo_columnas['descripcion'], mapeo_columnas['stock']]
        df_filtrado = df.loc[filtro_prod & filtro_desc, columnas_visibles]
        
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
