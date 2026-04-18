# TalkNWear — AI-Powered Multilingual Communication Wearable

TalkNWear is a prototype system designed for real-time speech-to-speech translation across 22+ Indian languages. It features a hybrid edge-cloud architecture with government-grade encryption.

## Project Structure

- **/backend**: FastAPI server handling ASR, NMT, and TTS pipelines.
- **/frontend**: React (Vite) dashboard for real-time monitoring and configuration.
- **/edge**: Python scripts for the wearable hardware (Jetson Nano/Raspberry Pi) to stream audio securely.

## Technology Stack

- **Backend**: Python (FastAPI, WebSockets)
- **AI Models**: 
  - ASR: Whisper (OpenAI) / Vosk
  - NMT: IndicTrans2 (AI4Bharat)
  - TTS: IndicTTS / Matcha-TTS
- **Frontend**: React.js + Vanilla CSS (Glassmorphism UI)
- **Security**: AES-256 GCM Encryption for audio streams, JWT for auth.

## Getting Started

### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install -r requirements.txt
python -m app.main
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 3. Edge Wearable Simulation
```bash
cd edge
pip install websockets cryptography
python recorder.py
```

## AI Pipeline Workflow
1. **ASR**: Captures source language speech (e.g., Hindi) and transcribes to text.
2. **NMT**: Translates Hindi text to target language (e.g., English) using IndicTrans2.
3. **TTS**: Synthesizes the translated text back into natural-sounding speech.
4. **Encryption**: All audio data is encrypted using AES-256 before being sent over the secure WebSocket.

## Future Roadmap
- Integration of custom FPGA-based hardware for lower ASR latency.
- Support for offline emergency phrases via on-device 4-bit quantized models.
- Bone-conduction audio output for high-noise government environments.
