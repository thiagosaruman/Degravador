# app_web.py

import streamlit as st
import os
import time
import transcriber_core # Importa o motor central

# Configura o título e layout da página
st.set_page_config(page_title="Deepgram Transcriber", layout="wide")

st.title("🗣️ Degravador da Mari")
st.markdown("---")

# Widget de Upload de Arquivos
uploaded_file = st.file_uploader(
    "1. Arraste o arquivo de áudio ou vídeo (MP4, MP3, WAV) aqui:",
    type=['mp4', 'mov', 'mp3', 'wav', 'm4a', 'avi']
)

# Bloco de processamento
if uploaded_file is not None:
    
    # Define caminhos temporários
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, uploaded_file.name)
    
    try:
        # 1. Salva o arquivo temporariamente
        with open(temp_file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.success(f"Arquivo '{uploaded_file.name}' carregado.")
        
        if st.button("2. Iniciar Transcrição (Deepgram)"):
            
            with st.spinner("Processando na Nuvem... Isso pode levar alguns minutos para arquivos grandes."):
                
                # CHAMA O MOTOR CENTRAL COM O CAMINHO DO ARQUIVO TEMPORÁRIO
                inicio = time.time()
                resultado_formatado = transcriber_core.run_transcription(temp_file_path)
                
                tempo_gasto = time.time() - inicio
                
            st.markdown("---")
            
            # 3. Exibe o Resultado
            if resultado_formatado.startswith("❌"):
                st.error(f"Ocorreu um erro no processamento: {resultado_formatado}")
            else:
                st.success(f"Processamento concluído em {tempo_gasto:.2f} segundos!")
                
                st.subheader("Resultado da Transcrição:")
                st.code(resultado_formatado, language='text')

                # 4. Cria um botão para download do arquivo TXT
                st.download_button(
                    label="Baixar Transcrição (.txt)",
                    data=resultado_formatado,
                    file_name=f"{os.path.splitext(uploaded_file.name)[0]}.txt",
                    mime="text/plain"
                )
    
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {e}")

    finally:
        # 🚨 GARANTINDO A LIMPEZA 🚨
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                # Tenta remover a pasta temporária se estiver vazia
                if not os.listdir(temp_dir):
                    os.rmdir(temp_dir)
            except Exception as e:
                # O ideal é não mostrar erros de limpeza, mas manter para depuração
                print(f"Erro ao limpar arquivo temporário: {e}")

# Footer para lembrar o modelo
st.sidebar.info(f"Modelo: {transcriber_core.MODELO_DEEPGRAM} | API: Deepgram")