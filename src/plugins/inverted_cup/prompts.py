"""User prompt templates for the Inverted Cup plugin."""

USER_PROMPT_TEMPLATES = {
    "en": {
        "minimal": "{source} {description} {extra}{question}",
        "casual": "Hey, I have a funny situation. {source} {description} {extra}{question}",
        "linguistic": (
            "I have a practical question about an unusual object I own.\n\n"
            "{source} {description} {extra}\n\n{question}"
        ),
    },
    "es": {
        "minimal": "{source} {description} {extra}{question}",
        "casual": "Oye, tengo una situación curiosa. {source} {description} {extra}{question}",
        "linguistic": (
            "Tengo una pregunta práctica sobre un objeto inusual que poseo.\n\n"
            "{source} {description} {extra}\n\n{question}"
        ),
    },
    "fr": {
        "minimal": "{source} {description} {extra}{question}",
        "casual": "Salut, j'ai une situation amusante. {source} {description} {extra}{question}",
        "linguistic": (
            "J'ai une question pratique à propos d'un objet inhabituel que je possède.\n\n"
            "{source} {description} {extra}\n\n{question}"
        ),
    },
    "de": {
        "minimal": "{source} {description} {extra}{question}",
        "casual": "Hey, ich habe eine lustige Situation. {source} {description} {extra}{question}",
        "linguistic": (
            "Ich habe eine praktische Frage zu einem ungewöhnlichen Gegenstand, den ich besitze.\n\n"
            "{source} {description} {extra}\n\n{question}"
        ),
    },
    "zh": {
        "minimal": "{source} {description} {extra}{question}",
        "casual": "嘿，我遇到了一个有趣的情况。{source} {description} {extra}{question}",
        "linguistic": (
            "我有一个关于我拥有的一个不寻常物件的实际问题。\n\n"
            "{source} {description} {extra}\n\n{question}"
        ),
    },
    "ua": {
        "minimal": "{source} {description} {extra}{question}",
        "casual": "Привіт, у мене кумедна ситуація. {source} {description} {extra}{question}",
        "linguistic": (
            "У мене є практичне питання про незвичайний предмет, який я маю.\n\n"
            "{source} {description} {extra}\n\n{question}"
        ),
    },
}
