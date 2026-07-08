"""Unit tests for voice-agent sentence streaming and barge-in helpers."""
import asyncio

import pytest

from app.voice_agent.speech_pipeline import PlaybackGate, barge_in, pick_immediate_ack, split_sentences, speak_text, speak_with_filler


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


class TestSpeakWithFiller:
    @pytest.mark.asyncio
    async def test_plays_filler_before_response(self):
        gate = PlaybackGate()
        order = []

        class FakeSpeech:
            async def synthesize(self, text, voice="female"):
                order.append(f"synth:{text}")
                return f"{text}-audio".encode()

        async def fake_publish(room, source, audio, rate, playback_gate):
            order.append(f"play:{audio.decode()}")

        async def slow_response():
            order.append("llm:start")
            await asyncio.sleep(0.05)
            order.append("llm:done")
            return "Next question?"

        text = await speak_with_filler(
            filler="Got it.",
            response_coro=slow_response(),
            speech=FakeSpeech(),
            room=None,
            audio_source=None,
            publish_fn=fake_publish,
            playback_gate=gate,
        )
        assert text == "Next question?"
        assert order.index("llm:start") < order.index("llm:done")
        assert "synth:Got it." in order
        assert "synth:Next question?" in order

    @pytest.mark.asyncio
    async def test_prefetches_next_sentence(self):
        gate = PlaybackGate()
        synth_order = []

        class FakeSpeech:
            async def synthesize(self, text, voice="female"):
                synth_order.append(text)
                await asyncio.sleep(0.02)
                return f"{text}-audio".encode()

        async def fake_publish(*args, **kwargs):
            await asyncio.sleep(0.03)

        await speak_text(
            "First. Second.",
            FakeSpeech(),
            None,
            None,
            fake_publish,
            gate,
        )
        assert synth_order == ["First.", "Second."]
