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
# Modelo para MÁXIMA precisão jurídica
MODELO_DEEPGRAM = "whisper-large" 
# NOVO: Pausa mínima em segundos para forçar uma quebra de parágrafo em monólogos
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
    Função corrigida para usar o codec WAV/PCM (universal e seguro para nuvem).
    """
    video_path = limpar_caminho(video_path)
    audio_path = video_path + ".temp.wav" 
    
    print("   ↳ 🔨 Extraindo áudio (WAV/PCM Universal)...")
    
    # Comando FFmpeg PCM: Garante sintaxe correta e codec universal
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
    Formata o JSON da Deepgram. Trata monólogos com quebra de parágrafo por pausa longa.
    """
    try:
        alternatives = dados.get('results', {}).get('channels', [{}])[0].get('alternatives', [{}])[0]
        sentences = alternatives.get('sentences')

        # === REDE DE SEGURANÇA: MODO MONÓLOGO/GERAL ===
        if not sentences:
            # Se a diarização falhou (sem oradores distintos), retorna o texto bruto [GERAL]
            transcript_bruto = alternatives.get('transcript', "(Áudio silencioso ou inválido)")
            words = alternatives.get('words')
            
            start_time_seconds = 0
            if words and len(words) > 0:
                start_time_seconds = words[0].get('start', 0)
            
            time_marker = formatar_tempo(start_time_seconds)
            conteudo_final = f"[{time_marker}] GERAL: {transcript_bruto.strip()}"
            return conteudo_final
        # ===============================================

        # === MODO DIÁLOGO E LEITURA FÁCIL ===
        texto_final = []
        current_speaker = None
        buffer_text = ""
        buffer_time = 0
        last_end_time = 0

        for sentence in sentences:
            speaker_id = sentence.get('speaker')
            sentence_start = sentence['start']
            
            speaker_changed = (speaker_id != current_speaker and current_speaker is not None)
            long_pause = (sentence_start - last_end_time >= PAUSE_THRESHOLD_SECONDS)
            
            # Condição para DESPEJAR o bloco anterior
            if speaker_changed or long_pause:
                if buffer_text:
                    numero_pessoa = current_speaker + 1
                    speaker_name = f"PESSOA {numero_pessoa}"
                    linha = f"[{formatar_tempo(buffer_time)}] {speaker_name}: {buffer_text.strip()}"
                    texto_final.append(linha)
                    texto_final.append("") # Quebra de linha dupla (Parágrafo)
                
                # Reseta o buffer
                buffer_text = sentence['text']
                buffer_time = sentence['start']
                
            else:
                # Acumula o texto
                buffer_text += " " + sentence['text']
                if current_speaker is None:
                    buffer_time = sentence['start']
            
            current_speaker = speaker_id
            last_end_time = sentence['end'] # Atualiza o tempo final para próxima comparação
            
        # Despejar o último buffer
        if buffer_text:
            numero_pessoa = current_speaker + 1
            speaker_name = f"PESSOA {numero_pessoa}"
            linha = f"[{formatar_tempo(buffer_time)}] {speaker_name}: {buffer_text.strip()}"
            texto_final.append(linha)
            
        conteudo_final = "\n".join(texto_final)
        return conteudo_final

    except Exception as e:
        # Se houver um erro estrutural real na API
        return f"❌ ERRO CRÍTICO NA ESTRUTURA DO JSON: {e}"


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
        return "❌ ERRO CRÍTICO: Falha na extração de áudio do FFmpeg. Verifique o log do Streamlit."

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
    # Bloco principal desativado para garantir que o Streamlit não rode o CLI
    pass
