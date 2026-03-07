"""
Frontend — Input Panel Component

Provides text / image / audio tabs for question input.
"""

from __future__ import annotations

import streamlit as st
from PIL import Image

from backend.multimodal.text_input import process_text_input
from backend.multimodal.image_ocr import extract_text_from_image
from backend.multimodal.audio_asr import transcribe_audio


def render_input_panel() -> None:
    """Render the multimodal input tabs."""
    st.subheader("1️⃣ Input Your Question")

    tab_text, tab_image, tab_audio = st.tabs(["✏️ Text", "📷 Image", "🎤 Audio"])

    with tab_text:
        text_input = st.text_area(
            "Type your math question",
            placeholder="e.g.  Solve x² - 5x + 6 = 0",
            height=100,
        )
        st.markdown('<div class="btn-info">', unsafe_allow_html=True)
        if st.button("Submit Text", key="btn_text", use_container_width=True):
            result = process_text_input(text_input)
            st.session_state.extracted_text = result.value
            st.session_state.input_confidence = result.score
            st.session_state.input_type = "text"
        st.markdown('</div>', unsafe_allow_html=True)

    with tab_image:
        uploaded_image = st.file_uploader(
            "Upload an image of a math problem",
            type=["png", "jpg", "jpeg", "bmp", "webp"],
        )
        if uploaded_image:
            image = Image.open(uploaded_image)
            st.image(image, caption="Uploaded image", use_container_width=True)

            st.markdown('<div class="btn-warning">', unsafe_allow_html=True)
            if st.button("Extract Text (Mathpix OCR)", key="btn_ocr", use_container_width=True):
                with st.spinner("Running Mathpix OCR…"):
                    ocr_result = extract_text_from_image(image)

                st.session_state.extracted_text = ocr_result.value
                st.session_state.input_confidence = ocr_result.score
                st.session_state.input_type = "image"

                if not str(ocr_result.value).strip():
                    st.error("No text detected in the image. Try a clearer or higher-resolution photo.")
                else:
                    conf_pct = f"{ocr_result.score:.0%}"
                    if ocr_result.reason == "ocr_low_confidence":
                        st.warning(
                            f"OCR confidence is low ({conf_pct}). "
                            "The extracted text may contain errors — please review and edit it below.",
                            icon="⚠️",
                        )
                    else:
                        st.success(f"Text extracted successfully (confidence {conf_pct}).", icon="✅")

                    if "error" in ocr_result.reason.lower() or ocr_result.score < 0.4:
                        st.info(
                            "💡 **Tip:** For best math OCR, add your Mathpix API keys in the sidebar "
                            "(🔑 API Configuration → 📷 Mathpix OCR). "
                            "Get free keys at mathpix.com.",
                            icon="ℹ️",
                        )
            st.markdown('</div>', unsafe_allow_html=True)


    with tab_audio:
        uploaded_audio = st.file_uploader(
            "Upload an audio recording of your question",
            type=["wav", "mp3", "m4a", "ogg", "flac"],
        )
        if uploaded_audio:
            st.audio(uploaded_audio)
            st.markdown('<div class="btn-info">', unsafe_allow_html=True)
            if st.button("Transcribe Audio", key="btn_asr", use_container_width=True):
                with st.spinner("Transcribing…"):
                    asr_result = transcribe_audio(uploaded_audio.read())
                    st.session_state.extracted_text = asr_result.value
                    st.session_state.input_confidence = asr_result.score
                    st.session_state.input_type = "audio"
            st.markdown('</div>', unsafe_allow_html=True)
