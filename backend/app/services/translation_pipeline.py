import logging
import asyncio
from typing import Optional
from .ai_models import ASRModel, NMTModel, TTSModel

logger = logging.getLogger(__name__)

class TranslationPipeline:
    def __init__(self):
        self.asr = ASRModel()
        self.nmt = NMTModel()
        self.tts = TTSModel()

    async def process_audio_chunk(self, audio_data: bytes, source_lang: str, target_lang: str):
        """
        Full S2ST pipeline with LID.
        Overall timeout of 60s as a safety net.
        """
        try:
            return await asyncio.wait_for(
                self._run_pipeline(audio_data, source_lang, target_lang),
                timeout=60.0
            )
        except asyncio.TimeoutError:
            logger.error("Pipeline timed out after 60 seconds!")
            return None
        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}", exc_info=True)
            return None

    async def _run_pipeline(self, audio_data: bytes, source_lang: str, target_lang: str):
        """Internal pipeline steps."""
        try:
            # 1. ASR + LID - Speech to Text with Auto-Detection
            asr_result = await self.asr.transcribe(audio_data, language=source_lang)
            text = asr_result.get("text", "")
            detected_lang = asr_result.get("language", "en")
            
            if not text or text.startswith("["):
                logger.warning(f"ASR returned empty or error text: '{text}'")
                return None
            
            logger.info(f"ASR Output: '{text}' (detected: {detected_lang})")

            # 2. NMT - Translate Text
            # Use detected language as source if auto was selected
            source_for_nmt = detected_lang if source_lang == "auto" else source_lang
            translated_text = await self.nmt.translate(text, source_for_nmt, target_lang)
            logger.info(f"NMT Output: '{translated_text}'")

            # 3. TTS - Text to Speech (synthesize in target language)
            audio_output = await self.tts.synthesize(translated_text, target_lang)
            logger.info(f"TTS Output: {len(audio_output)} bytes of audio")
            
            return {
                "original_text": text,
                "translated_text": translated_text,
                "detected_lang": detected_lang,
                "audio_output": audio_output
            }
        except Exception as e:
            logger.error(f"Pipeline step error: {str(e)}", exc_info=True)
            return None

# Singleton instance
pipeline = TranslationPipeline()
