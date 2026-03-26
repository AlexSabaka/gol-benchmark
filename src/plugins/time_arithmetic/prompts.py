"""User prompt templates for the Time Arithmetic plugin.

Placeholder: {question}
"""

USER_PROMPT_TEMPLATES = {
    "en": {
        "linguistic": (
            "Solve the following temporal reasoning problem. Show your reasoning "
            "step by step, then provide the final answer.\n\n"
            "{question}\n\n"
            "Provide your answer in the exact format requested (a specific time, "
            "a day of the week, a number of minutes, or state that the date is "
            "impossible if applicable)."
        ),
        "casual": (
            "Hey, quick time question for you:\n\n"
            "{question}\n\n"
            "What's the answer?"
        ),
        "minimal": "{question}\n\nAnswer:",
    },
    "es": {
        "linguistic": (
            "Resuelve el siguiente problema de razonamiento temporal. "
            "Muestra tu razonamiento paso a paso y luego da la respuesta final.\n\n"
            "{question}\n\n"
            "Proporciona tu respuesta en el formato exacto solicitado."
        ),
        "casual": (
            "Oye, una pregunta rápida sobre el tiempo:\n\n"
            "{question}\n\n"
            "¿Cuál es la respuesta?"
        ),
        "minimal": "{question}\n\nRespuesta:",
    },
    "fr": {
        "linguistic": (
            "Résolvez le problème de raisonnement temporel suivant. "
            "Montrez votre raisonnement étape par étape, puis donnez la réponse finale.\n\n"
            "{question}\n\n"
            "Fournissez votre réponse dans le format exact demandé."
        ),
        "casual": (
            "Hé, une petite question sur le temps :\n\n"
            "{question}\n\n"
            "Quelle est la réponse ?"
        ),
        "minimal": "{question}\n\nRéponse :",
    },
    "de": {
        "linguistic": (
            "Lösen Sie das folgende zeitliche Denkproblem. "
            "Zeigen Sie Ihre Überlegungen Schritt für Schritt und geben Sie "
            "dann die endgültige Antwort.\n\n"
            "{question}\n\n"
            "Geben Sie Ihre Antwort im genau angeforderten Format an."
        ),
        "casual": (
            "Hey, eine kurze Zeitfrage:\n\n"
            "{question}\n\n"
            "Was ist die Antwort?"
        ),
        "minimal": "{question}\n\nAntwort:",
    },
    "zh": {
        "linguistic": (
            "请解决以下时间推理问题。逐步展示你的推理过程，然后给出最终答案。\n\n"
            "{question}\n\n"
            "请以要求的格式提供答案。"
        ),
        "casual": "{question}\n\n答案是什么？",
        "minimal": "{question}\n\n答案：",
    },
    "ua": {
        "linguistic": (
            "Розв'яжіть наступну задачу на часове міркування. "
            "Покажіть своє міркування крок за кроком, а потім дайте остаточну відповідь.\n\n"
            "{question}\n\n"
            "Надайте відповідь у точному запитуваному форматі."
        ),
        "casual": (
            "Привіт, швидке запитання про час:\n\n"
            "{question}\n\n"
            "Яка відповідь?"
        ),
        "minimal": "{question}\n\nВідповідь:",
    },
}
