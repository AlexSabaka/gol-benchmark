"""User prompt templates for the Measure Comparison plugin."""

USER_PROMPT_TEMPLATES = {
    "en": {
        "minimal": "{question}\n\nAnswer:",
        "casual": "Hey, quick question — {question}",
        "linguistic": (
            "I have a measurement comparison question for you.\n\n"
            "{question}\n\n"
            "Please provide just the winning measurement "
            "(or 'equal' / 'incomparable' if applicable)."
        ),
    },
    "es": {
        "minimal": "{question}\n\nRespuesta:",
        "casual": "Oye, pregunta rápida — {question}",
        "linguistic": (
            "Tengo una pregunta sobre comparación de medidas.\n\n"
            "{question}\n\n"
            "Por favor, proporciona solo la medida ganadora."
        ),
    },
    "fr": {
        "minimal": "{question}\n\nRéponse :",
        "casual": "Salut, petite question — {question}",
        "linguistic": (
            "J'ai une question de comparaison de mesures.\n\n"
            "{question}\n\n"
            "Veuillez fournir uniquement la mesure gagnante."
        ),
    },
    "de": {
        "minimal": "{question}\n\nAntwort:",
        "casual": "Hey, kurze Frage — {question}",
        "linguistic": (
            "Ich habe eine Frage zum Vergleich von Maßeinheiten.\n\n"
            "{question}\n\n"
            "Bitte geben Sie nur die größere Messung an."
        ),
    },
    "zh": {
        "minimal": "{question}\n\n答案：",
        "casual": "嘿，快问一下——{question}",
        "linguistic": (
            "我有一个关于测量比较的问题。\n\n"
            "{question}\n\n"
            "请只提供较大的测量值。"
        ),
    },
    "ua": {
        "minimal": "{question}\n\nВідповідь:",
        "casual": "Привіт, швидке питання — {question}",
        "linguistic": (
            "У мене є питання про порівняння вимірювань.\n\n"
            "{question}\n\n"
            "Будь ласка, надайте лише більше вимірювання."
        ),
    },
}
