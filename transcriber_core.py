# transcriber_core.py
# MOTOR CENTRAL DE TRANSCRIÇÃO - Versão Otimizada para Arquivos Grandes (+2GB)

import os
import subprocess
import requests
import time

# ==============================================================================
# CONFIGURAÇÕES GLOBAIS
# ==============================================================================
DEEPGRAM_API_KEY = "5f7e604041127c06320e8105cfb738b70c4c7fc8"
MODELO_DEEPGRAM = "whisper-large" 
PAUSE_THRESHOLD_SECONDS = 2.5 
# ==============================================================================

def limpar_caminho(caminho):
    return caminho.strip().replace('"', '')

def formatar_tempo(segundos):
    m, s = divmod(segundos, 60)
    h, m = divmod(m, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

def extrair_audio_temporario(video_path):
    """
    Usa FFmpeg para extrair áudio de qualquer formato (MKV, MP4, etc).
    Otimizado para não sobrecarregar o disco.
    """
    video_path = limpar_caminho(video_path)
    # Cria o nome do áudio baseado no caminho do vídeo para evitar conflitos
    audio_path = os.path.splitext(video_path)[0] + ".temp.wav"
    
    print(f"    ↳ 🔨 Extraindo áudio: {os.path.basename(video_path)}")
    
    # Comando FFmpeg PCM: Universal e aceito pela Deepgram
    comando = (
        f'ffmpeg -i "{video_path}" -vn '
        f'-acodec pcm_s16le -ar 16000 -ac 1 ' 
        f'"{audio_path}" -y -loglevel error'
    )
    
    try:
        subprocess.run(comando, shell=True, check=True)
        return audio_path
    except Exception as e:
        print(f"❌ Erro no FFmpeg: {e}")
        return None

def formatar_resultado_final(dados):
    """
    Processa o JSON da Deepgram e aplica a lógica de quebra por orador ou pausa.
    """
    try:
        results = dados.get('results', {})
        channels = results.get('channels', [{}])
        alternatives = channels[0].get('alternatives', [{}])[0]
        words = alternatives.get('words', [])

        if not words:
            transcript_bruto = alternatives.get('transcript', "(Áudio sem fala detectada)")
            return f"[00:00:00] GERAL: {transcript_bruto.strip()}"

        texto_final = []
        current_speaker = None
        buffer_words = []
        last_word_end_time = 0.0

        for word_data in words:
            speaker_id = word_data.get('speaker') 
            word_start = word_data['start']
            
            # Detecta mudança de orador ou pausa longa (2.5s)
            speaker_changed = (speaker_id != current_speaker and current_speaker is not None)
            long_pause = (word_start - last_word_end_time >= PAUSE_THRESHOLD_SECONDS)
            
            if speaker_changed or long_pause:
                if buffer_words:
                    first_time = buffer_words[0]['start']
                    s_name = f"PESSOA {current_speaker + 1}" if current_speaker is not None else "GERAL"
                    frase = ' '.join([w['punctuated_word'] for w in buffer_words])
                    texto_final.append(f"[{formatar_tempo(first_time)}] {s_name}: {frase}\n")
                
                buffer_words = [word_data]
            else:
                buffer_words.append(word_data)
            
            current_speaker = speaker_id
            last_word_end_time = word_data['end']
            
        # Último bloco
        if buffer_words:
            first_time = buffer_words[0]['start']
            s_name = f"PESSOA {current_speaker + 1}" if current_speaker is not None else "GERAL"
            frase = ' '.join([w['punctuated_word'] for w in buffer_words])
            texto_final.append(f"[{formatar_tempo(first_time)}] {s_name}: {frase}")
            
        return "\n".join(texto_final)

    except Exception as e:
        return f"❌ ERRO NA FORMATAÇÃO: {e}"

def run_transcription(caminho_arquivo):
    """
    Função principal chamada pelo app_web.py
    """
    if not os.path.exists(caminho_arquivo):
        return f"❌ Erro: Arquivo não encontrado."

    # 1. Extração
    arquivo_audio = extrair_audio_temporario(caminho_arquivo)
    
    if not arquivo_audio or not os.path.exists(arquivo_audio):
        return "❌ ERRO: Falha ao extrair áudio do vídeo."

    # 2. Configuração Deepgram
    url = "https://api.deepgram.com/v1/listen"
    params = {
        "model": MODELO_DEEPGRAM, 
        "language": "pt", 
        "smart_format": "true",
        "diarize": "true", 
        "punctuate": "true",
        "paragraphs": "false"
    }
    headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}

    try:
        # Enviando o áudio com timeout estendido para arquivos grandes
        with open(arquivo_audio, "rb") as audio:
            # Timeout de 1800 segundos (30 minutos)
            response = requests.post(url, params=params, headers=headers, data=audio, timeout=1800)
        
        if response.status_code != 200:
            return f"❌ Erro na Deepgram ({response.status_code}): {response.text}"

        # 3. Formatação
        return formatar_resultado_final(response.json())

    except Exception as e:
        return f"❌ Erro de processamento: {e}"
    finally:
        # 4. Limpeza rigorosa do áudio temporário
        if arquivo_audio and os.path.exists(arquivo_audio):
            try:
                os.remove(arquivo_audio)
            except:
                pass
