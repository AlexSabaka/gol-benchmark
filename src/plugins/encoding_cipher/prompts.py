"""User prompt templates for the encoding_cipher plugin.

Nested dict: ``{"en": {"minimal": "...", ...}}`` following the project convention
(see carwash, inverted_cup plugins for reference).
Each template receives ``{instruction}`` and ``{encoded}`` variables.
"""

TEMPLATES = {
    "en": {
        # ── minimal ───────────────────────────────────────────────
        "minimal": (
            "{instruction}\n\n"
            "{encoded}\n\n"
            "Answer: "
        ),

        # ── casual ────────────────────────────────────────────────
        "casual": (
            "Hey, quick one — {instruction}\n\n"
            "{encoded}"
        ),

        # ── linguistic ────────────────────────────────────────────
        "linguistic": (
            "I have an encoding task for you.\n\n"
            "{instruction}\n\n"
            "Here is the encoded payload:\n\n"
            "{encoded}\n\n"
            "Please provide your answer."
        ),
    },

    "es": {
        "minimal": (
            "{instruction}\n\n"
            "{encoded}\n\n"
            "Respuesta: "
        ),
        "casual": (
            "Oye, una rápida — {instruction}\n\n"
            "{encoded}"
        ),
        "linguistic": (
            "Tengo una tarea de codificación para ti.\n\n"
            "{instruction}\n\n"
            "Aquí está el contenido codificado:\n\n"
            "{encoded}\n\n"
            "Por favor, proporciona tu respuesta."
        ),
    },

    "fr": {
        "minimal": (
            "{instruction}\n\n"
            "{encoded}\n\n"
            "Réponse : "
        ),
        "casual": (
            "Salut, un truc rapide — {instruction}\n\n"
            "{encoded}"
        ),
        "linguistic": (
            "J'ai une tâche d'encodage pour vous.\n\n"
            "{instruction}\n\n"
            "Voici le contenu encodé :\n\n"
            "{encoded}\n\n"
            "Veuillez fournir votre réponse."
        ),
    },

    "de": {
        "minimal": (
            "{instruction}\n\n"
            "{encoded}\n\n"
            "Antwort: "
        ),
        "casual": (
            "Hey, kurze Frage — {instruction}\n\n"
            "{encoded}"
        ),
        "linguistic": (
            "Ich habe eine Kodierungsaufgabe für dich.\n\n"
            "{instruction}\n\n"
            "Hier ist der kodierte Inhalt:\n\n"
            "{encoded}\n\n"
            "Bitte gib deine Antwort."
        ),
    },

    "zh": {
        "minimal": (
            "{instruction}\n\n"
            "{encoded}\n\n"
            "答案："
        ),
        "casual": (
            "嘿，快速问一下 — {instruction}\n\n"
            "{encoded}"
        ),
        "linguistic": (
            "我有一个编码任务给你。\n\n"
            "{instruction}\n\n"
            "以下是编码内容：\n\n"
            "{encoded}\n\n"
            "请提供你的答案。"
        ),
    },

    "ua": {
        "minimal": (
            "{instruction}\n\n"
            "{encoded}\n\n"
            "Відповідь: "
        ),
        "casual": (
            "Гей, швидке питання — {instruction}\n\n"
            "{encoded}"
        ),
        "linguistic": (
            "У мене є завдання з кодування для тебе.\n\n"
            "{instruction}\n\n"
            "Ось закодований вміст:\n\n"
            "{encoded}\n\n"
            "Будь ласка, надай свою відповідь."
        ),
    },
}
