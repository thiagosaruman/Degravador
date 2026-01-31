# app_web.py

import streamlit as st
import os
import time
import uuid
import transcriber_core 

st.set_page_config(page_title="Deepgram Transcriber", layout="wide")

st.title("🗣️ Degravador da Mari")
st.markdown("---")

st.sidebar.info(f"Modelo: {transcriber_core.MODELO_DEEPGRAM} | API: Deepgram")

# --- AJUSTE 1: ADICIONADO 'mkv' ---
uploaded_file = st.file_uploader(
    "1. Arraste o arquivo de áudio ou vídeo aqui:",
    type=['mp4', 'mkv', 'mov', 'mp3', 'wav', 'm4a', 'avi']
)

if uploaded_file is not None:
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Criamos o caminho seguro usando UUID para evitar conflitos de nomes iguais
    unique_id = uuid.uuid4().hex
    original_ext = os.path.splitext(uploaded_file.name)[1]
    safe_file_path = os.path.join(temp_dir, f"safe_{unique_id}{original_ext}")

    # Salva o arquivo temporariamente
    # Usamos o contexto 'with' para garantir que o arquivo seja fechado após a gravação
    if not os.path.exists(safe_file_path):
        with open(safe_file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

    st.success(f"Arquivo '{uploaded_file.name}' carregado e pronto.")
    
    # Botão para processar
    if st.button("2. Iniciar Degravação"):
        with st.spinner("Processando na Nuvem..."):
            try:
                inicio = time.time()
                # Chama o motor central
                resultado_formatado = transcriber_core.run_transcription(safe_file_path)
                tempo_gasto = time.time() - inicio
                
                st.markdown("---")
                
                if resultado_formatado.startswith("❌"):
                    st.error(f"Ocorreu um erro no processamento: {resultado_formatado}")
                else:
                    st.success(f"Processamento concluído em {tempo_gasto:.2f} segundos!")
                    st.subheader("Resultado da Transcrição:")
                    
                    # Área de texto para cópia rápida
                    st.text_area("Texto Transcrito:", value=resultado_formatado, height=400)

                    # Botão de download
                    st.download_button(
                        label="Baixar Transcrição (.txt)",
                        data=resultado_formatado,
                        file_name=f"{os.path.splitext(uploaded_file.name)[0]}.txt",
                        mime="text/plain"
                    )
            except Exception as e:
                st.error(f"Erro durante a transcrição: {e}")
            finally:
                # Limpeza imediata após o processamento do botão
                if os.path.exists(safe_file_path):
                    try:
                        os.remove(safe_file_path)
                    except:
                        pass
