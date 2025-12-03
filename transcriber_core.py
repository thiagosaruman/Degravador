# transcriber_core.py
# MOTOR CENTRAL DE TRANSCRIÇÃO (Versão Final Otimizada)

import os
import sys
import time
import subprocess
import requests
import json

# ==============================================================================
# CONFIGURAÇÕES GLOBAIS (DEVE ESTAR NO TOPO)
# ==============================================================================
# Chave da Deepgram (Seus créditos de $200)
DEEPGRAM_API_KEY = "5f7e604041127c06320e8105cfb738b70c4c7fc8"
# Modelo para máxima precisão jurídica
MODELO_DEEPGRAM = "whisper-large" 
# ==============================================================================

def limpar_caminho(caminho):
    return caminho.strip().replace('"', '')

def formatar_tempo(segundos):
    m, s = divmod(segundos, 60)
    h, m = divmod(m, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

def extrair_audio_temporario(video_path):
    """
    Função corrigida para FFmpeg. Usa o codec AAC, mais universal em nuvem.
    """
    video_path = limpar_caminho(video_path)
    audio_path = video_path + ".temp.mp3"
    
    # Comando FFmpeg com sintaxe limpa e explícita (Corrigindo erro 127)
    comando = (
        f'ffmpeg -i "{video_path}" -vn '
        f'-c:a aac -b:a 128k -ar 16000 -ac 1 '
        f'"{audio_path}" -y -loglevel error'
    )
    
    # Usamos o shell=True, mas com a sintaxe perfeita, o erro 127 deve sumir.
    subprocess.run(comando, shell=True, check=True)
    return audio_path


def formatar_resultado_final(dados, arquivo_original):
    """
    Formata o JSON da Deepgram em blocos de fácil leitura (PESSOA 1, PESSOA 2).
    """
    sentences = dados['results']['channels'][0]['alternatives'][0]['sentences']
    texto_final = []
    
    current_speaker = None
    buffer_text = ""
    buffer_time = 0

    for sentence in sentences:
        speaker_id = sentence.get('speaker')
        
        # Se o orador mudar (E não for o primeiro item)
        if speaker_id != current_speaker and current_speaker is not None:
            # 1. Despejar o bloco anterior
            if buffer_text:
                numero_pessoa = current_speaker + 1
                speaker_name = f"PESSOA {numero_pessoa}"
                linha = f"[{formatar_tempo(buffer_time)}] {speaker_name}: {buffer_text.strip()}"
                texto_final.append(linha)
                texto_final.append("") # Quebra de linha dupla para leitura
            
            # 2. Resetar o buffer para o novo orador
            buffer_text = sentence['text']
            buffer_time = sentence['start']
            
        else:
            # Acumula o texto
            buffer_text += " " + sentence['text']
            if current_speaker is None:
                buffer_time = sentence['start']
        
        current_speaker = speaker_id
        
    # Despejar o último buffer que sobrar
    if buffer_text:
        numero_pessoa = current_speaker + 1
        speaker_name = f"PESSOA {numero_pessoa}"
        linha = f"[{formatar_tempo(buffer_time)}] {speaker_name}: {buffer_text.strip()}"
        texto_final.append(linha)
        
    conteudo_final = "\n".join(texto_final)
    return conteudo_final

def run_transcription(caminho_arquivo):
    """
    Motor principal chamado pelo app_cli.py ou app_web.py.
    """
    if not os.path.exists(caminho_arquivo):
        return f"❌ Erro: Arquivo não encontrado em {caminho_arquivo}"

    # O PyInstaller (para o caso de usarmos) precisa do 'requests' instalado
    try:
        import requests
    except ImportError:
        return "❌ ERRO: Biblioteca 'requests' faltando no ambiente."


    print(f"   ↳ Arquivo: {os.path.basename(caminho_arquivo)}")

    # 1. Preparação (Conversão e Envio)
    arquivo_para_enviar = extrair_audio_temporario(caminho_arquivo)
    
    # 2. Conexão
    url = "https://api.deepgram.com/v1/listen"
    params = {
        "model": MODELO_DEEPGRAM, "language": "pt", "smart_format": "true",
        "diarize": "true", "paragraphs": "false", "punctuate": "true",
        "sentences": "true", "profanity_filter": "false" 
    }
    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}

    try:
        with open(arquivo_para_enviar, "rb") as audio:
            response = requests.post(url, params=params, headers=headers, data=audio, timeout=900)
        
        if response.status_code != 200:
            return f"❌ Erro {response.status_code} na Deepgram: {response.text}"

        dados = response.json()
        
        # 3. Formatação
        conteudo = formatar_resultado_final(dados, caminho_arquivo)
        
        return conteudo

    except Exception as e:
        return f"❌ Erro de conexão/processamento: {e}"
    finally:
        # 4. Limpeza (Apaga o MP3 temporário)
        if arquivo_para_enviar.endswith(".temp.mp3") and os.path.exists(arquivo_para_enviar):
            try:
                os.remove(arquivo_para_enviar)
            except:
                pass


if __name__ == "__main__":
    # Bloco CLI de uso local (se rodar app_cli.py)
    arquivos = sys.argv[1:]
    if not arquivos:
        print("💡 ARRASTE ARQUIVOS PARA O ÍCONE .BAT")
        input("Pressione Enter para sair...")
    else:
        print(f"🔌 Iniciando Deepgram...")
        for arq in arquivos:
            print(run_transcription(arq))
        print("\n🏁 Fim da fila.")
        time.sleep(3)

