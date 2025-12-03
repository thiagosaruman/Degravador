# transcriber_core.py
# MOTOR CENTRAL DE TRANSCRIÇÃO (Versão Final e Estável com Quebra por Pausa)

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
    # Garante que o tempo seja sempre inteiro e formatado
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
    Formata o JSON: Implementa quebra de parágrafo por PAUSA LONGA (2.5s) ou ORADOR.
    Usa a lista 'words' para timestamps e detecção de pausas em todos os modos.
    """
    try:
        alternatives = dados.get('results', {}).get('channels', [{}])[0].get('alternatives', [{}])[0]
        words = alternatives.get('words') # Lista de palavras é mais confiável que 'sentences'

        if not words:
            # Caso de áudio silencioso ou erro fatal
            transcript_bruto = alternatives.get('transcript', "(Áudio silencioso ou inválido)")
            return f"[00:00:00] GERAL: {transcript_bruto.strip()}"

        texto_final = []
        current_speaker = None
        buffer_words = []
        last_word_end_time = 0.0

        for word_data in words:
            # 'speaker' só estará presente se houver diarização, senão é None/0
            speaker_id = word_data.get('speaker') 
            word_start = word_data['start']
            
            # Condição 1: Orador Mudou (Quebra de Diálogo)
            speaker_changed = (speaker_id != current_speaker and current_speaker is not None)
            
            # Condição 2: Pausa Longa (Quebra de Parágrafo para Leitura Fácil)
            long_pause = (word_start - last_word_end_time >= PAUSE_THRESHOLD_SECONDS)
            
            # Condição para DESPEJAR o bloco anterior
            if speaker_changed or long_pause:
                if buffer_words:
                    # Formata e anexa o parágrafo anterior
                    first_word_time = buffer_words[0]['start']
                    
                    if current_speaker is None:
                        speaker_name = "GERAL"
                    else:
                        numero_pessoa = current_speaker + 1
                        speaker_name = f"PESSOA {numero_pessoa}"
                        
                    # Junta as palavras do buffer para formar a frase do parágrafo
                    linha = f"[{formatar_tempo(first_word_time)}] {speaker_name}: {' '.join([w['punctuated_word'] for w in buffer_words])}"
                    texto_final.append(linha)
                    texto_final.append("") # Quebra de linha dupla (Parágrafo)
                
                # Reseta o buffer com a palavra atual
                buffer_words = [word_data]
                
            else:
                # Acumula a palavra
                buffer_words.append(word_data)
            
            current_speaker = speaker_id
            last_word_end_time = word_data['end']
            
        # Despejar o último buffer
        if buffer_words:
            first_word_time = buffer_words[0]['start']
            
            if current_speaker is None:
                speaker_name = "GERAL"
            else:
                numero_pessoa = current_speaker + 1
                speaker_name = f"PESSOA {numero_pessoa}"
                
            linha = f"[{formatar_tempo(first_word_time)}] {speaker_name}: {' '.join([w['punctuated_word'] for w in buffer_words])}"
            texto_final.append(linha)
            
        conteudo_final = "\n".join(texto_final)
        return conteudo_final

    except Exception as e:
        return f"❌ ERRO CRÍTICO NA ESTRUTURA DO JSON (Final): {e}"


def run_transcription(caminho_arquivo):
    """
    Motor principal.
    """
    if not os.path.exists(caminho_arquivo):
        return f"❌ Erro: Arquivo não encontrado em {caminho_arquivo}"

    try:
        import requests
    except ImportError:
        return "❌ ERRO: Biblioteca 'requests' faltando no ambiente."


    print(f"   ↳ Arquivo: {os.path.basename(caminho_arquivo)}")

    # 1. Preparação (Conversão e Envio)
    arquivo_para_enviar = extrair_audio_temporario(caminho_arquivo)
    
    if not arquivo_para_enviar or not os.path.exists(arquivo_para_enviar):
        return "❌ ERRO CRÍTICO: Falha na extração de áudio do FFmpeg. Verifique o log do Streamlit."

    # 2. Conexão
    url = "https://api.deepgram.com/v1/listen"
    params = {
        "model": MODELO_DEEPGRAM, "language": "pt", "smart_format": "true",
        "diarize": "true", "paragraphs": "false", "punctuate": "true",
        "sentences": "true", "profanity_filter": "false", 
        "interim_results": "false" # Garante que a resposta só venha completa no final
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
    pass
