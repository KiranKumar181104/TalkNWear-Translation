import React, { useState, useEffect, useRef } from 'react';
import './index.css';

const LANGUAGES = [
  { code: 'auto', name: 'Auto Detect', native: 'Auto' },
  { code: 'hi', name: 'Hindi', native: 'हिन्दी' },
  { code: 'bn', name: 'Bengali', native: 'বাংলা' },
  { code: 'ta', name: 'Tamil', native: 'தமிழ்' },
  { code: 'te', name: 'Telugu', native: 'తెలుగు' },
  { code: 'mr', name: 'Marathi', native: 'मরাठी' },
  { code: 'en', name: 'English', native: 'English' },
];

function App() {
  const [messages, setMessages] = useState([]);
  const [status, setStatus] = useState('offline');
  const [sourceLang, setSourceLang] = useState('auto');
  const [targetLang, setTargetLang] = useState('hi');
  const [isRecording, setIsRecording] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [detectedLang, setDetectedLang] = useState(null);
  
  const socket = useRef(null);
  const scrollRef = useRef(null);
  const mediaRecorder = useRef(null);
  const audioChunks = useRef([]);
  const thinkingTimeout = useRef(null);

  useEffect(() => {
    // Initialize WebSocket — use env var for deployed backend, fallback to localhost for dev
    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/stream';
    const ws = new WebSocket(wsUrl);
    socket.current = ws;

    ws.onopen = () => setStatus('online');
    ws.onclose = () => {
      setStatus('offline');
      setIsThinking(false); // Reset thinking if connection drops
      if (thinkingTimeout.current) clearTimeout(thinkingTimeout.current);
    };
    ws.onerror = () => {
      setIsThinking(false);
      if (thinkingTimeout.current) clearTimeout(thinkingTimeout.current);
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.status === 'success') {
        setIsThinking(false);
        if (thinkingTimeout.current) clearTimeout(thinkingTimeout.current);
        setMessages(prev => [...prev, {
          id: Date.now(),
          original: data.original_text,
          translated: data.translated_text,
          detected: data.detected_lang,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }]);
        
        if (data.detected_lang) {
          setDetectedLang(data.detected_lang);
        }

        // Automatic Voice Playback
        if (data.audio_response) {
          const audio = new Audio(`data:audio/mp3;base64,${data.audio_response}`);
          audio.play().catch(e => console.error("Audio playback failed:", e));
        }
      } else if (data.status === 'error') {
        setIsThinking(false);
        if (thinkingTimeout.current) clearTimeout(thinkingTimeout.current);
        setMessages(prev => [...prev, {
          id: Date.now(),
          original: '(Processing Failed)',
          translated: data.message || 'Error processing speech.',
          detected: 'error',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }]);
      }
    };

    return () => {
      if (thinkingTimeout.current) clearTimeout(thinkingTimeout.current);
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    };
  }, []);

  // Sync language configuration to backend whenever it changes
  useEffect(() => {
    if (socket.current && socket.current.readyState === WebSocket.OPEN) {
      const configPayload = {
        type: 'config',
        source_lang: sourceLang,
        target_lang: targetLang
      };
      socket.current.send(JSON.stringify(configPayload));
    }
  }, [sourceLang, targetLang, status]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isThinking]);

  const startRecording = async () => {
    if (status !== 'online') return;
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        } 
      });
      
      // Use standard webm sequence for broadest compatibility
      mediaRecorder.current = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      audioChunks.current = [];

      mediaRecorder.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.current.push(event.data);
        }
      };

      mediaRecorder.current.onstop = () => {
        const audioBlob = new Blob(audioChunks.current, { type: 'audio/webm' });
        if (socket.current && socket.current.readyState === WebSocket.OPEN) {
          socket.current.send(audioBlob);
          setIsThinking(true);
          // Safety timeout: if backend doesn't respond in 60s, reset
          if (thinkingTimeout.current) clearTimeout(thinkingTimeout.current);
          thinkingTimeout.current = setTimeout(() => {
            setIsThinking(false);
            setMessages(prev => [...prev, {
              id: Date.now(),
              original: '(No response from server)',
              translated: 'Backend may be processing slowly or waking up from sleep. Try again.',
              detected: 'timeout',
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            }]);
          }, 60000);
        }
        setIsRecording(false);
      };

      mediaRecorder.current.start();
      setIsRecording(true);
      setIsThinking(false);
      setDetectedLang(null);
    } catch (err) {
      console.error("Mic access denied:", err);
      alert("Microphone access is required for real-time translation.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorder.current && isRecording) {
      mediaRecorder.current.stop();
      mediaRecorder.current.stream.getTracks().forEach(track => track.stop());
    }
  };

  const clearMessages = () => {
    setMessages([]);
  };

  return (
    <div className="dashboard">
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '2rem', fontWeight: 600 }}>TalkNWear <span style={{ color: 'var(--primary)', fontSize: '1rem' }}>v1.0 Pro</span></h1>
          <p style={{ color: 'var(--text-muted)', margin: 0 }}>High-Fidelity Real-Time Dialect Translation</p>
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          {detectedLang && (
            <div className="status-badge" style={{ background: 'rgba(99, 102, 241, 0.2)', color: 'var(--primary)' }}>
              Detected: {detectedLang.toUpperCase()}
            </div>
          )}
          <div className={`status-badge ${status === 'online' ? 'status-online' : 'status-offline'}`}>
            {status === 'online' ? '● Engine Ready' : '○ Engine Offline'}
          </div>
        </div>
      </header>

      <div className="grid-layout">
        <main className="glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <h2 style={{ margin: 0 }}>Live Transcript</h2>
              {messages.length > 0 && (
                <button onClick={clearMessages} style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem', background: 'transparent', border: '1px solid var(--text-muted)', color: 'var(--text-muted)', borderRadius: '4px', cursor: 'pointer' }}>
                  Clear
                </button>
              )}
            </div>
            <div style={{ display: 'flex', gap: '1rem' }}>
              <div className="language-pill">{LANGUAGES.find(l => l.code === sourceLang).name}</div>
              <span style={{ color: 'var(--text-muted)' }}>→</span>
              <div className="language-pill">{LANGUAGES.find(l => l.code === targetLang).name}</div>
            </div>
          </div>

          <div className="transcript-area" ref={scrollRef}>
            {messages.length === 0 && !isThinking && (
              <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-muted)' }}>
                No active translation session. Hold the wearable button to talk.
              </div>
            )}
            {messages.map((msg) => (
              <React.Fragment key={msg.id}>
                <div className="message source">
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                    {msg.timestamp} • Original ({msg.detected || 'unknown'})
                  </div>
                  {msg.original}
                </div>
                <div className="message target">
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>Translated</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--secondary)' }}>{msg.translated}</div>
                </div>
              </React.Fragment>
            ))}
            {isThinking && (
              <div className="message system" style={{ fontStyle: 'italic', background: 'transparent', boxShadow: 'none' }}>
                <span className="typing-indicator">Analyzing dialect and slang...</span>
              </div>
            )}
          </div>
        </main>

        <aside>
          <section className="glass-card">
            <h3>Configuration</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Source language</label>
                <select 
                  value={sourceLang} 
                  onChange={(e) => setSourceLang(e.target.value)}
                >
                  {LANGUAGES.map(l => <option key={l.code} value={l.code}>{l.name} ({l.native})</option>)}
                </select>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Target language</label>
                <select 
                  value={targetLang} 
                  onChange={(e) => setTargetLang(e.target.value)}
                >
                  {LANGUAGES.map(l => <option key={l.code} value={l.code}>{l.name} ({l.native})</option>)}
                </select>
              </div>
            </div>
          </section>

          <section className="glass-card" style={{ textAlign: 'center', position: 'relative', overflow: 'hidden' }}>
            <h3>Wearable Simulation</h3>
            <div className="mic-rings">
              {isRecording && <><div className="ring"></div><div className="ring" style={{ animationDelay: '0.5s' }}></div><div className="ring" style={{ animationDelay: '1s' }}></div></>}
              <button 
                onMouseDown={startRecording}
                onMouseUp={stopRecording}
                onMouseLeave={stopRecording}
                disabled={status !== 'online'}
                style={{ 
                  width: '80px', 
                  height: '80px', 
                  borderRadius: '50%', 
                  background: isRecording ? 'var(--secondary)' : 'var(--primary)', 
                  border: 'none', 
                  color: 'white', 
                  cursor: 'pointer',
                  zIndex: 10,
                  transition: 'all 0.3s'
                }}
              >
                {isRecording ? 'Listening...' : 'Hold to Talk'}
              </button>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Hold down to record and release to translate
            </p>
          </section>

          <section className="glass-card">
            <h3>Hardware Status</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.9rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Battery Level</span>
                <span style={{ color: 'var(--secondary)' }}>84%</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Neural Engine Load</span>
                <span>12%</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Latency</span>
                <span>182ms</span>
              </div>
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}

export default App;
