# transcriber_core.py
# MOTOR CENTRAL DE TRANSCRIÇÃO (Versão Final e Estável)

import os
import sys
import time
import subprocess
import requests
import json

# ==============================================================================
# CONFIGURAÇÕES GLOBAIS
# ==============================================================================
# Sua chave Deepgram (Para acesso aos créditos de $200)
DEEPGRAM_API_KEY = "5f7e604041127c06320e8105cfb738b70c4c7fc8"
# Modelo para MÁXIMA precisão jurídica (mais lento, mas mais preciso)
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
    Extrai o áudio do vídeo usando FFmpeg, gerando um WAV/PCM universal.
    Isso corrige os erros de codec e sintaxe.
    """
    video_path = limpar_caminho(video_path)
    audio_path = video_path + ".temp.wav" 
    
    print("   ↳ 🔨 Extraindo áudio (WAV/PCM Universal)...")
    
    # Comando FFmpeg PCM: -acodec pcm_s16le (WAV, seguro para servidores Linux/Cloud)
    comando = (
        f'ffmpeg -i "{video_path}" -vn '
        f'-acodec pcm_s16le -ar 16000 -ac 1 ' 
        f'"{audio_path}" -y -loglevel error'
    )
    
    try:
        subprocess.run(comando, shell=True, check=True)
        return audio_path
    except:
        return None

def formatar_resultado_final(dados, arquivo_original):
    """
    Formata o JSON da Deepgram com o rastreamento do orador (PESSOA 1, PESSOA 2) 
    e adiciona quebras de linha para leitura fácil.
    """
    try:
        # Acessa a estrutura principal, com checagem de existência
        alternatives = dados.get('results', {}).get('channels', [{}])[0].get('alternatives', [{}])[0]
        sentences = alternatives.get('sentences')

        # === REDE DE SEGURANÇA para o erro 'sentences' ===
        if not sentences:
            # Tenta pegar o texto bruto em caso de erro na estrutura
            transcript = alternatives.get('transcript', "(Áudio silencioso ou inválido)")
            return f"❌ Erro de conteúdo: {transcript}"
        # ===============================================

        texto_final = []
        current_speaker = None
        buffer_text = ""
        buffer_time = 0

        # Processamento das sentenças (Lógica de Agrupamento)
        for sentence in sentences:
            speaker_id = sentence.get('speaker')
            
            if speaker_id != current_speaker and current_speaker is not None:
                if buffer_text:
                    numero_pessoa = current_speaker + 1
                    speaker_name = f"PESSOA {numero_pessoa}"
                    linha = f"[{formatar_tempo(buffer_time)}] {speaker_name}: {buffer_text.strip()}"
                    texto_final.append(linha)
                    texto_final.append("") # Quebra de linha dupla
                
                buffer_text = sentence['text']
                buffer_time = sentence['start']
                
            else:
                buffer_text += " " + sentence['text']
                if current_speaker is None:
                    buffer_time = sentence['start']
            
            current_speaker = speaker_id
            
        # Despejar o último buffer
        if buffer_text:
            numero_pessoa = current_speaker + 1
            speaker_name = f"PESSOA {numero_pessoa}"
            linha = f"[{formatar_tempo(buffer_time)}] {speaker_name}: {buffer_text.strip()}"
            texto_final.append(linha)
            
        conteudo_final = "\n".join(texto_final)
        return conteudo_final

    except Exception as e:
        # Erro geral de parse
        return f"❌ Erro na estrutura do JSON (parse): {e}"


def run_transcription(caminho_arquivo):
    """
    Motor principal chamado pelo app_cli.py ou app_web.py.
    """
    if not os.path.exists(caminho_arquivo):
        return f"❌ Erro: Arquivo não encontrado em {caminho_arquivo}"

    # Verifica se a biblioteca de requisições está presente
    try:
        import requests
    except ImportError:
        return "❌ ERRO: Biblioteca 'requests' faltando no ambiente."


    print(f"   ↳ Arquivo: {os.path.basename(caminho_arquivo)}")

    # 1. Preparação (Conversão e Envio)
    arquivo_para_enviar = extrair_audio_temporario(caminho_arquivo)
    
    # Sai se a extração falhar (erro de codec/ffmpeg)
    if not arquivo_para_enviar or not os.path.exists(arquivo_para_enviar):
        return "❌ ERRO CRÍTICO: Falha na extração de áudio do FFmpeg. Arquivo corrompido ou codec inválido."

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
        # 4. Limpeza (Apaga o WAV temporário)
        if arquivo_para_enviar.endswith(".temp.wav") and os.path.exists(arquivo_para_enviar):
            try:
                os.remove(arquivo_para_enviar)
            except:
                pass


if __name__ == "__main__":
    # O bloco principal para uso local (app_cli.py)
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
