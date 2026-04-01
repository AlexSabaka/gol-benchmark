"""User prompt templates for the Grid Tasks plugin."""

USER_PROMPT_TEMPLATES = {
    "en": {
        "minimal": "{table_str}\n\n{question}\nAnswer:",
        "casual": (
            "Here is a data table:\n\n"
            "{table_str}\n\n"
            "Question: {question}\n\n"
            "Please provide your answer clearly."
        ),
        "linguistic": (
            "Please analyze the following data table carefully "
            "and answer the question.\n\n"
            "{table_str}\n\n"
            "Question: {question}\n\n"
            "Provide your answer with a brief explanation."
        ),
    },
    "es": {
        "minimal": "{table_str}\n\n{question}\nRespuesta:",
        "casual": (
            "Aquí tienes una tabla de datos:\n\n"
            "{table_str}\n\n"
            "Pregunta: {question}\n\n"
            "Por favor, proporciona tu respuesta con claridad."
        ),
        "linguistic": (
            "Por favor, analiza la siguiente tabla de datos con atención "
            "y responde a la pregunta.\n\n"
            "{table_str}\n\n"
            "Pregunta: {question}\n\n"
            "Proporciona tu respuesta con una breve explicación."
        ),
    },
    "fr": {
        "minimal": "{table_str}\n\n{question}\nRéponse :",
        "casual": (
            "Voici un tableau de données :\n\n"
            "{table_str}\n\n"
            "Question : {question}\n\n"
            "Veuillez fournir votre réponse clairement."
        ),
        "linguistic": (
            "Veuillez analyser attentivement le tableau de données suivant "
            "et répondre à la question.\n\n"
            "{table_str}\n\n"
            "Question : {question}\n\n"
            "Fournissez votre réponse avec une brève explication."
        ),
    },
    "de": {
        "minimal": "{table_str}\n\n{question}\nAntwort:",
        "casual": (
            "Hier ist eine Datentabelle:\n\n"
            "{table_str}\n\n"
            "Frage: {question}\n\n"
            "Bitte geben Sie Ihre Antwort klar an."
        ),
        "linguistic": (
            "Bitte analysieren Sie die folgende Datentabelle sorgfältig "
            "und beantworten Sie die Frage.\n\n"
            "{table_str}\n\n"
            "Frage: {question}\n\n"
            "Geben Sie Ihre Antwort mit einer kurzen Erklärung an."
        ),
    },
    "zh": {
        "minimal": "{table_str}\n\n{question}\n答案：",
        "casual": (
            "这是一张数据表：\n\n"
            "{table_str}\n\n"
            "问题：{question}\n\n"
            "请清楚地给出你的答案。"
        ),
        "linguistic": (
            "请仔细分析以下数据表并回答问题。\n\n"
            "{table_str}\n\n"
            "问题：{question}\n\n"
            "请给出你的答案并附上简要说明。"
        ),
    },
    "ua": {
        "minimal": "{table_str}\n\n{question}\nВідповідь:",
        "casual": (
            "Ось таблиця даних:\n\n"
            "{table_str}\n\n"
            "Питання: {question}\n\n"
            "Будь ласка, надайте чітку відповідь."
        ),
        "linguistic": (
            "Будь ласка, уважно проаналізуйте наступну таблицю даних "
            "і дайте відповідь на питання.\n\n"
            "{table_str}\n\n"
            "Питання: {question}\n\n"
            "Надайте відповідь із коротким поясненням."
        ),
    },
}
