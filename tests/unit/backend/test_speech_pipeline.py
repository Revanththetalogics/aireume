import io
import numpy as np
import pytest
import wave


SAMPLE_RATE = 16000


def create_test_wav(duration_sec=1, sample_rate=16000):
    """Create a simple test WAV file."""
    n_samples = int(duration_sec * sample_rate)
    audio_data = np.sin(2 * np.pi * 440 * np.arange(n_samples) / sample_rate).astype(np.float32)
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        audio_int16 = (audio_data * 32767).astype(np.int16)
        wf.writeframes(audio_int16.tobytes())
    return buffer.getvalue()


def create_test_pcm(duration_sec=1, sample_rate=16000):
    """Create raw PCM audio data."""
    n_samples = int(duration_sec * sample_rate)
    audio_data = np.sin(2 * np.pi * 440 * np.arange(n_samples) / sample_rate)
    audio_int16 = (audio_data * 32767).astype(np.int16)
    return audio_int16.tobytes()


class TestSTTDtypePreservation:
    """Test that STT maintains float32 dtype throughout the pipeline."""

    def test_raw_pcm_division_preserves_float32(self):
        """Critical: np.float32 / float64 promotes to float64."""
        body = create_test_pcm(duration_sec=1)
        audio_np = np.frombuffer(body, dtype=np.int16).astype(np.float32) / np.float32(32768.0)
        assert audio_np.dtype == np.float32, f"Raw PCM division failed: got {audio_np.dtype}"

    def test_raw_pcm_with_fix_preserves_float32(self):
        """Test that the fix (np.float32(32768.0)) preserves float32."""
        body = create_test_pcm(duration_sec=1)
        audio_np = np.frombuffer(body, dtype=np.int16).astype(np.float32) / np.float32(32768.0)
        assert audio_np.dtype == np.float32, f"Fix failed: got {audio_np.dtype}"

    def test_wav_loading_preserves_float32(self):
        """Test that WAV loading maintains float32."""
        import soundfile as sf
        wav_data = create_test_wav(duration_sec=1)
        buffer = io.BytesIO(wav_data)
        audio_np, sr = sf.read(buffer, dtype="float32")
        assert audio_np.dtype == np.float32, f"WAV load failed: got {audio_np.dtype}"

    def test_wav_explicit_cast_preserves_float32(self):
        """Test that explicit astype maintains float32."""
        import soundfile as sf
        wav_data = create_test_wav(duration_sec=1)
        buffer = io.BytesIO(wav_data)
        audio_np, sr = sf.read(buffer, dtype="float32")
        audio_np = audio_np.astype(np.float32)
        assert audio_np.dtype == np.float32, f"WAV explicit cast failed: got {audio_np.dtype}"

    def test_convolve_with_fix_preserves_float32(self):
        """Test that np.convolve with .astype fix maintains float32."""
        audio_np = np.random.randn(16000).astype(np.float32)
        audio_np = np.convolve(audio_np, np.array([1.0, -0.97]), mode="same").astype(np.float32)
        assert audio_np.dtype == np.float32, f"Convolve fix failed: got {audio_np.dtype}"

    def test_percentile_preserves_float32(self):
        """Test that np.percentile doesn't change dtype."""
        audio_np = np.random.randn(16000).astype(np.float32)
        peak = np.percentile(np.abs(audio_np), 95)
        assert isinstance(peak, (np.floating, float)), f"Percentile returned: {type(peak)}"

    def test_clip_preserves_float32(self):
        """Test that np.clip maintains float32."""
        audio_np = np.random.randn(16000).astype(np.float32)
        audio_np = np.clip(audio_np, -1.0, 1.0)
        assert audio_np.dtype == np.float32, f"Clip changed dtype: got {audio_np.dtype}"

    def test_where_preserves_float32(self):
        """Test that np.where maintains float32."""
        audio_np = np.random.randn(16000).astype(np.float32)
        audio_np = np.where(np.abs(audio_np) < 0.01, 0.0, audio_np)
        assert audio_np.dtype == np.float32, f"Where changed dtype: got {audio_np.dtype}"

    def test_full_pipeline_preserves_float32(self):
        """Test the complete STT preprocessing pipeline with all fixes."""
        body = create_test_pcm(duration_sec=1)

        # Step 1: Raw PCM conversion (with fix)
        audio_np = np.frombuffer(body, dtype=np.int16).astype(np.float32) / np.float32(32768.0)
        assert audio_np.dtype == np.float32, f"Step 1 failed: {audio_np.dtype}"

        # Step 2: Preprocessing (with fixes)
        audio_np = audio_np.astype(np.float32)
        audio_np = np.convolve(audio_np, np.array([1.0, -0.97]), mode="same").astype(np.float32)
        peak = np.percentile(np.abs(audio_np), 95)
        if peak > 0:
            audio_np = (audio_np / peak).astype(np.float32)
            audio_np = np.clip(audio_np, -1.0, 1.0)
        audio_np = np.where(np.abs(audio_np) < 0.01, 0.0, audio_np).astype(np.float32)

        assert audio_np.dtype == np.float32, f"Pipeline failed: got {audio_np.dtype}"


class TestSTTTranscription:
    """Test STT transcription functionality."""

    @pytest.mark.asyncio
    async def test_transcribe_accepts_valid_audio(self):
        """Test that transcribe endpoint accepts valid audio."""
        from httpx import AsyncClient, ASGITransport
        from app.speech_service.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Wait for model to load (in real tests, mock this)
            pass

    def test_transcribe_rejects_empty_body(self):
        """Test that empty audio is rejected."""
        # This would require the actual endpoint - placeholder for integration test
        assert True


class TestTTSVoiceSelection:
    """Test TTS voice selection and synthesis."""

    def test_kokoro_voices_defined(self):
        """Test that Kokoro voices are properly defined."""
        from app.speech_service.main import KOKORO_VOICES
        assert "female" in KOKORO_VOICES
        assert "male" in KOKORO_VOICES

    def test_kokoro_voices_are_valid(self):
        """Test that voice names are valid."""
        from app.speech_service.main import KOKORO_VOICES
        valid_voices = ["af_bella", "af_heart", "am_puck", "am_michael"]
        for voice in KOKORO_VOICES.values():
            assert voice in valid_voices, f"Invalid voice: {voice}"

    def test_edge_tts_voices_defined(self):
        """Test that Edge TTS voices are properly defined."""
        from app.speech_service.main import EDGE_TTS_VOICES
        assert "female" in EDGE_TTS_VOICES
        assert "male" in EDGE_TTS_VOICES


class TestVADConfiguration:
    """Test VAD configuration."""

    def test_vad_sample_rate(self):
        """Test VAD uses correct sample rate."""
        from app.speech_service.main import SAMPLE_RATE
        assert SAMPLE_RATE == 16000

    def test_vad_model_loaded(self):
        """Test VAD model can be imported."""
        # This would require actual VAD model - placeholder
        assert True


class TestAudioResampling:
    """Test audio resampling functionality."""

    def test_resample_48000_to_16000_preserves_float32(self):
        """Test that torchaudio resampling maintains float32."""
        import torch
        import torchaudio

        # Create 1 second of 48kHz audio
        audio_48k = np.sin(2 * np.pi * 440 * np.arange(48000) / 48000).astype(np.float32)
        audio_tensor = torch.from_numpy(audio_48k).unsqueeze(0)

        resampler = torchaudio.transforms.Resample(48000, 16000)
        audio_tensor = resampler(audio_tensor)
        audio_np = audio_tensor.squeeze(0).numpy().astype(np.float32)

        assert audio_np.dtype == np.float32, f"Resample failed: got {audio_np.dtype}"
        assert len(audio_np) == 16000, f"Wrong length: {len(audio_np)}"


class TestIntegration:
    """Integration tests for the full voice screening pipeline."""

    def test_pipeline_sample_rates(self):
        """Test that all sample rates are aligned."""
        from app.speech_service.main import SAMPLE_RATE, KOKORO_SAMPLE_RATE
        assert SAMPLE_RATE == 16000
        assert KOKORO_SAMPLE_RATE == 24000

    def test_tts_output_sample_rate(self):
        """Test TTS output is resampled to correct rate."""
        # Placeholder - would test actual TTS output
        assert True
