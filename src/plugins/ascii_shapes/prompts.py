"""User prompt templates for the ASCII Shapes plugin.

Placeholders: {shape}, {question}
Note: {answer_format} was in the original templates but never set by
the generator, so it is omitted here to avoid literal placeholder text
appearing in the prompt output.
"""

USER_PROMPT_TEMPLATES = {
    "en": {
        "linguistic": (
            "Please analyze the following ASCII-rendered shape carefully "
            "and answer the question.\n\n"
            "Shape:\n{shape}\n\n"
            "{question}\n\n"
            "Provide your answer."
        ),
        "casual": (
            "Check out this shape:\n\n{shape}\n\n"
            "{question}\n\n"
            "Answer:"
        ),
        "minimal": "{shape}\n\n{question}",
    },
    "es": {
        "linguistic": (
            "Por favor, analice cuidadosamente la siguiente forma renderizada "
            "en ASCII y responda la pregunta.\n\n"
            "Forma:\n{shape}\n\n"
            "{question}\n\n"
            "Proporcione su respuesta."
        ),
        "casual": (
            "Mira esta forma:\n\n{shape}\n\n"
            "{question}\n\n"
            "Respuesta:"
        ),
        "minimal": "{shape}\n\n{question}",
    },
    "fr": {
        "linguistic": (
            "Veuillez analyser attentivement la forme ASCII suivante "
            "et répondre à la question.\n\n"
            "Forme:\n{shape}\n\n"
            "{question}\n\n"
            "Fournissez votre réponse."
        ),
        "casual": (
            "Regarde cette forme:\n\n{shape}\n\n"
            "{question}\n\n"
            "Réponse:"
        ),
        "minimal": "{shape}\n\n{question}",
    },
    "de": {
        "linguistic": (
            "Bitte analysieren Sie die folgende ASCII-gerenderte Form "
            "sorgfältig und beantworten Sie die Frage.\n\n"
            "Form:\n{shape}\n\n"
            "{question}\n\n"
            "Geben Sie Ihre Antwort."
        ),
        "casual": (
            "Schau dir diese Form an:\n\n{shape}\n\n"
            "{question}\n\n"
            "Antwort:"
        ),
        "minimal": "{shape}\n\n{question}",
    },
    "zh": {
        "linguistic": (
            "请仔细分析以下ASCII渲染的形状并回答问题。\n\n"
            "形状：\n{shape}\n\n"
            "{question}\n\n"
            "请提供答案。"
        ),
        "casual": (
            "看看这个形状：\n\n{shape}\n\n"
            "{question}\n\n"
            "答案："
        ),
        "minimal": "{shape}\n\n{question}",
    },
    "ua": {
        "linguistic": (
            "Будь ласка, уважно проаналізуйте наступну ASCII-форму "
            "та дайте відповідь на запитання.\n\n"
            "Форма:\n{shape}\n\n"
            "{question}\n\n"
            "Надайте відповідь."
        ),
        "casual": (
            "Подивись на цю форму:\n\n{shape}\n\n"
            "{question}\n\n"
            "Відповідь:"
        ),
        "minimal": "{shape}\n\n{question}",
    },
}
