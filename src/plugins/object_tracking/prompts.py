"""User prompt templates for the Object Tracking plugin.

Object tracking is special: the prompt body depends on scenario steps
formatted by a StepBuilder.  The templates below wrap that steps text.
"""

USER_PROMPT_TEMPLATES = {
    "en": {
        "minimal": "{steps_text}\n\n{question}\nAnswer:",
        "casual": "{steps_text} {question} Give single word answer.",
        "linguistic": (
            "{steps_text}\n\n"
            "Based on the sequence of actions described above, determine the "
            "current location of the {object}.\n\n"
            "Apply logical reasoning to track the object through each step:\n"
            "1. Identify where the object was initially placed\n"
            "2. Track any movements or transfers\n"
            "3. Pay special attention to any inversion or flipping of containers\n"
            "4. Determine the final resting location\n\n"
            "{question}\n"
            "Provide your answer as a single word indicating the location."
        ),
    },
    "es": {
        "minimal": "{steps_text}\n\n{question}\nRespuesta:",
        "casual": "{steps_text} {question} Da una respuesta de una sola palabra.",
        "linguistic": (
            "{steps_text}\n\n"
            "Basandote en la secuencia de acciones descritas anteriormente, determina la "
            "ubicacion actual del/de la {object}.\n\n"
            "Aplica razonamiento logico para seguir el objeto en cada paso:\n"
            "1. Identifica donde se coloco inicialmente el objeto\n"
            "2. Rastrea cualquier movimiento o transferencia\n"
            "3. Presta especial atencion a cualquier inversion o volteo de contenedores\n"
            "4. Determina la ubicacion final\n\n"
            "{question}\n"
            "Proporciona tu respuesta como una sola palabra indicando la ubicacion."
        ),
    },
    "fr": {
        "minimal": "{steps_text}\n\n{question}\nReponse :",
        "casual": "{steps_text} {question} Donne une reponse en un seul mot.",
        "linguistic": (
            "{steps_text}\n\n"
            "En vous basant sur la sequence d'actions decrites ci-dessus, determinez "
            "l'emplacement actuel du/de la {object}.\n\n"
            "Appliquez un raisonnement logique pour suivre l'objet a chaque etape :\n"
            "1. Identifiez ou l'objet a ete place initialement\n"
            "2. Suivez tous les mouvements ou transferts\n"
            "3. Portez une attention particuliere a toute inversion ou retournement de conteneurs\n"
            "4. Determinez l'emplacement final\n\n"
            "{question}\n"
            "Fournissez votre reponse en un seul mot indiquant l'emplacement."
        ),
    },
    "de": {
        "minimal": "{steps_text}\n\n{question}\nAntwort:",
        "casual": "{steps_text} {question} Gib eine Antwort in einem einzigen Wort.",
        "linguistic": (
            "{steps_text}\n\n"
            "Bestimmen Sie anhand der oben beschriebenen Aktionsfolge den "
            "aktuellen Standort des/der {object}.\n\n"
            "Wenden Sie logisches Denken an, um das Objekt durch jeden Schritt zu verfolgen:\n"
            "1. Identifizieren Sie, wo das Objekt urspruenglich platziert wurde\n"
            "2. Verfolgen Sie alle Bewegungen oder Transfers\n"
            "3. Achten Sie besonders auf jede Umkehrung oder das Umdrehen von Behaeltern\n"
            "4. Bestimmen Sie den endgueltigen Standort\n\n"
            "{question}\n"
            "Geben Sie Ihre Antwort als ein einzelnes Wort an, das den Standort angibt."
        ),
    },
    "zh": {
        "minimal": "{steps_text}\n\n{question}\n答案：",
        "casual": "{steps_text} {question} 请用一个词回答。",
        "linguistic": (
            "{steps_text}\n\n"
            "根据上述描述的一系列操作，确定{object}的当前位置。\n\n"
            "运用逻辑推理追踪物体在每一步中的变化：\n"
            "1. 确定物体最初被放置的位置\n"
            "2. 追踪所有的移动或转移\n"
            "3. 特别注意任何容器的翻转或倒置\n"
            "4. 确定最终的位置\n\n"
            "{question}\n"
            "请用一个词回答，指出物体的位置。"
        ),
    },
    "ua": {
        "minimal": "{steps_text}\n\n{question}\nВідповідь:",
        "casual": "{steps_text} {question} Дай відповідь одним словом.",
        "linguistic": (
            "{steps_text}\n\n"
            "На основі послідовності дій, описаних вище, визначте "
            "поточне місцезнаходження {object}.\n\n"
            "Застосуйте логічне міркування для відстеження об'єкта на кожному кроці:\n"
            "1. Визначте, де об'єкт був розміщений спочатку\n"
            "2. Відстежте будь-які переміщення або передачі\n"
            "3. Зверніть особливу увагу на будь-яке перевертання або перекидання контейнерів\n"
            "4. Визначте кінцеве місцезнаходження\n\n"
            "{question}\n"
            "Надайте відповідь одним словом, що вказує на місцезнаходження."
        ),
    },
}
