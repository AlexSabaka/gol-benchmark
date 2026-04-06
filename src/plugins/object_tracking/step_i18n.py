"""Multilingual translations for Object Tracking scenario generation.

Gender-aware templates and case-inflected vocabulary for ES, FR, DE, UA.
Uses grammar_utils (article, pick_templates, resolve_vocab, vocab_gender)
for runtime resolution.
"""

from src.plugins.grammar_utils import (
    article,
    pick_templates,
    resolve_vocab,
    vocab_gender,
)

# ── Localized vocabulary ─────────────────────────────────────────────────
# ES / FR / DE: {"word": ..., "gender": ...}
# UA:           {"nom": ..., "acc": ..., "loc": ..., "gender": ...}
# EN / ZH:     plain strings

OBJECTS = {
    "en": {
        "grape": "grape", "marble": "marble", "keys": "keys", "coin": "coin",
        "ring": "ring", "pill": "pill", "button": "button", "pebble": "pebble",
    },
    "es": {
        "grape": {"word": "uva", "gender": "f"},
        "marble": {"word": "canica", "gender": "f"},
        "keys": {"word": "llaves", "gender": "f"},
        "coin": {"word": "moneda", "gender": "f"},
        "ring": {"word": "anillo", "gender": "m"},
        "pill": {"word": "pastilla", "gender": "f"},
        "button": {"word": "botón", "gender": "m"},
        "pebble": {"word": "piedrita", "gender": "f"},
    },
    "fr": {
        "grape": {"word": "raisin", "gender": "m"},
        "marble": {"word": "bille", "gender": "f"},
        "keys": {"word": "clés", "gender": "f"},
        "coin": {"word": "pièce", "gender": "f"},
        "ring": {"word": "bague", "gender": "f"},
        "pill": {"word": "pilule", "gender": "f"},
        "button": {"word": "bouton", "gender": "m"},
        "pebble": {"word": "caillou", "gender": "m"},
    },
    "de": {
        "grape": {"word": "Traube", "gender": "f"},
        "marble": {"word": "Murmel", "gender": "f"},
        "keys": {"word": "Schlüssel", "gender": "m"},
        "coin": {"word": "Münze", "gender": "f"},
        "ring": {"word": "Ring", "gender": "m"},
        "pill": {"word": "Pille", "gender": "f"},
        "button": {"word": "Knopf", "gender": "m"},
        "pebble": {"word": "Kiesel", "gender": "m"},
    },
    "zh": {
        "grape": "葡萄", "marble": "弹珠", "keys": "钥匙", "coin": "硬币",
        "ring": "戒指", "pill": "药丸", "button": "纽扣", "pebble": "小石子",
    },
    "ua": {
        "grape":  {"nom": "виноградина", "acc": "виноградину", "loc": "виноградині", "gender": "f"},
        "marble": {"nom": "кулька",      "acc": "кульку",      "loc": "кульці",      "gender": "f"},
        "keys":   {"nom": "ключі",       "acc": "ключі",       "loc": "ключах",      "gender": "m"},
        "coin":   {"nom": "монета",      "acc": "монету",      "loc": "монеті",      "gender": "f"},
        "ring":   {"nom": "каблучка",    "acc": "каблучку",    "loc": "каблучці",    "gender": "f"},
        "pill":   {"nom": "пігулка",     "acc": "пігулку",     "loc": "пігулці",     "gender": "f"},
        "button": {"nom": "ґудзик",      "acc": "ґудзик",      "loc": "ґудзику",     "gender": "m"},
        "pebble": {"nom": "камінчик",    "acc": "камінчик",    "loc": "камінчику",   "gender": "m"},
    },
}

CONTAINERS = {
    "en": {
        "cup": "cup", "bowl": "bowl", "bucket": "bucket", "mug": "mug",
        "box": "box", "jar": "jar", "glass": "glass",
    },
    "es": {
        "cup": {"word": "taza", "gender": "f"},
        "bowl": {"word": "tazón", "gender": "m"},
        "bucket": {"word": "balde", "gender": "m"},
        "mug": {"word": "jarra", "gender": "f"},
        "box": {"word": "caja", "gender": "f"},
        "jar": {"word": "frasco", "gender": "m"},
        "glass": {"word": "vaso", "gender": "m"},
    },
    "fr": {
        "cup": {"word": "tasse", "gender": "f"},
        "bowl": {"word": "bol", "gender": "m"},
        "bucket": {"word": "seau", "gender": "m"},
        "mug": {"word": "mug", "gender": "m"},
        "box": {"word": "boîte", "gender": "f"},
        "jar": {"word": "bocal", "gender": "m"},
        "glass": {"word": "verre", "gender": "m"},
    },
    "de": {
        "cup": {"word": "Tasse", "gender": "f"},
        "bowl": {"word": "Schüssel", "gender": "f"},
        "bucket": {"word": "Eimer", "gender": "m"},
        "mug": {"word": "Becher", "gender": "m"},
        "box": {"word": "Kiste", "gender": "f"},
        "jar": {"word": "Glas", "gender": "n"},
        "glass": {"word": "Glas", "gender": "n"},
    },
    "zh": {
        "cup": "杯子", "bowl": "碗", "bucket": "桶", "mug": "马克杯",
        "box": "盒子", "jar": "罐子", "glass": "玻璃杯",
    },
    "ua": {
        "cup":    {"nom": "чашка",   "acc": "чашку",   "loc": "чашці",   "gender": "f"},
        "bowl":   {"nom": "миска",   "acc": "миску",   "loc": "мисці",   "gender": "f"},
        "bucket": {"nom": "відро",   "acc": "відро",   "loc": "відрі",   "gender": "n"},
        "mug":    {"nom": "кухоль",  "acc": "кухоль",  "loc": "кухлі",   "gender": "m"},
        "box":    {"nom": "коробка", "acc": "коробку", "loc": "коробці", "gender": "f"},
        "jar":    {"nom": "банка",   "acc": "банку",   "loc": "банці",   "gender": "f"},
        "glass":  {"nom": "склянка", "acc": "склянку", "loc": "склянці", "gender": "f"},
    },
}

LOCATIONS = {
    "en": {
        "counter": "counter", "table": "table", "shelf": "shelf",
        "desk": "desk", "dresser": "dresser", "nightstand": "nightstand",
    },
    "es": {
        "counter": {"word": "mostrador", "gender": "m"},
        "table": {"word": "mesa", "gender": "f"},
        "shelf": {"word": "estante", "gender": "m"},
        "desk": {"word": "escritorio", "gender": "m"},
        "dresser": {"word": "cómoda", "gender": "f"},
        "nightstand": {"word": "mesita de noche", "gender": "f"},
    },
    "fr": {
        "counter": {"word": "comptoir", "gender": "m"},
        "table": {"word": "table", "gender": "f"},
        "shelf": {"word": "étagère", "gender": "f"},
        "desk": {"word": "bureau", "gender": "m"},
        "dresser": {"word": "commode", "gender": "f"},
        "nightstand": {"word": "table de nuit", "gender": "f"},
    },
    "de": {
        "counter": {"word": "Theke", "gender": "f"},
        "table": {"word": "Tisch", "gender": "m"},
        "shelf": {"word": "Regal", "gender": "n"},
        "desk": {"word": "Schreibtisch", "gender": "m"},
        "dresser": {"word": "Kommode", "gender": "f"},
        "nightstand": {"word": "Nachttisch", "gender": "m"},
    },
    "zh": {
        "counter": "柜台", "table": "桌子", "shelf": "架子",
        "desk": "书桌", "dresser": "梳妆台", "nightstand": "床头柜",
    },
    "ua": {
        "counter":    {"nom": "стійка",         "acc": "стійку",         "loc": "стійці",         "gender": "f"},
        "table":      {"nom": "стіл",           "acc": "стіл",           "loc": "столі",          "gender": "m"},
        "shelf":      {"nom": "полиця",         "acc": "полицю",         "loc": "полиці",         "gender": "f"},
        "desk":       {"nom": "письмовий стіл", "acc": "письмовий стіл", "loc": "письмовому столі", "gender": "m"},
        "dresser":    {"nom": "комод",          "acc": "комод",          "loc": "комоді",         "gender": "m"},
        "nightstand": {"nom": "тумбочка",       "acc": "тумбочку",       "loc": "тумбочці",       "gender": "f"},
    },
}

ROOMS = {
    "en": ["living room", "kitchen", "bedroom", "hallway", "bathroom"],
    "es": [
        {"word": "sala", "gender": "f"},
        {"word": "cocina", "gender": "f"},
        {"word": "dormitorio", "gender": "m"},
        {"word": "pasillo", "gender": "m"},
        {"word": "baño", "gender": "m"},
    ],
    "fr": [
        {"word": "salon", "gender": "m"},
        {"word": "cuisine", "gender": "f"},
        {"word": "chambre", "gender": "f"},
        {"word": "couloir", "gender": "m"},
        {"word": "salle de bain", "gender": "f"},
    ],
    "de": [
        {"word": "Wohnzimmer", "gender": "n"},
        {"word": "Küche", "gender": "f"},
        {"word": "Schlafzimmer", "gender": "n"},
        {"word": "Flur", "gender": "m"},
        {"word": "Badezimmer", "gender": "n"},
    ],
    "zh": ["客厅", "厨房", "卧室", "走廊", "浴室"],
    "ua": [
        {"nom": "вітальня",      "gen": "вітальні",      "loc": "вітальні",      "gender": "f"},
        {"nom": "кухня",         "gen": "кухні",         "loc": "кухні",         "gender": "f"},
        {"nom": "спальня",       "gen": "спальні",       "loc": "спальні",       "gender": "f"},
        {"nom": "коридор",       "gen": "коридору",      "loc": "коридорі",      "gender": "m"},
        {"nom": "ванна кімната", "gen": "ванної кімнати", "loc": "ванній кімнаті", "gender": "f"},
    ],
}

NEARBY_OBJECTS = {
    "en": ["clock", "picture", "plant", "lamp", "chair", "window"],
    "es": [
        {"word": "reloj", "gender": "m"},
        {"word": "cuadro", "gender": "m"},
        {"word": "planta", "gender": "f"},
        {"word": "lámpara", "gender": "f"},
        {"word": "silla", "gender": "f"},
        {"word": "ventana", "gender": "f"},
    ],
    "fr": [
        {"word": "horloge", "gender": "f"},
        {"word": "tableau", "gender": "m"},
        {"word": "plante", "gender": "f"},
        {"word": "lampe", "gender": "f"},
        {"word": "chaise", "gender": "f"},
        {"word": "fenêtre", "gender": "f"},
    ],
    "de": [
        {"word": "Uhr", "gender": "f"},
        {"word": "Bild", "gender": "n"},
        {"word": "Pflanze", "gender": "f"},
        {"word": "Lampe", "gender": "f"},
        {"word": "Stuhl", "gender": "m"},
        {"word": "Fenster", "gender": "n"},
    ],
    "zh": ["时钟", "画", "植物", "台灯", "椅子", "窗户"],
    "ua": [
        {"nom": "годинник", "acc": "годинник", "gender": "m"},
        {"nom": "картина",  "acc": "картину",  "gender": "f"},
        {"nom": "рослина",  "acc": "рослину",  "gender": "f"},
        {"nom": "лампа",    "acc": "лампу",    "gender": "f"},
        {"nom": "стілець",  "acc": "стілець",  "gender": "m"},
        {"nom": "вікно",    "acc": "вікно",    "gender": "n"},
    ],
}

APPLIANCES = {
    "en": {
        "microwave": "microwave", "oven": "oven",
        "dishwasher": "dishwasher", "refrigerator": "refrigerator",
    },
    "es": {
        "microwave": {"word": "microondas", "gender": "m"},
        "oven": {"word": "horno", "gender": "m"},
        "dishwasher": {"word": "lavavajillas", "gender": "m"},
        "refrigerator": {"word": "refrigerador", "gender": "m"},
    },
    "fr": {
        "microwave": {"word": "micro-ondes", "gender": "m"},
        "oven": {"word": "four", "gender": "m"},
        "dishwasher": {"word": "lave-vaisselle", "gender": "m"},
        "refrigerator": {"word": "réfrigérateur", "gender": "m"},
    },
    "de": {
        "microwave": {"word": "Mikrowelle", "gender": "f"},
        "oven": {"word": "Ofen", "gender": "m"},
        "dishwasher": {"word": "Geschirrspüler", "gender": "m"},
        "refrigerator": {"word": "Kühlschrank", "gender": "m"},
    },
    "zh": {
        "microwave": "微波炉", "oven": "烤箱",
        "dishwasher": "洗碗机", "refrigerator": "冰箱",
    },
    "ua": {
        "microwave":    {"nom": "мікрохвильовка", "acc": "мікрохвильовку", "gender": "f"},
        "oven":         {"nom": "духовка",        "acc": "духовку",        "gender": "f"},
        "dishwasher":   {"nom": "посудомийка",    "acc": "посудомийку",    "gender": "f"},
        "refrigerator": {"nom": "холодильник",    "acc": "холодильник",    "gender": "m"},
    },
}

MOVE_LOCATIONS = {
    "en": {
        "microwave": "microwave", "refrigerator": "refrigerator",
        "oven": "oven", "sink": "sink", "drawer": "drawer", "cabinet": "cabinet",
    },
    "es": {
        "microwave": {"word": "microondas", "gender": "m"},
        "refrigerator": {"word": "refrigerador", "gender": "m"},
        "oven": {"word": "horno", "gender": "m"},
        "sink": {"word": "fregadero", "gender": "m"},
        "drawer": {"word": "cajón", "gender": "m"},
        "cabinet": {"word": "armario", "gender": "m"},
    },
    "fr": {
        "microwave": {"word": "micro-ondes", "gender": "m"},
        "refrigerator": {"word": "réfrigérateur", "gender": "m"},
        "oven": {"word": "four", "gender": "m"},
        "sink": {"word": "évier", "gender": "m"},
        "drawer": {"word": "tiroir", "gender": "m"},
        "cabinet": {"word": "placard", "gender": "m"},
    },
    "de": {
        "microwave": {"word": "Mikrowelle", "gender": "f"},
        "refrigerator": {"word": "Kühlschrank", "gender": "m"},
        "oven": {"word": "Ofen", "gender": "m"},
        "sink": {"word": "Spüle", "gender": "f"},
        "drawer": {"word": "Schublade", "gender": "f"},
        "cabinet": {"word": "Schrank", "gender": "m"},
    },
    "zh": {
        "microwave": "微波炉", "refrigerator": "冰箱",
        "oven": "烤箱", "sink": "水槽", "drawer": "抽屉", "cabinet": "柜子",
    },
    "ua": {
        "microwave":    {"nom": "мікрохвильовка", "acc": "мікрохвильовку", "loc": "мікрохвильовці", "gender": "f"},
        "refrigerator": {"nom": "холодильник",    "acc": "холодильник",    "loc": "холодильнику",   "gender": "m"},
        "oven":         {"nom": "духовка",        "acc": "духовку",        "loc": "духовці",        "gender": "f"},
        "sink":         {"nom": "раковина",       "acc": "раковину",       "loc": "раковині",       "gender": "f"},
        "drawer":       {"nom": "шухляда",        "acc": "шухляду",        "loc": "шухляді",        "gender": "f"},
        "cabinet":      {"nom": "шафа",           "acc": "шафу",           "loc": "шафі",           "gender": "f"},
    },
}

# ── Scenario templates ───────────────────────────────────────────────────
# ES / FR / DE use article placeholders resolved at runtime.
# UA uses gender sub-dicts {"m": [...], "f": [...]}.
# FR uses gender sub-dicts for past-participle agreement where needed.

PLACEMENT = {
    "en": [
        "{subject} put a {object} in a {container} and sit the {container} on the {location}.",
        "{subject} place a {object} into a {container} on the {location}.",
        "{subject} drop a {object} in a {container} sitting on the {location}.",
        "{subject} put a {object} inside a {container} that is on the {location}.",
    ],
    "es": [
        "{subject} puso {art_indef_obj} {object} en {art_indef_cont} {container} y colocó {art_def_cont} {container} sobre {art_def_loc} {location}.",
        "{subject} colocó {art_indef_obj} {object} dentro de {art_indef_cont} {container} en {art_def_loc} {location}.",
        "{subject} dejó caer {art_indef_obj} {object} en {art_indef_cont} {container} que está en {art_def_loc} {location}.",
        "{subject} puso {art_indef_obj} {object} dentro de {art_indef_cont} {container} que está sobre {art_def_loc} {location}.",
    ],
    "fr": [
        "{subject} a mis {art_indef_obj} {object} dans {art_indef_cont} {container} et a posé {art_def_cont} {container} sur {art_def_loc} {location}.",
        "{subject} a placé {art_indef_obj} {object} dans {art_indef_cont} {container} sur {art_def_loc} {location}.",
        "{subject} a déposé {art_indef_obj} {object} dans {art_indef_cont} {container} sur {art_def_loc} {location}.",
        "{subject} a mis {art_indef_obj} {object} à l'intérieur d'{art_indef_cont} {container} qui se trouve sur {art_def_loc} {location}.",
    ],
    "de": [
        "{subject} legte {art_indef_obj_acc} {object} in {art_indef_cont_acc} {container} und stellte {art_def_cont_acc} {container} auf {art_def_loc_acc} {location}.",
        "{subject} platzierte {art_indef_obj_acc} {object} in {art_indef_cont_acc} {container} auf {art_def_loc_dat} {location}.",
        "{subject} ließ {art_indef_obj_acc} {object} in {art_indef_cont_acc} {container} fallen, {art_def_cont_nom} auf {art_def_loc_dat} {location} steht.",
        "{subject} legte {art_indef_obj_acc} {object} in {art_indef_cont_acc} {container}, {art_def_cont_nom} auf {art_def_loc_dat} {location} steht.",
    ],
    "zh": [
        "{subject}把一个{object}放进了一个{container}里，然后把{container}放在了{location}上。",
        "{subject}将一个{object}放入{location}上的一个{container}中。",
        "{subject}把一个{object}丢进了放在{location}上的一个{container}里。",
        "{subject}把一个{object}放在了{location}上的一个{container}里面。",
    ],
    "ua": {
        "m": [
            "{subject} поклав {object_acc} у {container_acc} і поставив {container_acc} на {location_loc}.",
            "{subject} помістив {object_acc} у {container_acc} на {location_loc}.",
            "{subject} кинув {object_acc} у {container_acc}, що стоїть на {location_loc}.",
            "{subject} поклав {object_acc} всередину {container_acc}, що знаходиться на {location_loc}.",
        ],
        "f": [
            "{subject} поклала {object_acc} у {container_acc} і поставила {container_acc} на {location_loc}.",
            "{subject} помістила {object_acc} у {container_acc} на {location_loc}.",
            "{subject} кинула {object_acc} у {container_acc}, що стоїть на {location_loc}.",
            "{subject} поклала {object_acc} всередину {container_acc}, що знаходиться на {location_loc}.",
        ],
    },
}

INVERSION = {
    "en": [
        "{subject} turn the {container} upside down.",
        "{subject} flip the {container} over.",
        "{subject} invert the {container}.",
        "{subject} tip the {container} upside down.",
    ],
    "es": [
        "{subject} volteó {art_def_cont} {container} boca abajo.",
        "{subject} dio la vuelta {art_def_cont_a} {container}.",
        "{subject} invirtió {art_def_cont} {container}.",
        "{subject} puso {art_def_cont} {container} boca abajo.",
    ],
    "fr": [
        "{subject} a retourné {art_def_cont} {container}.",
        "{subject} a mis {art_def_cont} {container} à l'envers.",
        "{subject} a inversé {art_def_cont} {container}.",
        "{subject} a renversé {art_def_cont} {container}.",
    ],
    "de": [
        "{subject} drehte {art_def_cont_acc} {container} um.",
        "{subject} stellte {art_def_cont_acc} {container} auf den Kopf.",
        "{subject} kippte {art_def_cont_acc} {container} um.",
        "{subject} wendete {art_def_cont_acc} {container}.",
    ],
    "zh": [
        "{subject}把{container}翻了过来。",
        "{subject}把{container}倒扣了。",
        "{subject}把{container}上下翻转了。",
        "{subject}把{container}倒置了。",
    ],
    "ua": {
        "m": [
            "{subject} перевернув {container_acc} догори дном.",
            "{subject} перекинув {container_acc}.",
            "{subject} перевернув {container_acc}.",
            "{subject} поставив {container_acc} догори дном.",
        ],
        "f": [
            "{subject} перевернула {container_acc} догори дном.",
            "{subject} перекинула {container_acc}.",
            "{subject} перевернула {container_acc}.",
            "{subject} поставила {container_acc} догори дном.",
        ],
    },
}

MOVEMENT = {
    "en": [
        "{subject} then place the {container} in the {location}.",
        "{subject} move the {container} to the {location}.",
        "{subject} put the {container} on the {location}.",
        "{subject} carry the {container} over to the {location}.",
    ],
    "es": [
        "{subject} luego colocó {art_def_cont} {container} en {art_def_loc} {location}.",
        "{subject} movió {art_def_cont} {container} {art_def_loc_a} {location}.",
        "{subject} puso {art_def_cont} {container} sobre {art_def_loc} {location}.",
        "{subject} llevó {art_def_cont} {container} {art_def_loc_a} {location}.",
    ],
    "fr": [
        "{subject} a ensuite posé {art_def_cont} {container} sur {art_def_loc} {location}.",
        "{subject} a déplacé {art_def_cont} {container} vers {art_def_loc} {location}.",
        "{subject} a mis {art_def_cont} {container} sur {art_def_loc} {location}.",
        "{subject} a porté {art_def_cont} {container} jusqu'au {location}.",
    ],
    "de": [
        "{subject} stellte dann {art_def_cont_acc} {container} auf {art_def_loc_acc} {location}.",
        "{subject} bewegte {art_def_cont_acc} {container} zum {location}.",
        "{subject} legte {art_def_cont_acc} {container} auf {art_def_loc_acc} {location}.",
        "{subject} trug {art_def_cont_acc} {container} zum {location}.",
    ],
    "zh": [
        "{subject}然后把{container}放到了{location}上。",
        "{subject}把{container}移到了{location}。",
        "{subject}把{container}放在了{location}上。",
        "{subject}把{container}拿到了{location}旁。",
    ],
    "ua": {
        "m": [
            "{subject} потім поставив {container_acc} на {location_loc}.",
            "{subject} перемістив {container_acc} до {location_loc}.",
            "{subject} поклав {container_acc} на {location_loc}.",
            "{subject} переніс {container_acc} до {location_loc}.",
        ],
        "f": [
            "{subject} потім поставила {container_acc} на {location_loc}.",
            "{subject} перемістила {container_acc} до {location_loc}.",
            "{subject} поклала {container_acc} на {location_loc}.",
            "{subject} перенесла {container_acc} до {location_loc}.",
        ],
    },
}

QUESTION = {
    "en": ["Where is the {object}?", "Where is the {object} now?"],
    "es": [
        "¿Dónde está {art_def_obj} {object}?",
        "¿Dónde está {art_def_obj} {object} ahora?",
    ],
    "fr": [
        "Où est {art_def_obj} {object} ?",
        "Où se trouve {art_def_obj} {object} maintenant ?",
    ],
    "de": [
        "Wo ist {art_def_obj_nom} {object}?",
        "Wo befindet sich {art_def_obj_nom} {object} jetzt?",
    ],
    "zh": ["{object}在哪里？", "{object}现在在哪里？"],
    "ua": [
        "Де зараз {object_nom}?",
        "Де знаходиться {object_nom}?",
    ],
}

INTERACT = {
    "en": [
        "{subject} then start the {appliance}.",
        "{subject} close the {appliance} door.",
        "{subject} turn on the {appliance}.",
    ],
    "es": [
        "{subject} luego encendió {art_def_appl} {appliance}.",
        "{subject} cerró la puerta {art_def_appl_de} {appliance}.",
        "{subject} encendió {art_def_appl} {appliance}.",
    ],
    "fr": [
        "{subject} a ensuite démarré {art_def_appl} {appliance}.",
        "{subject} a fermé la porte {art_def_appl_de} {appliance}.",
        "{subject} a allumé {art_def_appl} {appliance}.",
    ],
    "de": [
        "{subject} startete dann {art_def_appl_acc} {appliance}.",
        "{subject} schloss die Tür {art_def_appl_gen} {appliance}.",
        "{subject} schaltete {art_def_appl_acc} {appliance} ein.",
    ],
    "zh": [
        "{subject}然后启动了{appliance}。",
        "{subject}关上了{appliance}的门。",
        "{subject}打开了{appliance}。",
    ],
    "ua": {
        "m": [
            "{subject} потім увімкнув {appliance_acc}.",
            "{subject} закрив дверцята {appliance_acc}.",
            "{subject} увімкнув {appliance_acc}.",
        ],
        "f": [
            "{subject} потім увімкнула {appliance_acc}.",
            "{subject} закрила дверцята {appliance_acc}.",
            "{subject} увімкнула {appliance_acc}.",
        ],
    },
}

# ── Distractor templates ─────────────────────────────────────────────────

DISTRACTOR_IRRELEVANT = {
    "en": [
        "{subject} look at {possessive} phone.",
        "{subject} take a deep breath.",
        "{subject} check the time.",
        "{subject} yawn briefly.",
        "{subject} hum a little tune.",
    ],
    "es": [
        "{subject} miró su teléfono.",
        "{subject} respiró hondo.",
        "{subject} miró la hora.",
        "{subject} bostezó brevemente.",
        "{subject} tarareó una melodía.",
    ],
    "fr": [
        "{subject} a regardé son téléphone.",
        "{subject} a pris une grande respiration.",
        "{subject} a vérifié l'heure.",
        "{subject} a bâillé brièvement.",
        "{subject} a fredonné un air.",
    ],
    "de": [
        "{subject} schaute auf das Handy.",
        "{subject} holte tief Luft.",
        "{subject} schaute auf die Uhr.",
        "{subject} gähnte kurz.",
        "{subject} summte eine kleine Melodie.",
    ],
    "zh": [
        "{subject}看了一下手机。",
        "{subject}深呼吸了一下。",
        "{subject}看了一下时间。",
        "{subject}打了个哈欠。",
        "{subject}哼了一首小曲。",
    ],
    "ua": {
        "m": [
            "{subject} подивився на телефон.",
            "{subject} глибоко вдихнув.",
            "{subject} перевірив час.",
            "{subject} позіхнув.",
            "{subject} наспівував мелодію.",
        ],
        "f": [
            "{subject} подивилася на телефон.",
            "{subject} глибоко вдихнула.",
            "{subject} перевірила час.",
            "{subject} позіхнула.",
            "{subject} наспівувала мелодію.",
        ],
    },
}

DISTRACTOR_SPATIAL = {
    "en": [
        "{subject} walk to the {room}.",
        "{subject} look at the {nearby_object}.",
        "{subject} glance at the window.",
        "{subject} turn around.",
    ],
    "es": [
        "{subject} caminó hacia {art_def_room} {room}.",
        "{subject} miró {art_def_nearby} {nearby_object}.",
        "{subject} echó un vistazo a la ventana.",
        "{subject} se dio la vuelta.",
    ],
    "fr": {
        "m": [
            "{subject} est allé dans {art_def_room} {room}.",
            "{subject} a regardé {art_def_nearby} {nearby_object}.",
            "{subject} a jeté un coup d'œil à la fenêtre.",
            "{subject} s'est retourné.",
        ],
        "f": [
            "{subject} est allée dans {art_def_room} {room}.",
            "{subject} a regardé {art_def_nearby} {nearby_object}.",
            "{subject} a jeté un coup d'œil à la fenêtre.",
            "{subject} s'est retournée.",
        ],
    },
    "de": [
        "{subject} ging {art_def_room_zu} {room}.",
        "{subject} schaute auf {art_def_nearby_acc} {nearby_object}.",
        "{subject} warf einen Blick auf das Fenster.",
        "{subject} drehte sich um.",
    ],
    "zh": [
        "{subject}走向了{room}。",
        "{subject}看了一眼{nearby_object}。",
        "{subject}瞥了一眼窗户。",
        "{subject}转过身来。",
    ],
    "ua": {
        "m": [
            "{subject} пішов до {room_gen}.",
            "{subject} подивився на {nearby_object_acc}.",
            "{subject} глянув у вікно.",
            "{subject} обернувся.",
        ],
        "f": [
            "{subject} пішла до {room_gen}.",
            "{subject} подивилася на {nearby_object_acc}.",
            "{subject} глянула у вікно.",
            "{subject} обернулася.",
        ],
    },
}

DISTRACTOR_TEMPORAL = {
    "en": [
        "{subject} wait for {time} seconds.",
        "{subject} pause for a moment.",
        "{subject} count to {number}.",
    ],
    "es": [
        "{subject} esperó {time} segundos.",
        "{subject} hizo una pausa.",
        "{subject} contó hasta {number}.",
    ],
    "fr": [
        "{subject} a attendu {time} secondes.",
        "{subject} a fait une pause.",
        "{subject} a compté jusqu'à {number}.",
    ],
    "de": [
        "{subject} wartete {time} Sekunden.",
        "{subject} machte eine kurze Pause.",
        "{subject} zählte bis {number}.",
    ],
    "zh": [
        "{subject}等了{time}秒。",
        "{subject}停顿了一下。",
        "{subject}数到了{number}。",
    ],
    "ua": {
        "m": [
            "{subject} зачекав {time} секунд.",
            "{subject} зробив паузу.",
            "{subject} порахував до {number}.",
        ],
        "f": [
            "{subject} зачекала {time} секунд.",
            "{subject} зробила паузу.",
            "{subject} порахувала до {number}.",
        ],
    },
}

# ── Subject pronoun and possessive per language ──────────────────────────

SUBJECT_FORMS = {
    "en": {"I": ("I", "my"), "You": ("You", "your")},
    "es": {"I": ("Yo", "mi"), "You": ("Tú", "tu")},
    "fr": {"I": ("Je", "mon"), "You": ("Vous", "votre")},
    "de": {"I": ("Ich", "mein"), "You": ("Sie", "Ihr")},
    "zh": {"I": ("我", "我的"), "You": ("你", "你的")},
    "ua": {"I": ("Я", "мій"), "You": ("Ви", "ваш")},
}


# ── Helper functions ─────────────────────────────────────────────────────

def localize_vocab(en_word: str, vocab_dict: dict, language: str,
                   case: str = "nom") -> str:
    """Translate an English vocabulary word to the target language.

    Delegates to ``grammar_utils.resolve_vocab`` for case-aware lookups.
    """
    return resolve_vocab(en_word, vocab_dict, language, case)


def get_templates(template_dict: dict, language: str,
                  gender: str = "m") -> list:
    """Get templates for a language with English fallback.

    Delegates to ``grammar_utils.pick_templates`` for gender sub-dicts.
    """
    return pick_templates(template_dict, language, gender)


def get_subject_forms(subject: str, language: str) -> tuple:
    """Return (formatted_subject, possessive) for a given subject and language."""
    forms = SUBJECT_FORMS.get(language, SUBJECT_FORMS["en"])
    if subject in forms:
        return forms[subject]
    # Named subject -- use as-is, possessive is just the name
    return (subject, subject)
