from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional

import streamlit as st

from transcriber import TranscriptionError, load_model, transcribe_audio

st.set_page_config(page_title="Audio Transcriber", page_icon="🎙️")
st.title("🎙️ Whisper Audio Transcriber")
st.caption("Upload an audio/video file to get the transcription using faster-whisper.")

MODEL_SIZES = ["tiny", "base", "small", "medium", "large-v2"]
COMPUTE_TYPES = ["int8", "int8_float16", "int16", "float16", "float32"]


@st.cache_resource(show_spinner="Loading Whisper model...")
def get_model(model_size: str, compute_type: str):
    return load_model(model_size=model_size, compute_type=compute_type)


def save_uploaded_file(uploaded_file) -> Optional[Path]:
    if uploaded_file is None:
        return None

    suffix = Path(uploaded_file.name).suffix or ".mp3"
    temp_file = NamedTemporaryFile(delete=False, suffix=suffix)
    temp_file.write(uploaded_file.read())
    temp_file.flush()
    return Path(temp_file.name)


def main() -> None:
    st.sidebar.header("Configuration")
    model_size = st.sidebar.selectbox("Model size", MODEL_SIZES, index=1)
    compute_type = st.sidebar.selectbox("Compute type", COMPUTE_TYPES, index=0)
    beam_size = st.sidebar.slider("Beam size", 1, 10, 5)
    best_of = st.sidebar.slider("Best of", 1, 10, 5)

    uploaded_audio = st.file_uploader(
        "Upload audio/video file",
        type=["mp3", "wav", "m4a", "mp4", "mov", "aac", "flac"],
    )

    submit = st.button("Transcribe", type="primary", use_container_width=True)

    if not submit:
        st.info("Upload a file and click Transcribe to start.")
        return

    if uploaded_audio is None:
        st.warning("Please upload an audio or video file before transcribing.")
        return

    audio_path = save_uploaded_file(uploaded_audio)
    if audio_path is None:
        st.error("Could not cache uploaded file. Please try again.")
        return

    with st.spinner("Transcribing..."):
        try:
            model = get_model(model_size, compute_type)
            transcript, duration = transcribe_audio(
                model,
                audio_path,
                beam_size=beam_size,
                best_of=best_of,
            )
        except TranscriptionError as exc:
            st.error(str(exc))
            return
        finally:
            audio_path.unlink(missing_ok=True)

    st.success(f"Completed transcription ({duration:.1f}s audio)")
    st.text_area("Transcript", transcript, height=300)


if __name__ == "__main__":
    main()
