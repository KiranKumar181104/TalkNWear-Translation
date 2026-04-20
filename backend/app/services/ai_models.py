import asyncio
import os
import tempfile
import io
import logging
from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator
from gtts import gTTS

# Ensure ffmpeg binaries are in PATH for Whisper (Fixes Render missing ffmpeg)
import static_ffmpeg
static_ffmpeg.add_paths()

logger = logging.getLogger(__name__)

# Mapping from Whisper language codes to Google Translate language codes
# Whisper sometimes returns codes that Google Translate doesn't understand
WHISPER_TO_GOOGLE = {
    "zh": "zh-CN",
    "jw": "jv",
    "nn": "no",  # Norwegian Nynorsk -> Norwegian
    "nb": "no",  # Norwegian Bokmål -> Norwegian
    "sr": "sr",
    "he": "iw",  # Hebrew
    "tl": "tl",  # Filipino/Tagalog
}

# Languages supported by Google Translate (subset we care about)
GOOGLE_SUPPORTED = {
    'af', 'sq', 'am', 'ar', 'hy', 'as', 'ay', 'az', 'bm', 'eu', 'be', 'bn',
    'bho', 'bs', 'bg', 'ca', 'ceb', 'ny', 'zh-CN', 'zh-TW', 'co', 'hr', 'cs',
    'da', 'dv', 'doi', 'nl', 'en', 'eo', 'et', 'ee', 'tl', 'fi', 'fr', 'fy',
    'gl', 'ka', 'de', 'el', 'gn', 'gu', 'ht', 'ha', 'haw', 'iw', 'hi', 'hmn',
    'hu', 'is', 'ig', 'ilo', 'id', 'ga', 'it', 'ja', 'jw', 'kn', 'kk', 'km',
    'rw', 'gom', 'ko', 'kri', 'ku', 'ckb', 'ky', 'lo', 'la', 'lv', 'ln', 'lt',
    'lg', 'lb', 'mk', 'mai', 'mg', 'ms', 'ml', 'mt', 'mi', 'mr', 'mni-Mtei',
    'lus', 'mn', 'my', 'ne', 'no', 'or', 'om', 'ps', 'fa', 'pl', 'pt', 'pa',
    'qu', 'ro', 'ru', 'sm', 'sa', 'gd', 'nso', 'sr', 'st', 'sn', 'sd', 'si',
    'sk', 'sl', 'so', 'es', 'su', 'sw', 'sv', 'tg', 'ta', 'tt', 'te', 'th',
    'ti', 'ts', 'tr', 'tk', 'ak', 'uk', 'ur', 'ug', 'uz', 'vi', 'cy', 'xh',
    'yi', 'yo', 'zu'
}


def normalize_lang_code(whisper_code: str) -> str:
    """Convert a Whisper language code to a Google Translate-compatible code."""
    if not whisper_code:
        return "en"
    code = whisper_code.lower().strip()
    # Check explicit mapping first
    if code in WHISPER_TO_GOOGLE:
        return WHISPER_TO_GOOGLE[code]
    # Check if already valid for Google
    if code in GOOGLE_SUPPORTED:
        return code
    # Fallback: try the first 2 chars
    if len(code) > 2 and code[:2] in GOOGLE_SUPPORTED:
        return code[:2]
    # Ultimate fallback
    logger.warning(f"Unknown language code '{code}' from Whisper, falling back to 'en'")
    return "en"


class ASRModel:
    def __init__(self, model_size="base"):
        # 'base' model for better dialect/slang recognition
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    async def transcribe(self, audio_data: bytes, language: str = None) -> dict:
        """
        Transcribes audio data and automatically identifies the language.
        """
        tmp_path = None
        try:
            # Save binary to temporary file for Whisper to read
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
                tmp.write(audio_data)
                tmp_path = tmp.name

            logger.info(f"Saved {len(audio_data)} bytes to {tmp_path}")

            # Helper that runs BOTH transcribe and segment iteration in one thread call.
            # This is critical because model.transcribe() returns a lazy generator -
            # the actual heavy computation happens during list(segments), NOT during
            # the transcribe() call itself. Both must be inside the timeout.
            def _transcribe_and_collect(path, beam, lang):
                segments, info = self.model.transcribe(
                    path, beam_size=beam, language=lang
                )
                segment_list = list(segments)  # This is where real work happens
                text = "".join([s.text for s in segment_list])
                return text, info

            text, info = await asyncio.wait_for(
                asyncio.to_thread(
                    _transcribe_and_collect,
                    tmp_path,
                    5,
                    None if language == "auto" else language
                ),
                timeout=30.0
            )

            detected_lang = info.language
            
            logger.info(f"Whisper detected language: '{detected_lang}' (prob: {info.language_probability:.2f}), text: '{text.strip()}'")
            
            # Normalize the language code for downstream use
            normalized_lang = normalize_lang_code(detected_lang)
            
            return {
                "text": text.strip(),
                "language": normalized_lang,
                "raw_language": detected_lang,
                "probability": info.language_probability
            }
        except asyncio.TimeoutError:
            logger.error("ASR timed out after 30 seconds")
            return {"text": "", "language": "en", "raw_language": "timeout"}
        except Exception as e:
            logger.error(f"ASR Error: {str(e)}")
            return {"text": "", "language": "en", "raw_language": "error"}
        finally:
            # Always cleanup temp file
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except:
                    pass

class NMTModel:
    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        try:
            # Normalize both source and target language codes
            src = normalize_lang_code(source_lang)
            tgt = normalize_lang_code(target_lang)
            
            # Skip translation if source and target are the same
            if src == tgt:
                return text
            
            logger.info(f"Translating: src='{src}', tgt='{tgt}', text='{text[:50]}...'")
            
            translated = await asyncio.wait_for(
                asyncio.to_thread(
                    GoogleTranslator(source=src, target=tgt).translate, 
                    text
                ),
                timeout=15.0
            )
            return translated or text
        except Exception as e:
            logger.error(f"NMT Error: {str(e)}")
            # On translation failure, return the original text so the pipeline doesn't break
            return text

class TTSModel:
    async def synthesize(self, text: str, language: str) -> bytes:
        """
        Synthesizes text to speech using gTTS.
        returns: binary audio data (MP3)
        """
        try:
            tgt = normalize_lang_code(language)
            logger.info(f"TTS: Synthesizing '{text[:50]}...' in language '{tgt}'")
            audio_fp = io.BytesIO()
            tts = await asyncio.wait_for(
                asyncio.to_thread(gTTS, text=text, lang=tgt),
                timeout=15.0
            )
            await asyncio.to_thread(tts.write_to_fp, audio_fp)
            return audio_fp.getvalue()
        except Exception as e:
            logger.error(f"TTS Synthesis error: {str(e)}")
            return b""
