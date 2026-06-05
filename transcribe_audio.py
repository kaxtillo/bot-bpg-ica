#!/usr/bin/env python3
"""
Transcribe audio files using faster-whisper (local, no API key).
Usage: python3 transcribe_audio.py <audio_file>
"""

import sys
import os
import json

def transcribe(audio_path):
    if not os.path.exists(audio_path):
        return f"Error: archivo no encontrado: {audio_path}"
    
    from faster_whisper import WhisperModel
    
    # Use small model (good balance of speed/accuracy, ~500MB download)
    model_size = "small"
    model_dir = os.path.expanduser("~/.cache/whisper")
    
    print(f"🔊 Cargando modelo Whisper {model_size}...", file=sys.stderr)
    
    # Run on CPU with int8
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    
    print(f"🎤 Transcribiendo: {os.path.basename(audio_path)}", file=sys.stderr)
    segments, info = model.transcribe(audio_path, beam_size=5, language="es")
    
    result = {
        "language": info.language,
        "duration_seconds": round(info.duration, 1),
        "segments": []
    }
    
    full_text = []
    for segment in segments:
        seg = {
            "start": round(segment.start, 2),
            "end": round(segment.end, 2),
            "text": segment.text.strip()
        }
        result["segments"].append(seg)
        full_text.append(segment.text.strip())
    
    result["full_text"] = " ".join(full_text)
    print(f"\n📝 Transcripción completa:\n", file=sys.stderr)
    print(result["full_text"])
    
    # Also save
    out_path = audio_path + ".transcript.txt"
    with open(out_path, "w") as f:
        f.write(result["full_text"])
    
    print(f"\n💾 Transcripción guardada en: {out_path}", file=sys.stderr)
    
    # Output JSON for tool consumption
    print(f"\n---JSON---\n{json.dumps(result, ensure_ascii=False)}", file=sys.stderr)
    
    return result["full_text"]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 transcribe_audio.py <archivo_audio>")
        sys.exit(1)
    
    transcribe(sys.argv[1])
