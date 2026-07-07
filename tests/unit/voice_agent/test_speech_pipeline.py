"""Unit tests for voice-agent sentence streaming and barge-in helpers."""
import pytest

from app.voice_agent.speech_pipeline import PlaybackGate, barge_in, split_sentences, speak_text


class TestSplitSentences:
    def test_empty(self):
        assert split_sentences("") == []
        assert split_sentences("   ") == []

    def test_single_sentence(self):
        assert split_sentences("Hello there.") == ["Hello there."]

    def test_multiple_sentences(self):
        text = "Hi. How are you? I am fine!"
        assert split_sentences(text) == ["Hi.", "How are you?", "I am fine!"]

    def test_no_trailing_space_after_punctuation(self):
        assert split_sentences("One.Two") == ["One.Two"]


class TestPlaybackGate:
    def test_defaults(self):
        gate = PlaybackGate()
        assert gate.is_playing is False
        assert gate.cancelled is False

    def test_cancel_and_reset(self):
        gate = PlaybackGate()
        gate.cancel()
        assert gate.cancelled is True
        gate.reset()
        assert gate.cancelled is False


class TestSpeakText:
    @pytest.mark.asyncio
    async def test_skips_empty_text(self):
        gate = PlaybackGate()
        calls = []

        async def fake_publish(*args, **kwargs):
            calls.append(args)

        class FakeSpeech:
            async def synthesize(self, text, voice="female"):
                return b"audio"

        await speak_text("", FakeSpeech(), None, None, fake_publish, gate)
        assert calls == []

    @pytest.mark.asyncio
    async def test_publishes_each_sentence(self):
        gate = PlaybackGate()
        synthesized = []
        published = []

        class FakeSpeech:
            async def synthesize(self, text, voice="female"):
                synthesized.append(text)
                return f"{text}-audio".encode()

        async def fake_publish(room, source, audio, rate, playback_gate):
            published.append((audio.decode(), rate))

        await speak_text(
            "First. Second!",
            FakeSpeech(),
            "room",
            "source",
            fake_publish,
            gate,
            sample_rate=16000,
        )
        assert synthesized == ["First.", "Second!"]
        assert published == [("First.-audio", 16000), ("Second!-audio", 16000)]
        assert gate.is_playing is False

    @pytest.mark.asyncio
    async def test_stops_when_cancelled_mid_playback(self):
        gate = PlaybackGate()
        synthesized = []

        class FakeSpeech:
            async def synthesize(self, text, voice="female"):
                synthesized.append(text)
                if text == "First.":
                    gate.cancel()
                return b"audio"

        async def fake_publish(*args, **kwargs):
            return None

        await speak_text(
            "First. Second.",
            FakeSpeech(),
            None,
            None,
            fake_publish,
            gate,
        )
        assert synthesized == ["First."]


class TestBargeIn:
    @pytest.mark.asyncio
    async def test_no_op_when_not_playing(self):
        gate = PlaybackGate()
        await barge_in(gate, settle_ms=0)
        assert gate.cancelled is False

    @pytest.mark.asyncio
    async def test_cancels_when_playing(self):
        gate = PlaybackGate()
        gate.is_playing = True
        await barge_in(gate, settle_ms=0)
        assert gate.cancelled is True
