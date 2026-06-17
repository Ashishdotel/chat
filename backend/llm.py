"""
llm.py — Ollama AI Integration Layer
======================================
This is the ONLY file in the project that talks directly to the Ollama API.
Uses the Ollama native /api/chat endpoint via httpx.

Functions provided:
    get_chat_response()         — Multilingual chat reply
    translate_text()            — Text translation between languages
    translate_image_document()  — OCR + translation from image (requires vision model)
"""

import httpx
from typing import List, Dict
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

LANGUAGE_NAMES = {
    "ne": "Nepali (नेपाली)",
    "en": "English",
    "hi": "Hindi (हिन्दी)",
    "zh": "Chinese (中文)",
    "ja": "Japanese (日本語)",
    "ko": "Korean (한국어)",
    "es": "Spanish (Español)",
    "fr": "French (Français)",
    "de": "German (Deutsch)",
    "ar": "Arabic (العربية)",
    "pt": "Portuguese (Português)",
    "ru": "Russian (Русский)",
}

NEPALI_SYSTEM_PROMPT = """
तपाईं एक बुद्धिमान नेपाली भाषा च्याटबट हुनुहुन्छ।
(You are an intelligent Nepali language chatbot.)

तपाईंका मुख्य निर्देशनहरू:
1. सधैं नेपाली भाषामा जवाफ दिनुहोस् — प्रयोगकर्ताले जुनसुकै भाषामा सोधे पनि।
2. विनम्र र सहयोगी रहनुहोस्।
3. स्पष्ट र सरल नेपाली भाषा प्रयोग गर्नुहोस्।
4. यदि प्रयोगकर्ताले अंग्रेजीमा सोध्छन्, नेपालीमा जवाफ दिनुहोस्।
5. नेपाली संस्कृति र सन्दर्भलाई ध्यानमा राख्नुहोस्।

तपाईं एक विश्वविद्यालय थेसिस प्रोजेक्टको लागि बनाइएको च्याटबट हुनुहुन्छ।
"""


def _build_system_prompt(language: str = "ne") -> str:
    if language == "ne":
        return NEPALI_SYSTEM_PROMPT
    lang_name = LANGUAGE_NAMES.get(language, "English")
    return f"""You are an intelligent multilingual chatbot assistant built as a university thesis project.

Always respond in {lang_name}.
Be polite, helpful, and clear. Even if the user writes in a different language, reply in {lang_name}.
When helping with word meanings or translations, provide clear explanations and examples."""


def _chat(messages: List[Dict], model: str = None) -> str:
    """Make a single call to Ollama /api/chat and return the reply text."""
    model = model or settings.ollama_model
    base = settings.ollama_base_url.rstrip("/")
    # Strip /v1 suffix if present — Ollama native API doesn't use it
    if base.endswith("/v1"):
        base = base[:-3]
    url = f"{base}/api/chat"

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"num_predict": settings.ollama_max_tokens},
    }
    headers = {
        "Authorization": f"Bearer {settings.ollama_api_key}",
        "Content-Type": "application/json",
    }

    response = httpx.post(url, json=payload, headers=headers, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data["message"]["content"]


def get_chat_response(
    history: List[Dict[str, str]],
    user_message: str,
    language: str = "ne"
) -> str:
    """Send a message to Ollama and return the response."""
    system_prompt = _build_system_prompt(language)

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        role = msg.get("role", "user")
        if role == "system":
            continue
        messages.append({"role": role, "content": msg.get("content", "")})
    messages.append({"role": "user", "content": user_message})

    logger.info(f"Calling Ollama | Model: {settings.ollama_model} | Lang: {language} | Messages: {len(messages)}")
    reply = _chat(messages)
    if not reply:
        raise ValueError("Ollama returned an empty response")
    logger.info(f"Ollama response received | {len(reply)} chars")
    return reply.strip()


def translate_text(text: str, source_lang: str, target_lang: str) -> dict:
    """Translate text using Ollama."""
    target_name = LANGUAGE_NAMES.get(target_lang, target_lang)
    if source_lang == "auto":
        instruction = f"Auto-detect the source language and translate the following text to {target_name}."
    else:
        source_name = LANGUAGE_NAMES.get(source_lang, source_lang)
        instruction = f"Translate the following text from {source_name} to {target_name}."

    prompt = f"""{instruction}

Return ONLY the translated text — no explanations, labels, or quotes.

Text:
{text}"""

    logger.info(f"Translation request | {source_lang} → {target_lang} | {len(text)} chars")

    messages = [
        {"role": "system", "content": "You are a professional translator. Translate text accurately and naturally."},
        {"role": "user", "content": prompt},
    ]
    translated = _chat(messages).strip()
    return {"translated_text": translated, "char_count": len(translated)}


def translate_image_document(base64_image: str, image_mime: str, target_lang: str) -> dict:
    """Use Ollama vision model to OCR an image and translate its text."""
    target_name = LANGUAGE_NAMES.get(target_lang, target_lang)
    logger.info(f"Image OCR+translation | target: {target_lang} | mime: {image_mime}")

    messages = [
        {
            "role": "system",
            "content": "You are a document OCR and translation assistant. Extract text from images accurately.",
        },
        {
            "role": "user",
            "content": f"""Please do the following with this document image:
1. Extract ALL text from the image (OCR)
2. Translate the extracted text to {target_name}

Respond in exactly this format:
ORIGINAL TEXT:
[extracted text]

TRANSLATED TEXT:
[translated text]

If no readable text is found, write "No text found in image." under both sections.""",
            "images": [base64_image],
        },
    ]

    content = _chat(messages).strip()
    original_text = ""
    translated_text = ""

    if "ORIGINAL TEXT:" in content and "TRANSLATED TEXT:" in content:
        parts = content.split("TRANSLATED TEXT:")
        original_text = parts[0].replace("ORIGINAL TEXT:", "").strip()
        translated_text = parts[1].strip()
    else:
        translated_text = content
        original_text = content

    return {"original_text": original_text, "translated_text": translated_text}
