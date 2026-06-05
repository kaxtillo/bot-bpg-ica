#!/usr/bin/env python3
"""
Script de transcripción de audio para el agente BPG.
Integración con OpenClaw: usa Google STT (gratuito) o Whisper API (con clave).
"""

import speech_recognition as sr
import os
import sys
import subprocess

def convert_to_wav(audio_path):
    """Convert any audio to WAV 16kHz mono for processing."""
    wav_path = audio_path + ".converted.wav"
    subprocess.run([
        "ffmpeg", "-y", "-i", audio_path,
        "-ar", "16000", "-ac", "1", wav_path
    ], capture_output=True)
    if os.path.exists(wav_path) and os.path.getsize(wav_path) > 1000:
        return wav_path
    return None

def transcribe_audio(audio_path):
    """
    Transcribe audio file using Google STT (free, no API key needed).
    Returns transcript text or error message.
    """
    if not os.path.exists(audio_path):
        return f"Error: archivo no encontrado: {audio_path}"
    
    recognizer = sr.Recognizer()
    
    # Convert to WAV if needed
    if not audio_path.endswith('.wav'):
        print(f"Convertiendo a WAV...", file=sys.stderr)
        wav = convert_to_wav(audio_path)
        if not wav:
            return "Error: no se pudo convertir el audio"
        audio_path = wav
    
    with sr.AudioFile(audio_path) as source:
        print(f"Leyendo audio...", file=sys.stderr)
        audio = recognizer.record(source)
    
    try:
        print(f"Enviando a Google STT (es-CO)...", file=sys.stderr)
        text = recognizer.recognize_google(audio, language="es-CO")
        return text
    except sr.UnknownValueError:
        # Try English as fallback
        try:
            text = recognizer.recognize_google(audio, language="en-US")
            return text
        except:
            return "No se pudo reconocer el audio"
    except sr.RequestError as e:
        return f"Error de conexión: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Check for media inbound files
        media_dir = "/home/ubuntu/.openclaw/media/inbound"
        ogg_files = [f for f in os.listdir(media_dir) if f.endswith('.ogg')] if os.path.isdir(media_dir) else []
        if ogg_files:
            latest = max([os.path.join(media_dir, f) for f in ogg_files], key=os.path.getmtime)
            print(f"Usando último audio: {latest}", file=sys.stderr)
            sys.argv.append(latest)
        else:
            print("Uso: python3 transcribe.py <archivo_audio>")
            sys.exit(1)
    
    result = transcribe_audio(sys.argv[1])
    print(result)
