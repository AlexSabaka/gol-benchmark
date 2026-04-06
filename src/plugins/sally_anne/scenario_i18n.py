"""
Multilingual translations for Sally-Anne scenario generation.

All localized content for 6 languages: en, es, fr, de, zh, ua.
Covers narrative templates, question templates, objects, containers,
pronouns, names, and leave activities.

Gender-aware templates:
- UA: past-tense verbs differ by subject gender; possessives differ by
  object gender; nouns have nominative / accusative / locative / genitive.
- FR: possessives depend on OBJECT gender (son livre / sa balle);
  ``absent`` vs ``absente`` depends on subject gender; question pronoun
  ``il`` / ``elle`` depends on subject gender.
- ES / DE: articles depend on noun gender (resolved at build time).
"""

# ── Narrative sentence templates ────────────────────────────────────────
# Keys: place, leave, move, witness, witness_move, return
#
# Templates that need gender inflection are stored as
#   {"m": {...}, "f": {...}}
# Others are flat dicts.  ``pick_templates`` handles both.
#
# Placeholder overview
#   {name}             character name
#   {poss}             possessive (resolved by builder, object-gender-aware)
#   {obj}              object display name (correct case for the slot)
#   {container}        container display name (correct case for the slot)
#   {container_a/b}    container A / B display name
#   {leave_activity}   translated activity string
#
# UA-specific extra placeholders:
#   {obj_acc}          object accusative
#   {container_acc}    container accusative
#   {container_a_gen}  container A genitive
#   {container_b_acc}  container B accusative
#
# FR-specific extra placeholders:
#   {art_def}          definite article for container (le/la)
#   {art_def_obj}      definite article for object
#   {prep_from}        "du" / "de la" (from the ...)
#   {pron_obj}         object pronoun "le" / "la"
#   {art_def_cont_b}   definite article for container B
#
# ES-specific extra placeholders:
#   {art_def_obj}      definite article for object (el/la)
#   {art_def_cont}     definite article for container
#   {art_def_cont_a}   definite article for container A
#   {art_def_cont_b}   definite article for container B
#   {pron_obj}         object pronoun (lo/la)
#
# DE-specific extra placeholders:
#   {art_acc_obj}      accusative article for object (den/die/das)
#   {art_acc_cont}     accusative article for container
#   {art_acc_cont_a}   accusative article for container A
#   {art_acc_cont_b}   accusative article for container B
#   {art_dat_cont_a}   dative article for container A ("aus dem/der")
#   {pron_obj}         accusative pronoun for object (ihn/sie/es)
#   {poss_dat}         possessive + dative ending for object ("seinem/seiner/seinem")

NARRATIVE_TEMPLATES = {
    "en": {
        "place": "{name} puts {poss} {obj} in the {container}.",
        "leave": "{name} {leave_activity}.",
        "move": "While {name_a} is away, {name_b} takes the {obj} from the {container_a} and puts it in the {container_b}.",
        "witness": "{name} watches {name_a} put the {obj} in the {container}.",
        "witness_move": "{name} sees {name_b} move the {obj} to the {container_b}.",
        "return": "{name} returns.",
    },
    "es": {
        "place": "{name} pone {poss} {obj} en {art_def_cont} {container}.",
        "leave": "{name} {leave_activity}.",
        "move": "Mientras {name_a} est\u00e1 fuera, {name_b} saca {art_def_obj} {obj} {prep_from} {container_a} y {pron_obj} pone en {art_def_cont_b} {container_b}.",
        "witness": "{name} observa c\u00f3mo {name_a} pone {art_def_obj} {obj} en {art_def_cont} {container}.",
        "witness_move": "{name} ve a {name_b} mover {art_def_obj} {obj} a {art_def_cont_b} {container_b}.",
        "return": "{name} regresa.",
    },
    "fr": {
        "place": "{name} met {poss} {obj} dans {art_def} {container}.",
        "leave": "{name} {leave_activity}.",
        "move": "Pendant que {name_a} est {absent}, {name_b} prend {art_def_obj} {obj} {prep_from} {container_a} et {pron_obj} met dans {art_def_cont_b} {container_b}.",
        "witness": "{name} regarde {name_a} mettre {art_def_obj} {obj} dans {art_def} {container}.",
        "witness_move": "{name} voit {name_b} d\u00e9placer {art_def_obj} {obj} vers {art_def_cont_b} {container_b}.",
        "return": "{name} revient.",
    },
    "de": {
        "place": "{name} legt {poss_acc} {obj} in {art_acc_cont} {container}.",
        "leave": "{name} {leave_activity}.",
        "move": "W\u00e4hrend {name_a} weg ist, nimmt {name_b} {art_acc_obj} {obj} aus {art_dat_cont_a} {container_a} und legt {pron_obj} in {art_acc_cont_b} {container_b}.",
        "witness": "{name} beobachtet, wie {name_a} {art_acc_obj} {obj} in {art_acc_cont} {container} legt.",
        "witness_move": "{name} sieht, wie {name_b} {art_acc_obj} {obj} in {art_acc_cont_b} {container_b} legt.",
        "return": "{name} kommt zur\u00fcck.",
    },
    "zh": {
        "place": "{name}\u628a{poss}{obj}\u653e\u5728{container}\u91cc\u3002",
        "leave": "{name}{leave_activity}\u3002",
        "move": "\u8d81{name_a}\u4e0d\u5728\u7684\u65f6\u5019\uff0c{name_b}\u628a{obj}\u4ece{container_a}\u91cc\u62ff\u51fa\u6765\uff0c\u653e\u8fdb\u4e86{container_b}\u91cc\u3002",
        "witness": "{name}\u770b\u5230{name_a}\u628a{obj}\u653e\u5728{container}\u91cc\u3002",
        "witness_move": "{name}\u770b\u5230{name_b}\u628a{obj}\u79fb\u5230\u4e86{container_b}\u91cc\u3002",
        "return": "{name}\u56de\u6765\u4e86\u3002",
    },
    "ua": {
        "m": {
            "place": "{name} \u043f\u043e\u043a\u043b\u0430\u0432 {poss} {obj_acc} \u0443 {container_acc}.",
            "leave": "{name} {leave_activity}.",
            "move": "\u041f\u043e\u043a\u0438 {name_a} \u043d\u0435\u043c\u0430\u0454, {name_b} {took} {obj_acc} \u0437 {container_a_gen} \u0456 {put} \u0443 {container_b_acc}.",
            "witness": "{name} \u0441\u043f\u043e\u0441\u0442\u0435\u0440\u0456\u0433\u0430\u0432 \u0437\u0430 \u0432\u0441\u0456\u043c.",
            "witness_move": "{name} \u0431\u0430\u0447\u0438\u0432, \u044f\u043a {name_b} {moved} {obj_acc} \u0434\u043e {container_b_gen}.",
            "return": "{name} \u043f\u043e\u0432\u0435\u0440\u043d\u0443\u0432\u0441\u044f.",
        },
        "f": {
            "place": "{name} \u043f\u043e\u043a\u043b\u0430\u043b\u0430 {poss} {obj_acc} \u0443 {container_acc}.",
            "leave": "{name} {leave_activity}.",
            "move": "\u041f\u043e\u043a\u0438 {name_a} \u043d\u0435\u043c\u0430\u0454, {name_b} {took} {obj_acc} \u0437 {container_a_gen} \u0456 {put} \u0443 {container_b_acc}.",
            "witness": "{name} \u0441\u043f\u043e\u0441\u0442\u0435\u0440\u0456\u0433\u0430\u043b\u0430 \u0437\u0430 \u0432\u0441\u0456\u043c.",
            "witness_move": "{name} \u0431\u0430\u0447\u0438\u043b\u0430, \u044f\u043a {name_b} {moved} {obj_acc} \u0434\u043e {container_b_gen}.",
            "return": "{name} \u043f\u043e\u0432\u0435\u0440\u043d\u0443\u043b\u0430\u0441\u044f.",
        },
    },
}

# ── Question templates ──────────────────────────────────────────────────
# FR: ``-t-il`` / ``-t-elle`` depends on subject gender
# UA: ``\u0441\u0432\u0456\u0439`` / ``\u0441\u0432\u043e\u044e`` depends on OBJECT gender (resolved by builder)

QUESTION_TEMPLATES = {
    "en": "Where will {name} look for {poss} {obj}?",
    "es": "\u00bfD\u00f3nde buscar\u00e1 {name} {poss} {obj}?",
    "fr": {
        "m": "O\u00f9 {name} cherchera-t-il {poss} {obj}\u00a0?",
        "f": "O\u00f9 {name} cherchera-t-elle {poss} {obj}\u00a0?",
    },
    "de": "Wo wird {name} nach {poss_dat} {obj} suchen?",
    "zh": "{name}\u4f1a\u53bb\u54ea\u91cc\u627e{poss}{obj}\uff1f",
    "ua": "De {name} \u0448\u0443\u043a\u0430\u0442\u0438\u043c\u0435 {poss} {obj_acc}?",
}

# ── Object translations ─────────────────────────────────────────────────
# Keys are English canonical names; values vary by language:
#   en / zh : plain string
#   es / fr : {"word": ..., "gender": "m"/"f"}
#   de      : {"word": ..., "gender": "m"/"f"/"n"}
#   ua      : {"nom": ..., "acc": ..., "loc": ..., "gen": ..., "gender": "m"/"f"}

OBJECTS = {
    "en": {
        "marble": "marble",
        "ball": "ball",
        "toy": "toy",
        "book": "book",
        "doll": "doll",
        "keys": "keys",
    },
    "es": {
        "marble": {"word": "canica", "gender": "f"},
        "ball": {"word": "pelota", "gender": "f"},
        "toy": {"word": "juguete", "gender": "m"},
        "book": {"word": "libro", "gender": "m"},
        "doll": {"word": "mu\u00f1eca", "gender": "f"},
        "keys": {"word": "llaves", "gender": "f"},
    },
    "fr": {
        "marble": {"word": "bille", "gender": "f"},
        "ball": {"word": "balle", "gender": "f"},
        "toy": {"word": "jouet", "gender": "m"},
        "book": {"word": "livre", "gender": "m"},
        "doll": {"word": "poup\u00e9e", "gender": "f"},
        "keys": {"word": "cl\u00e9s", "gender": "f"},
    },
    "de": {
        "marble": {"word": "Murmel", "gender": "f"},
        "ball": {"word": "Ball", "gender": "m"},
        "toy": {"word": "Spielzeug", "gender": "n"},
        "book": {"word": "Buch", "gender": "n"},
        "doll": {"word": "Puppe", "gender": "f"},
        "keys": {"word": "Schl\u00fcssel", "gender": "m"},
    },
    "zh": {
        "marble": "\u5f39\u73e0",
        "ball": "\u7403",
        "toy": "\u73a9\u5177",
        "book": "\u4e66",
        "doll": "\u5a03\u5a03",
        "keys": "\u94a5\u5319",
    },
    "ua": {
        "marble": {"nom": "\u043a\u0443\u043b\u044c\u043a\u0430", "acc": "\u043a\u0443\u043b\u044c\u043a\u0443", "loc": "\u043a\u0443\u043b\u044c\u0446\u0456", "gen": "\u043a\u0443\u043b\u044c\u043a\u0438", "gender": "f"},
        "ball": {"nom": "\u043c\u2019\u044f\u0447", "acc": "\u043c\u2019\u044f\u0447", "loc": "\u043c\u2019\u044f\u0447\u0456", "gen": "\u043c\u2019\u044f\u0447\u0430", "gender": "m"},
        "toy": {"nom": "\u0456\u0433\u0440\u0430\u0448\u043a\u0430", "acc": "\u0456\u0433\u0440\u0430\u0448\u043a\u0443", "loc": "\u0456\u0433\u0440\u0430\u0448\u0446\u0456", "gen": "\u0456\u0433\u0440\u0430\u0448\u043a\u0438", "gender": "f"},
        "book": {"nom": "\u043a\u043d\u0438\u0433\u0430", "acc": "\u043a\u043d\u0438\u0433\u0443", "loc": "\u043a\u043d\u0438\u0437\u0456", "gen": "\u043a\u043d\u0438\u0433\u0438", "gender": "f"},
        "doll": {"nom": "\u043b\u044f\u043b\u044c\u043a\u0430", "acc": "\u043b\u044f\u043b\u044c\u043a\u0443", "loc": "\u043b\u044f\u043b\u044c\u0446\u0456", "gen": "\u043b\u044f\u043b\u044c\u043a\u0438", "gender": "f"},
        "keys": {"nom": "\u043a\u043b\u044e\u0447\u0456", "acc": "\u043a\u043b\u044e\u0447\u0456", "loc": "\u043a\u043b\u044e\u0447\u0430\u0445", "gen": "\u043a\u043b\u044e\u0447\u0456\u0432", "gender": "m"},
    },
}

# ── Container translations ──────────────────────────────────────────────

CONTAINERS = {
    "en": {
        "basket": "basket",
        "box": "box",
        "bag": "bag",
        "drawer": "drawer",
        "cupboard": "cupboard",
        "pocket": "pocket",
    },
    "es": {
        "basket": {"word": "cesta", "gender": "f"},
        "box": {"word": "caja", "gender": "f"},
        "bag": {"word": "bolsa", "gender": "f"},
        "drawer": {"word": "caj\u00f3n", "gender": "m"},
        "cupboard": {"word": "armario", "gender": "m"},
        "pocket": {"word": "bolsillo", "gender": "m"},
    },
    "fr": {
        "basket": {"word": "panier", "gender": "m"},
        "box": {"word": "bo\u00eete", "gender": "f"},
        "bag": {"word": "sac", "gender": "m"},
        "drawer": {"word": "tiroir", "gender": "m"},
        "cupboard": {"word": "placard", "gender": "m"},
        "pocket": {"word": "poche", "gender": "f"},
    },
    "de": {
        "basket": {"word": "Korb", "gender": "m"},
        "box": {"word": "Kiste", "gender": "f"},
        "bag": {"word": "Tasche", "gender": "f"},
        "drawer": {"word": "Schublade", "gender": "f"},
        "cupboard": {"word": "Schrank", "gender": "m"},
        "pocket": {"word": "Tasche", "gender": "f"},
    },
    "zh": {
        "basket": "\u7bee\u5b50",
        "box": "\u76d2\u5b50",
        "bag": "\u888b\u5b50",
        "drawer": "\u62bd\u5c49",
        "cupboard": "\u67dc\u5b50",
        "pocket": "\u53e3\u888b",
    },
    "ua": {
        "basket": {"nom": "\u043a\u043e\u0448\u0438\u043a", "acc": "\u043a\u043e\u0448\u0438\u043a", "loc": "\u043a\u043e\u0448\u0438\u043a\u0443", "gen": "\u043a\u043e\u0448\u0438\u043a\u0430", "gender": "m"},
        "box": {"nom": "\u043a\u043e\u0440\u043e\u0431\u043a\u0430", "acc": "\u043a\u043e\u0440\u043e\u0431\u043a\u0443", "loc": "\u043a\u043e\u0440\u043e\u0431\u0446\u0456", "gen": "\u043a\u043e\u0440\u043e\u0431\u043a\u0438", "gender": "f"},
        "bag": {"nom": "\u0441\u0443\u043c\u043a\u0430", "acc": "\u0441\u0443\u043c\u043a\u0443", "loc": "\u0441\u0443\u043c\u0446\u0456", "gen": "\u0441\u0443\u043c\u043a\u0438", "gender": "f"},
        "drawer": {"nom": "\u0448\u0443\u0445\u043b\u044f\u0434\u0430", "acc": "\u0448\u0443\u0445\u043b\u044f\u0434\u0443", "loc": "\u0448\u0443\u0445\u043b\u044f\u0434\u0456", "gen": "\u0448\u0443\u0445\u043b\u044f\u0434\u0438", "gender": "f"},
        "cupboard": {"nom": "\u0448\u0430\u0444\u0430", "acc": "\u0448\u0430\u0444\u0443", "loc": "\u0448\u0430\u0444\u0456", "gen": "\u0448\u0430\u0444\u0438", "gender": "f"},
        "pocket": {"nom": "\u043a\u0438\u0448\u0435\u043d\u044f", "acc": "\u043a\u0438\u0448\u0435\u043d\u044e", "loc": "\u043a\u0438\u0448\u0435\u043d\u0456", "gen": "\u043a\u0438\u0448\u0435\u043d\u0456", "gender": "f"},
    },
}

# ── Pronoun translations ────────────────────────────────────────────────
# NOTE: FR and UA possessives depend on OBJECT gender, not subject gender.
#   - FR:  son (m-obj) / sa (f-obj)  -- same regardless of speaker gender
#   - UA:  \u0441\u0432\u0456\u0439 (m-obj) / \u0441\u0432\u043e\u044e (f-obj)  -- same regardless of speaker gender
#   - DE:  possessive depends on SUBJECT gender but also on object case/gender
#
# Subject/object pronouns still depend on character gender as expected.
# Possessives stored here are subject-gender-based; object-gender-aware
# possessives are resolved at build time in scenario_builder.py.

PRONOUNS = {
    "en": {
        "male": {"subject": "he", "object": "him", "possessive": "his"},
        "female": {"subject": "she", "object": "her", "possessive": "her"},
    },
    "es": {
        "male": {"subject": "\u00e9l", "object": "lo", "possessive": "su"},
        "female": {"subject": "ella", "object": "la", "possessive": "su"},
    },
    "fr": {
        "male": {"subject": "il", "object": "le", "possessive": "son"},
        "female": {"subject": "elle", "object": "la", "possessive": "sa"},
    },
    "de": {
        "male": {"subject": "er", "object": "ihn", "possessive": "sein"},
        "female": {"subject": "sie", "object": "sie", "possessive": "ihr"},
    },
    "zh": {
        "male": {"subject": "\u4ed6", "object": "\u4ed6", "possessive": "\u4ed6\u7684"},
        "female": {"subject": "\u5979", "object": "\u5979", "possessive": "\u5979\u7684"},
    },
    "ua": {
        "male": {"subject": "\u0432\u0456\u043d", "object": "\u0439\u043e\u0433\u043e", "possessive": "\u0441\u0432\u0456\u0439"},
        "female": {"subject": "\u0432\u043e\u043d\u0430", "object": "\u0457\u0457", "possessive": "\u0441\u0432\u043e\u044e"},
    },
}

# ── Culturally appropriate names ────────────────────────────────────────

NAMES = {
    "en": {
        "male": ["Alex", "Ben", "Charlie", "David", "Ethan", "Frank", "George", "Henry"],
        "female": ["Alice", "Beth", "Clara", "Diana", "Emma", "Fiona", "Grace", "Hannah"],
    },
    "es": {
        "male": ["Carlos", "Miguel", "Pedro", "Juan", "Diego", "Pablo", "Luis", "Andr\u00e9s"],
        "female": ["Mar\u00eda", "Ana", "Luc\u00eda", "Carmen", "Elena", "Sof\u00eda", "Paula", "Laura"],
    },
    "fr": {
        "male": ["Pierre", "Jean", "Louis", "Paul", "Marc", "Andr\u00e9", "Henri", "Claude"],
        "female": ["Marie", "Claire", "Sophie", "Julie", "Emma", "L\u00e9a", "Camille", "Louise"],
    },
    "de": {
        "male": ["Hans", "Karl", "Thomas", "Max", "Felix", "Paul", "Leon", "Lukas"],
        "female": ["Anna", "Klara", "Sophie", "Marie", "Lena", "Hannah", "Mia", "Emma"],
    },
    "zh": {
        "male": ["\u5c0f\u660e", "\u5c0f\u521a", "\u5c0f\u5f3a", "\u5c0f\u534e", "\u5c0f\u4eae", "\u5c0f\u519b", "\u5c0f\u4f1f", "\u5c0f\u6770"],
        "female": ["\u5c0f\u7ea2", "\u5c0f\u4e3d", "\u5c0f\u82b3", "\u5c0f\u96ea", "\u5c0f\u4e91", "\u5c0f\u6708", "\u5c0f\u73b2", "\u5c0f\u6167"],
    },
    "ua": {
        "male": ["\u0406\u0432\u0430\u043d", "\u0410\u043d\u0434\u0440\u0456\u0439", "\u041e\u043b\u0435\u0433", "\u041f\u0435\u0442\u0440\u043e", "\u041c\u0438\u043a\u043e\u043b\u0430", "\u0422\u0430\u0440\u0430\u0441", "\u0414\u043c\u0438\u0442\u0440\u043e", "\u0411\u043e\u0433\u0434\u0430\u043d"],
        "female": ["\u041e\u043b\u0435\u043d\u0430", "\u041c\u0430\u0440\u0456\u044f", "\u041d\u0430\u0442\u0430\u043b\u0456\u044f", "\u041e\u043a\u0441\u0430\u043d\u0430", "\u0406\u0440\u0438\u043d\u0430", "\u0422\u0435\u0442\u044f\u043d\u0430", "\u042e\u043b\u0456\u044f", "\u041a\u0430\u0442\u0435\u0440\u0438\u043d\u0430"],
    },
}

# ── Leave activities ────────────────────────────────────────────────────
# UA leave activities are gender-split: past-tense verb forms differ.

LEAVE_ACTIVITIES = {
    "en": [
        "goes for a walk",
        "goes outside",
        "leaves the room",
        "goes to the kitchen",
    ],
    "es": [
        "sale a dar un paseo",
        "sale afuera",
        "sale de la habitaci\u00f3n",
        "va a la cocina",
    ],
    "fr": [
        "part se promener",
        "sort dehors",
        "quitte la pi\u00e8ce",
        "va \u00e0 la cuisine",
    ],
    "de": [
        "geht spazieren",
        "geht nach drau\u00dfen",
        "verl\u00e4sst den Raum",
        "geht in die K\u00fcche",
    ],
    "zh": [
        "\u51fa\u53bb\u6563\u6b65\u4e86",
        "\u51fa\u53bb\u4e86",
        "\u79bb\u5f00\u4e86\u623f\u95f4",
        "\u53bb\u4e86\u53a8\u623f",
    ],
    "ua": {
        "m": [
            "\u043f\u0456\u0448\u043e\u0432 \u043d\u0430 \u043f\u0440\u043e\u0433\u0443\u043b\u044f\u043d\u043a\u0443",
            "\u0432\u0438\u0439\u0448\u043e\u0432 \u043d\u0430\u0434\u0432\u0456\u0440",
            "\u0432\u0438\u0439\u0448\u043e\u0432 \u0437 \u043a\u0456\u043c\u043d\u0430\u0442\u0438",
            "\u043f\u0456\u0448\u043e\u0432 \u043d\u0430 \u043a\u0443\u0445\u043d\u044e",
        ],
        "f": [
            "\u043f\u0456\u0448\u043b\u0430 \u043d\u0430 \u043f\u0440\u043e\u0433\u0443\u043b\u044f\u043d\u043a\u0443",
            "\u0432\u0438\u0439\u0448\u043b\u0430 \u043d\u0430\u0434\u0432\u0456\u0440",
            "\u0432\u0438\u0439\u0448\u043b\u0430 \u0437 \u043a\u0456\u043c\u043d\u0430\u0442\u0438",
            "\u043f\u0456\u0448\u043b\u0430 \u043d\u0430 \u043a\u0443\u0445\u043d\u044e",
        ],
    },
}

# ── Distractor templates ────────────────────────────────────────────────
# Distractors use indefinite articles; resolved at build time for
# languages with grammatical gender.

DISTRACTOR_TEMPLATE = {
    "en": "There is a {d_obj} on the {d_loc}.",
    "es": "Hay {d_art} {d_obj} en {d_loc_art} {d_loc}.",
    "fr": "Il y a {d_art} {d_obj} sur {d_loc_art} {d_loc}.",
    "de": "Es gibt {d_art} {d_obj} auf {d_loc_art} {d_loc}.",
    "zh": "{d_loc}\u4e0a\u6709\u4e00\u4e2a{d_obj}\u3002",
    "ua": "\u041d\u0430 {d_loc} \u0454 {d_obj}.",
}

DISTRACTOR_OBJECTS = {
    "en": ["book", "cup", "pencil", "paper", "phone", "wallet", "keys", "hat"],
    "es": [
        {"word": "libro", "gender": "m"},
        {"word": "taza", "gender": "f"},
        {"word": "l\u00e1piz", "gender": "m"},
        {"word": "papel", "gender": "m"},
        {"word": "tel\u00e9fono", "gender": "m"},
        {"word": "cartera", "gender": "f"},
        {"word": "llaves", "gender": "f"},
        {"word": "sombrero", "gender": "m"},
    ],
    "fr": [
        {"word": "livre", "gender": "m"},
        {"word": "tasse", "gender": "f"},
        {"word": "crayon", "gender": "m"},
        {"word": "papier", "gender": "m"},
        {"word": "t\u00e9l\u00e9phone", "gender": "m"},
        {"word": "portefeuille", "gender": "m"},
        {"word": "cl\u00e9s", "gender": "f"},
        {"word": "chapeau", "gender": "m"},
    ],
    "de": [
        {"word": "Buch", "gender": "n"},
        {"word": "Tasse", "gender": "f"},
        {"word": "Bleistift", "gender": "m"},
        {"word": "Papier", "gender": "n"},
        {"word": "Telefon", "gender": "n"},
        {"word": "Geldb\u00f6rse", "gender": "f"},
        {"word": "Schl\u00fcssel", "gender": "m"},
        {"word": "Hut", "gender": "m"},
    ],
    "zh": ["\u4e66", "\u676f\u5b50", "\u94c5\u7b14", "\u7eb8", "\u624b\u673a", "\u94b1\u5305", "\u94a5\u5319", "\u5e3d\u5b50"],
    "ua": ["\u043a\u043d\u0438\u0433\u0430", "\u0447\u0430\u0448\u043a\u0430", "\u043e\u043b\u0456\u0432\u0435\u0446\u044c", "\u043f\u0430\u043f\u0456\u0440", "\u0442\u0435\u043b\u0435\u0444\u043e\u043d", "\u0433\u0430\u043c\u0430\u043d\u0435\u0446\u044c", "\u043a\u043b\u044e\u0447\u0456", "\u043a\u0430\u043f\u0435\u043b\u044e\u0445"],
}

DISTRACTOR_LOCATIONS = {
    "en": ["table", "shelf", "chair", "counter", "desk", "window"],
    "es": [
        {"word": "mesa", "gender": "f"},
        {"word": "estante", "gender": "m"},
        {"word": "silla", "gender": "f"},
        {"word": "mostrador", "gender": "m"},
        {"word": "escritorio", "gender": "m"},
        {"word": "ventana", "gender": "f"},
    ],
    "fr": [
        {"word": "table", "gender": "f"},
        {"word": "\u00e9tag\u00e8re", "gender": "f"},
        {"word": "chaise", "gender": "f"},
        {"word": "comptoir", "gender": "m"},
        {"word": "bureau", "gender": "m"},
        {"word": "fen\u00eatre", "gender": "f"},
    ],
    "de": [
        {"word": "Tisch", "gender": "m"},
        {"word": "Regal", "gender": "n"},
        {"word": "Stuhl", "gender": "m"},
        {"word": "Theke", "gender": "f"},
        {"word": "Schreibtisch", "gender": "m"},
        {"word": "Fenster", "gender": "n"},
    ],
    "zh": ["\u684c\u5b50", "\u67b6\u5b50", "\u6905\u5b50", "\u67dc\u53f0", "\u4e66\u684c", "\u7a97\u53f0"],
    "ua": ["\u0441\u0442\u043e\u043b\u0456", "\u043f\u043e\u043b\u0438\u0446\u0456", "\u0441\u0442\u0456\u043b\u044c\u0446\u0456", "\u0441\u0442\u0456\u0439\u0446\u0456", "\u043f\u0438\u0441\u044c\u043c\u043e\u0432\u043e\u043c\u0443 \u0441\u0442\u043e\u043b\u0456", "\u0432\u0456\u043a\u043d\u0456"],
}
