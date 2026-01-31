import streamlit as st
import os
import time
import uuid
import transcriber_core 

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="Deepgram Transcriber", 
    page_icon="🗣️",
    layout="wide"
)

# Estilo CSS para melhorar a visualização do texto
st.markdown("""
    <style>
    .stTextArea textarea {
        font-size: 16px !important;
        font-family: 'Helvetica', sans-serif !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🗣️ Degravador da Mari")
st.markdown("---")

# Sidebar com informações técnicas
st.sidebar.header("Configurações do Motor")
st.sidebar.info(f"**Modelo:** {transcriber_core.MODELO_DEEPGRAM}\n\n**API:** Deepgram Whisper")
st.sidebar.warning("⚠️ Arquivos grandes podem demorar alguns minutos para processar a extração de áudio.")

# 2. SELETOR DE ARQUIVOS (Agora com MKV e outros formatos)
uploaded_file = st.file_uploader(
    "1. Arraste o arquivo de áudio ou vídeo aqui (Limite: 3GB):",
    type=['mp4', 'mkv', 'mov', 'mp3', 'wav', 'm4a', 'avi', 'mpeg']
)

if uploaded_file is not None:
    # Definição de limites (3GB)
    LIMITE_GB = 3.0
    tamanho_atual_gb = uploaded_file.size / (1024**3)

    if tamanho_atual_gb > LIMITE_GB:
        st.error(f"❌ O arquivo é muito grande ({tamanho_atual_gb:.2f} GB). O limite do sistema é de {LIMITE_GB} GB.")
    else:
        # Preparação de diretórios e nomes seguros
        temp_dir = "temp_uploads"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        # Gerar um ID único para evitar que um arquivo sobrescreva outro de usuário diferente
        unique_id = uuid.uuid4().hex
        extensao = os.path.splitext(uploaded_file.name)[1]
        safe_file_path = os.path.join(temp_dir, f"video_{unique_id}{extensao}")

        # 3. SALVAMENTO EM DISCO (Protege a memória RAM para arquivos > 2GB)
        # O arquivo só é gravado se ainda não existir no diretório temp
        if not os.path.exists(safe_file_path):
            with st.status("Preparando arquivo para processamento...", expanded=False) as status:
                try:
                    with open(safe_file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    status.update(label="Arquivo carregado com sucesso!", state="complete")
                except Exception as e:
                    st.error(f"Erro ao gravar arquivo no disco: {e}")

        st.info(f"📁 **Arquivo:** {uploaded_file.name} | **Tamanho:** {tamanho_atual_gb*1024:.1f} MB")
        
        # 4. BOTÃO DE AÇÃO
        if st.button("2. Iniciar Transcrição Completa", type="primary"):
            
            # Espaço para o resultado
            container_resultado = st.container()
            
            with st.spinner("O FFmpeg está extraindo o áudio e a Deepgram processando o texto... aguarde."):
                inicio_cronometro = time.time()
                
                # Chama o motor central (transcriber_core.py)
                resultado = transcriber_core.run_transcription(safe_file_path)
                
                tempo_total = time.time() - inicio_cronometro

            st.markdown("---")

            # 5. EXIBIÇÃO E DOWNLOAD
            if resultado.startswith("❌"):
                st.error(f"Falha no processamento: {resultado}")
            else:
                st.success(f"Transcrição concluída em {tempo_total:.1f} segundos!")
                
                st.subheader("Conteúdo da Transcrição:")
                # Text area permite que a Mari edite ou copie o texto facilmente
                texto_editavel = st.text_area(
                    label="Você pode ajustar o texto abaixo antes de baixar:",
                    value=resultado,
                    height=500
                )

                # Botão de Download
                nome_download = f"Transcricao_{os.path.splitext(uploaded_file.name)[0]}.txt"
                st.download_button(
                    label="💾 Baixar Arquivo .txt",
                    data=texto_editavel,
                    file_name=nome_download,
                    mime="text/plain",
                    use_container_width=True
                )
        
        # 6. LIMPEZA DE SEGURANÇA
        # Removemos o arquivo original para não lotar o servidor após o uso
        # (Opcional: você pode deixar para um script de limpeza agendada)
        if 'resultado' in locals():
             if os.path.exists(safe_file_path):
                try:
                    os.remove(safe_file_path)
                except:
                    pass

else:
    st.write("Aguardando upload de arquivo...")

# Rodapé simples
st.markdown("---")
st.caption("Desenvolvido para uso jurídico e transcrições de alta precisão.")
