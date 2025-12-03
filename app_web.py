# app_web.py

import streamlit as st
import os
import time
import uuid # NOVO: Para criar nomes de arquivos únicos e seguros
import transcriber_core 

# Configura o título e layout da página
st.set_page_config(page_title="Deepgram Transcriber", layout="wide")

st.title("🗣️ Degravador da Mari")
st.markdown("---")

# Footer para lembrar o modelo (removido do bloco principal)
st.sidebar.info(f"Modelo: {transcriber_core.MODELO_DEEPGRAM} | API: Deepgram")

# Widget de Upload de Arquivos
uploaded_file = st.file_uploader(
    "1. Arraste o arquivo de áudio ou vídeo (MP4, MP3, WAV) aqui:",
    type=['mp4', 'mov', 'mp3', 'wav', 'm4a', 'avi']
)

# Bloco de processamento
if uploaded_file is not None:
    
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    
    # --- PASSO A PASSO DA CORREÇÃO ---
    
    # 1. Define o caminho do arquivo ORIGINAL com o nome original (apenas para salvar)
    original_file_path = os.path.join(temp_dir, uploaded_file.name)
    
    # 2. Define o caminho do arquivo SEGURO com um UUID
    unique_id = uuid.uuid4().hex
    original_ext = os.path.splitext(uploaded_file.name)[1]
    safe_file_path = os.path.join(temp_dir, f"safe_{unique_id}{original_ext}")

    try:
        # Salva o arquivo ORIGINAL no disco primeiro
        with open(original_file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Renomeia para o nome seguro antes de chamar o FFmpeg
        os.rename(original_file_path, safe_file_path)
        
        st.success(f"Arquivo '{uploaded_file.name}' carregado.")
        
        if st.button("2. Iniciar Degravação"):
            
            with st.spinner("Processando na Nuvem..."):
                
                # CHAMA O MOTOR CENTRAL COM O CAMINHO SEGURO
                inicio = time.time()
                resultado_formatado = transcriber_core.run_transcription(safe_file_path)
                
                tempo_gasto = time.time() - inicio
                
            st.markdown("---")
            
            # 3. Exibe o Resultado
            if resultado_formatado.startswith("❌"):
                st.error(f"Ocorreu um erro no processamento: {resultado_formatado}")
            else:
                st.success(f"Processamento concluído em {tempo_gasto:.2f} segundos!")
                st.subheader("Resultado da Transcrição:")
                st.code(resultado_formatado, language='text')

                # 4. Cria o botão de download com o nome original
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
        # Apaga o arquivo seguro (que foi renomeado)
        if os.path.exists(safe_file_path):
            try:
                os.remove(safe_file_path)
            except Exception as e:
                st.warning(f"Não foi possível limpar o arquivo temporário: {e}")

