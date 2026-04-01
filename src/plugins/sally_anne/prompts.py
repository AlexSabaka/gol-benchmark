"""User prompt templates for the Sally-Anne plugin.

Sally-Anne is a false belief test: the key instruction is to answer
what the character *believes*, not what is actually true.
Variables: {narrative} (scenario text) and {question} (the question).
"""

USER_PROMPT_TEMPLATES = {
    "en": {
        "minimal": "{narrative}\n\n{question}\nAnswer:",
        "casual": (
            "Here's a little scenario for you:\n\n"
            "{narrative}\n\n"
            "{question} Just give me the answer in one word."
        ),
        "linguistic": (
            "Please read the following scenario carefully and answer "
            "the question about what the character believes.\n\n"
            "{narrative}\n\n"
            "{question}\n"
            "Provide your answer as a single word."
        ),
    },
    "es": {
        "minimal": "{narrative}\n\n{question}\nRespuesta:",
        "casual": (
            "Aqui tienes un pequeno escenario:\n\n"
            "{narrative}\n\n"
            "{question} Solo dame la respuesta en una palabra."
        ),
        "linguistic": (
            "Lee atentamente el siguiente escenario y responde "
            "a la pregunta sobre lo que el personaje cree.\n\n"
            "{narrative}\n\n"
            "{question}\n"
            "Proporciona tu respuesta en una sola palabra."
        ),
    },
    "fr": {
        "minimal": "{narrative}\n\n{question}\nReponse :",
        "casual": (
            "Voici un petit scenario pour toi :\n\n"
            "{narrative}\n\n"
            "{question} Donne-moi la reponse en un seul mot."
        ),
        "linguistic": (
            "Veuillez lire attentivement le scenario suivant et repondre "
            "a la question sur ce que le personnage croit.\n\n"
            "{narrative}\n\n"
            "{question}\n"
            "Fournissez votre reponse en un seul mot."
        ),
    },
    "de": {
        "minimal": "{narrative}\n\n{question}\nAntwort:",
        "casual": (
            "Hier ist ein kleines Szenario fuer dich:\n\n"
            "{narrative}\n\n"
            "{question} Gib mir die Antwort in einem einzigen Wort."
        ),
        "linguistic": (
            "Bitte lesen Sie das folgende Szenario sorgfaeltig und beantworten Sie "
            "die Frage darueber, was die Person glaubt.\n\n"
            "{narrative}\n\n"
            "{question}\n"
            "Geben Sie Ihre Antwort als ein einzelnes Wort an."
        ),
    },
    "zh": {
        "minimal": "{narrative}\n\n{question}\n答案：",
        "casual": (
            "这里有一个小场景：\n\n"
            "{narrative}\n\n"
            "{question} 请用一个词回答。"
        ),
        "linguistic": (
            "请仔细阅读以下场景，并回答关于角色所相信的内容的问题。\n\n"
            "{narrative}\n\n"
            "{question}\n"
            "请用一个词作答。"
        ),
    },
    "ua": {
        "minimal": "{narrative}\n\n{question}\nВідповідь:",
        "casual": (
            "Ось невеличкий сценарій для тебе:\n\n"
            "{narrative}\n\n"
            "{question} Дай відповідь одним словом."
        ),
        "linguistic": (
            "Будь ласка, уважно прочитайте наступний сценарій та дайте відповідь "
            "на запитання про те, у що вірить персонаж.\n\n"
            "{narrative}\n\n"
            "{question}\n"
            "Надайте відповідь одним словом."
        ),
    },
}
