"""User prompt templates for the Linda Fallacy plugin.

Placeholders: {persona_description}, {ranked_items}, {num_options}
"""

USER_PROMPT_TEMPLATES = {
    "en": {
        "linguistic": (
            "Consider the following description:\n\n"
            "{persona_description}\n\n"
            "Based on this description, please rank the following statements from "
            "MOST probable (1) to LEAST probable ({num_options}):\n\n"
            "{ranked_items}\n\n"
            "Please provide your ranking as a numbered list, starting with the most "
            "probable option. Also, briefly explain your reasoning for the top 3 rankings.\n\n"
            "RANKING:"
        ),
        "casual": (
            "Check out this person:\n\n"
            "{persona_description}\n\n"
            "Which of these is more likely? Rank them 1-{num_options} (most to least likely):\n\n"
            "{ranked_items}\n\n"
            "Give me your ranking and explain your top 3 picks!\n\n"
            "RANKING:"
        ),
        "minimal": (
            "{persona_description}\n\n"
            "Rank (1=most likely, {num_options}=least likely):\n"
            "{ranked_items}\n\n"
            "RANKING:"
        ),
    },
    "es": {
        "linguistic": (
            "Considere la siguiente descripción:\n\n"
            "{persona_description}\n\n"
            "Basándose en esta descripción, por favor ordene las siguientes afirmaciones "
            "de MÁS probable (1) a MENOS probable ({num_options}):\n\n"
            "{ranked_items}\n\n"
            "Por favor, proporcione su clasificación como una lista numerada, comenzando "
            "con la opción más probable. Explique brevemente su razonamiento para las 3 "
            "primeras clasificaciones.\n\n"
            "CLASIFICACIÓN:"
        ),
        "casual": (
            "Mira esta persona:\n\n"
            "{persona_description}\n\n"
            "¿Cuál de estas es más probable? Ordénalas del 1-{num_options} (más a menos probable):\n\n"
            "{ranked_items}\n\n"
            "¡Dame tu clasificación y explica tus 3 primeras opciones!\n\n"
            "CLASIFICACIÓN:"
        ),
        "minimal": (
            "{persona_description}\n\n"
            "Ordena (1=más probable, {num_options}=menos probable):\n"
            "{ranked_items}\n\n"
            "CLASIFICACIÓN:"
        ),
    },
    "fr": {
        "linguistic": (
            "Considérez la description suivante :\n\n"
            "{persona_description}\n\n"
            "Sur la base de cette description, veuillez classer les affirmations suivantes "
            "de la PLUS probable (1) à la MOINS probable ({num_options}) :\n\n"
            "{ranked_items}\n\n"
            "Veuillez fournir votre classement sous forme de liste numérotée, en commençant "
            "par l'option la plus probable. Expliquez brièvement votre raisonnement pour les "
            "3 premiers classements.\n\n"
            "CLASSEMENT :"
        ),
        "casual": (
            "Regardez cette personne :\n\n"
            "{persona_description}\n\n"
            "Laquelle de ces options est la plus probable ? Classez-les de 1-{num_options} "
            "(plus au moins probable) :\n\n"
            "{ranked_items}\n\n"
            "Donnez-moi votre classement et expliquez vos 3 premiers choix !\n\n"
            "CLASSEMENT :"
        ),
        "minimal": (
            "{persona_description}\n\n"
            "Classez (1=plus probable, {num_options}=moins probable) :\n"
            "{ranked_items}\n\n"
            "CLASSEMENT :"
        ),
    },
    "de": {
        "linguistic": (
            "Betrachten Sie die folgende Beschreibung:\n\n"
            "{persona_description}\n\n"
            "Ordnen Sie auf Grundlage dieser Beschreibung die folgenden Aussagen "
            "von der WAHRSCHEINLICHSTEN (1) bis zur UNWAHRSCHEINLICHSTEN ({num_options}):\n\n"
            "{ranked_items}\n\n"
            "Bitte geben Sie Ihre Rangfolge als nummerierte Liste an, beginnend mit der "
            "wahrscheinlichsten Option. Erklären Sie kurz Ihre Begründung für die ersten "
            "3 Platzierungen.\n\n"
            "RANGFOLGE:"
        ),
        "casual": (
            "Schau dir diese Person an:\n\n"
            "{persona_description}\n\n"
            "Was davon ist wahrscheinlicher? Ordne sie von 1-{num_options} "
            "(wahrscheinlichste bis unwahrscheinlichste):\n\n"
            "{ranked_items}\n\n"
            "Gib mir deine Rangfolge und erkläre deine Top 3!\n\n"
            "RANGFOLGE:"
        ),
        "minimal": (
            "{persona_description}\n\n"
            "Rangfolge (1=wahrscheinlichste, {num_options}=unwahrscheinlichste):\n"
            "{ranked_items}\n\n"
            "RANGFOLGE:"
        ),
    },
    "zh": {
        "linguistic": (
            "请阅读以下描述：\n\n"
            "{persona_description}\n\n"
            "根据这段描述，请将以下陈述从最可能（1）到最不可能（{num_options}）进行排序：\n\n"
            "{ranked_items}\n\n"
            "请以编号列表的形式提供您的排名，从最可能的选项开始。"
            "同时，请简要说明您对前三名排序的理由。\n\n"
            "排名："
        ),
        "casual": (
            "看看这个人：\n\n"
            "{persona_description}\n\n"
            "下面哪个更可能？从1到{num_options}排个序（从最可能到最不可能）：\n\n"
            "{ranked_items}\n\n"
            "给出你的排名，并解释你的前三个选择！\n\n"
            "排名："
        ),
        "minimal": (
            "{persona_description}\n\n"
            "排序（1=最可能，{num_options}=最不可能）：\n"
            "{ranked_items}\n\n"
            "排名："
        ),
    },
    "ua": {
        "linguistic": (
            "Розгляньте наступний опис:\n\n"
            "{persona_description}\n\n"
            "На основі цього опису, будь ласка, розташуйте наступні твердження "
            "від НАЙІМОВІРНІШОГО (1) до НАЙМЕНШ ІМОВІРНОГО ({num_options}):\n\n"
            "{ranked_items}\n\n"
            "Будь ласка, надайте ваш рейтинг у вигляді нумерованого списку, починаючи "
            "з найімовірнішого варіанту. Також коротко поясніть ваші міркування щодо "
            "перших 3 позицій.\n\n"
            "РЕЙТИНГ:"
        ),
        "casual": (
            "Подивись на цю людину:\n\n"
            "{persona_description}\n\n"
            "Що з цього більш імовірно? Розстав від 1 до {num_options} "
            "(від найімовірнішого до найменш імовірного):\n\n"
            "{ranked_items}\n\n"
            "Дай мені свій рейтинг і поясни свої топ-3 вибори!\n\n"
            "РЕЙТИНГ:"
        ),
        "minimal": (
            "{persona_description}\n\n"
            "Рейтинг (1=найімовірніше, {num_options}=найменш імовірне):\n"
            "{ranked_items}\n\n"
            "РЕЙТИНГ:"
        ),
    },
}
