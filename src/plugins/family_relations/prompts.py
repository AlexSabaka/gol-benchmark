"""User prompt templates for the Family Relations plugin."""

USER_PROMPT_TEMPLATES = {
    "en": {
        "minimal": "{puzzle}\n\nAnswer with a single integer.",
        "casual": (
            "Hey, here's a quick family puzzle:\n\n"
            "{puzzle}\n\n"
            "What's the answer?  Just give me the number."
        ),
        "linguistic": (
            "Please solve the following family-relations reasoning problem. "
            "Think carefully about who is counted and from whose perspective.\n\n"
            "{puzzle}\n\n"
            "Provide your final answer as a single integer."
        ),
    },
    "es": {
        "minimal": "{puzzle}\n\nResponde con un solo numero entero.",
        "casual": (
            "Oye, aqui tienes un acertijo familiar rapido:\n\n"
            "{puzzle}\n\n"
            "Cual es la respuesta? Solo dame el numero."
        ),
        "linguistic": (
            "Por favor, resuelve el siguiente problema de razonamiento sobre "
            "relaciones familiares. Piensa cuidadosamente en quien se cuenta "
            "y desde la perspectiva de quien.\n\n"
            "{puzzle}\n\n"
            "Proporciona tu respuesta final como un solo numero entero."
        ),
    },
    "fr": {
        "minimal": "{puzzle}\n\nRepondez avec un seul nombre entier.",
        "casual": (
            "Salut, voici une petite enigme familiale :\n\n"
            "{puzzle}\n\n"
            "Quelle est la reponse ? Donne-moi juste le nombre."
        ),
        "linguistic": (
            "Veuillez resoudre le probleme de raisonnement suivant portant sur "
            "les relations familiales. Reflechissez bien a qui est compte "
            "et du point de vue de qui.\n\n"
            "{puzzle}\n\n"
            "Fournissez votre reponse finale sous la forme d'un seul nombre entier."
        ),
    },
    "de": {
        "minimal": "{puzzle}\n\nAntworten Sie mit einer einzelnen ganzen Zahl.",
        "casual": (
            "Hey, hier ist ein schnelles Familienraetsel:\n\n"
            "{puzzle}\n\n"
            "Was ist die Antwort? Gib mir einfach die Zahl."
        ),
        "linguistic": (
            "Bitte loesen Sie die folgende Aufgabe zum logischen Denken ueber "
            "Familienbeziehungen. Ueberlegen Sie genau, wer gezaehlt wird "
            "und aus wessen Perspektive.\n\n"
            "{puzzle}\n\n"
            "Geben Sie Ihre endgueltige Antwort als einzelne ganze Zahl an."
        ),
    },
    "zh": {
        "minimal": "{puzzle}\n\n请用一个整数作答。",
        "casual": (
            "嘿，这里有一个简单的家庭关系谜题：\n\n"
            "{puzzle}\n\n"
            "答案是什么？只给我数字就好。"
        ),
        "linguistic": (
            "请解决以下关于家庭关系的推理问题。"
            "请仔细思考统计的是谁，以及从谁的视角出发。\n\n"
            "{puzzle}\n\n"
            "请以一个整数作为你的最终答案。"
        ),
    },
    "ua": {
        "minimal": "{puzzle}\n\nВідповідайте одним цілим числом.",
        "casual": (
            "Привіт, ось швидка сімейна загадка:\n\n"
            "{puzzle}\n\n"
            "Яка відповідь? Просто дай мені число."
        ),
        "linguistic": (
            "Будь ласка, розв'яжіть наступну задачу на логічне мислення "
            "щодо сімейних відносин. Ретельно подумайте, хто рахується "
            "і з чиєї перспективи.\n\n"
            "{puzzle}\n\n"
            "Надайте вашу остаточну відповідь у вигляді одного цілого числа."
        ),
    },
}
