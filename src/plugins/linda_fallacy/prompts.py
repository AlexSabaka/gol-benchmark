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
}
