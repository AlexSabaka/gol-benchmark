"""Multilingual translations for Family Relations puzzle generation."""

from __future__ import annotations

import random
from typing import Dict, List

from src.plugins.grammar_utils import article as _get_article

# ---------------------------------------------------------------------------
# Relationship labels (singular forms)
# ---------------------------------------------------------------------------

RELATIONSHIP_LABELS: Dict[str, Dict[str, str]] = {
    "en": {
        "father": "father", "mother": "mother", "brother": "brother", "sister": "sister",
        "son": "son", "daughter": "daughter", "grandfather": "grandfather", "grandmother": "grandmother",
        "uncle": "uncle", "aunt": "aunt", "cousin": "cousin", "child": "child",
        "grandchild": "grandchild", "great-grandchild": "great-grandchild",
        "sibling": "sibling",
    },
    "es": {
        "father": "padre", "mother": "madre", "brother": "hermano", "sister": "hermana",
        "son": "hijo", "daughter": "hija", "grandfather": "abuelo", "grandmother": "abuela",
        "uncle": "tío", "aunt": "tía", "cousin": "primo", "child": "hijo",
        "grandchild": "nieto", "great-grandchild": "bisnieto",
        "sibling": "hermano",
    },
    "fr": {
        "father": "père", "mother": "mère", "brother": "frère", "sister": "soeur",
        "son": "fils", "daughter": "fille", "grandfather": "grand-père", "grandmother": "grand-mère",
        "uncle": "oncle", "aunt": "tante", "cousin": "cousin", "child": "enfant",
        "grandchild": "petit-enfant", "great-grandchild": "arrière-petit-enfant",
        "sibling": "frère ou soeur",
    },
    "de": {
        "father": "Vater", "mother": "Mutter", "brother": "Bruder", "sister": "Schwester",
        "son": "Sohn", "daughter": "Tochter", "grandfather": "Großvater", "grandmother": "Großmutter",
        "uncle": "Onkel", "aunt": "Tante", "cousin": "Cousin", "child": "Kind",
        "grandchild": "Enkel", "great-grandchild": "Urenkel",
        "sibling": "Geschwister",
    },
    "zh": {
        "father": "父亲", "mother": "母亲", "brother": "兄弟", "sister": "姐妹",
        "son": "儿子", "daughter": "女儿", "grandfather": "祖父", "grandmother": "祖母",
        "uncle": "叔叔", "aunt": "阿姨", "cousin": "表兄弟", "child": "孩子",
        "grandchild": "孙子", "great-grandchild": "曾孙",
        "sibling": "兄弟姐妹",
    },
    "ua": {
        "father": "батько", "mother": "мати", "brother": "брат", "sister": "сестра",
        "son": "син", "daughter": "дочка", "grandfather": "дідусь", "grandmother": "бабуся",
        "uncle": "дядько", "aunt": "тітка", "cousin": "двоюрідний брат", "child": "дитина",
        "grandchild": "онук", "great-grandchild": "правнук",
        "sibling": "брат чи сестра",
    },
}

# ---------------------------------------------------------------------------
# Plural forms
# ---------------------------------------------------------------------------

PLURAL_FORMS: Dict[str, Dict[str, str]] = {
    "en": {
        "brother": "brothers", "sister": "sisters", "son": "sons", "daughter": "daughters",
        "child": "children", "grandchild": "grandchildren", "cousin": "cousins",
        "great-grandchild": "great-grandchildren", "sibling": "siblings",
    },
    "es": {
        "brother": "hermanos", "sister": "hermanas", "son": "hijos", "daughter": "hijas",
        "child": "hijos", "grandchild": "nietos", "cousin": "primos",
        "great-grandchild": "bisnietos", "sibling": "hermanos",
    },
    "fr": {
        "brother": "frères", "sister": "soeurs", "son": "fils", "daughter": "filles",
        "child": "enfants", "grandchild": "petits-enfants", "cousin": "cousins",
        "great-grandchild": "arrière-petits-enfants", "sibling": "frères et soeurs",
    },
    "de": {
        "brother": "Brüder", "sister": "Schwestern", "son": "Söhne", "daughter": "Töchter",
        "child": "Kinder", "grandchild": "Enkel", "cousin": "Cousins",
        "great-grandchild": "Urenkel", "sibling": "Geschwister",
    },
    "zh": {
        "brother": "兄弟", "sister": "姐妹", "son": "儿子", "daughter": "女儿",
        "child": "孩子", "grandchild": "孙子", "cousin": "表兄弟",
        "great-grandchild": "曾孙", "sibling": "兄弟姐妹",
    },
    "ua": {
        "brother": "братів", "sister": "сестер", "son": "синів", "daughter": "дочок",
        "child": "дітей", "grandchild": "онуків", "cousin": "двоюрідних братів",
        "great-grandchild": "правнуків", "sibling": "братів і сестер",
    },
}

# ---------------------------------------------------------------------------
# Culturally appropriate name pools
# ---------------------------------------------------------------------------

NAMES: Dict[str, Dict[str, List[str]]] = {
    "en": {
        "m": ["James", "David", "Carlos", "Ahmed", "Ben", "Tom", "Oscar", "Leo",
              "Max", "Oliver", "Ethan", "Henry", "George", "Frank", "Ivan", "Raj"],
        "f": ["Sally", "Maria", "Emma", "Aisha", "Beth", "Clara", "Diana", "Fiona",
              "Grace", "Hannah", "Iris", "Julia", "Lily", "Nora", "Rosa", "Zoe"],
    },
    "es": {
        "m": ["Carlos", "Miguel", "Andrés", "Pablo", "Luis", "Diego", "Javier", "Rafael",
              "Sergio", "Fernando", "Alejandro", "Roberto", "Manuel", "Pedro", "Tomás", "Hugo"],
        "f": ["María", "Lucía", "Carmen", "Ana", "Isabel", "Elena", "Sofía", "Marta",
              "Laura", "Rosa", "Valentina", "Paula", "Natalia", "Raquel", "Andrea", "Clara"],
    },
    "fr": {
        "m": ["Pierre", "Jean", "Louis", "Marc", "Antoine", "Nicolas", "François", "Julien",
              "Thomas", "Philippe", "Luc", "Henri", "Paul", "Étienne", "Mathieu", "Benoît"],
        "f": ["Marie", "Claire", "Sophie", "Camille", "Isabelle", "Nathalie", "Élise", "Julie",
              "Céline", "Émilie", "Charlotte", "Margaux", "Léa", "Aurélie", "Diane", "Lucie"],
    },
    "de": {
        "m": ["Hans", "Klaus", "Stefan", "Wolfgang", "Thomas", "Michael", "Andreas", "Peter",
              "Markus", "Jürgen", "Friedrich", "Karl", "Lukas", "Felix", "Moritz", "Tobias"],
        "f": ["Anna", "Maria", "Katharina", "Petra", "Monika", "Heike", "Sabine", "Claudia",
              "Johanna", "Ingrid", "Lena", "Sophie", "Emma", "Frieda", "Greta", "Hilde"],
    },
    "zh": {
        "m": ["小明", "小刚", "小伟", "小杰", "志强", "建国", "大伟", "文博",
              "天明", "浩然", "子轩", "宇航", "一鸣", "嘉豪", "俊杰", "思远"],
        "f": ["小红", "小丽", "小芳", "小雪", "美玲", "淑芬", "玉兰", "丽华",
              "晓琳", "雨萱", "诗涵", "欣怡", "梦琪", "佳慧", "思颖", "雅婷"],
    },
    "ua": {
        "m": ["Олексій", "Богдан", "Дмитро", "Іван", "Микола", "Петро", "Тарас", "Андрій",
              "Василь", "Юрій", "Сергій", "Олег", "Максим", "Ярослав", "Віталій", "Роман"],
        "f": ["Оксана", "Марія", "Олена", "Тетяна", "Наталія", "Ірина", "Людмила", "Анна",
              "Катерина", "Юлія", "Софія", "Дарина", "Вікторія", "Галина", "Зоряна", "Леся"],
    },
}

# ---------------------------------------------------------------------------
# Pronoun tables (used for possessives, subjects, objects)
# ---------------------------------------------------------------------------

PRONOUNS: Dict[str, Dict[str, Dict[str, str]]] = {
    "en": {
        "m": {"subject": "he", "object": "him", "possessive": "his"},
        "f": {"subject": "she", "object": "her", "possessive": "her"},
    },
    "es": {
        "m": {"subject": "él", "object": "él", "possessive": "su"},
        "f": {"subject": "ella", "object": "ella", "possessive": "su"},
    },
    "fr": {
        "m": {"subject": "il", "object": "lui", "possessive": "ses"},
        "f": {"subject": "elle", "object": "elle", "possessive": "ses"},
    },
    "de": {
        "m": {"subject": "er", "object": "ihm", "possessive": "seinen"},
        "f": {"subject": "sie", "object": "ihr", "possessive": "ihren"},
    },
    "zh": {
        "m": {"subject": "他", "object": "他", "possessive": "他的"},
        "f": {"subject": "她", "object": "她", "possessive": "她的"},
    },
    "ua": {
        "m": {"subject": "він", "object": "його", "possessive": "його"},
        "f": {"subject": "вона", "object": "її", "possessive": "її"},
    },
}

# ---------------------------------------------------------------------------
# Parent / child / sibling labels by gender
# ---------------------------------------------------------------------------

PARENT_LABEL: Dict[str, Dict[str, str]] = {
    "en": {"m": "father", "f": "mother"},
    "es": {"m": "padre", "f": "madre"},
    "fr": {"m": "père", "f": "mère"},
    "de": {"m": "Vater", "f": "Mutter"},
    "zh": {"m": "父亲", "f": "母亲"},
    "ua": {"m": "батько", "f": "мати"},
}

CHILD_LABEL: Dict[str, Dict[str, str]] = {
    "en": {"m": "son", "f": "daughter"},
    "es": {"m": "hijo", "f": "hija"},
    "fr": {"m": "fils", "f": "fille"},
    "de": {"m": "Sohn", "f": "Tochter"},
    "zh": {"m": "儿子", "f": "女儿"},
    "ua": {"m": "син", "f": "дочка"},
}

SIBLING_LABEL: Dict[str, Dict[str, str]] = {
    "en": {"m": "brother", "f": "sister"},
    "es": {"m": "hermano", "f": "hermana"},
    "fr": {"m": "frère", "f": "soeur"},
    "de": {"m": "Bruder", "f": "Schwester"},
    "zh": {"m": "兄弟", "f": "姐妹"},
    "ua": {"m": "брат", "f": "сестра"},
}

GRANDPARENT_LABEL: Dict[str, Dict[str, str]] = {
    "en": {"m": "grandfather", "f": "grandmother"},
    "es": {"m": "abuelo", "f": "abuela"},
    "fr": {"m": "grand-père", "f": "grand-mère"},
    "de": {"m": "Großvater", "f": "Großmutter"},
    "zh": {"m": "祖父", "f": "祖母"},
    "ua": {"m": "дідусь", "f": "бабуся"},
}

AUNT_UNCLE_LABEL: Dict[str, Dict[str, str]] = {
    "en": {"m": "uncle", "f": "aunt"},
    "es": {"m": "tío", "f": "tía"},
    "fr": {"m": "oncle", "f": "tante"},
    "de": {"m": "Onkel", "f": "Tante"},
    "zh": {"m": "叔叔", "f": "阿姨"},
    "ua": {"m": "дядько", "f": "тітка"},
}

# ---------------------------------------------------------------------------
# Question templates
# ---------------------------------------------------------------------------

QUESTION_TEMPLATES: Dict[str, Dict[str, str]] = {
    "en": {
        "how_many_sisters": "How many sisters does {name} have?",
        "how_many_brothers": "How many brothers does {name} have?",
        "total_children_parents": "How many children do {name}'s parents have in total?",
        "how_many_children_parent": "How many children does the {parent} have?",
        "how_many_children_named": "How many children does {name} have in total?",
        "how_many_grandchildren": "How many grandchildren does the {grandparent} have?",
        "how_many_great_grandchildren": "How many great-grandchildren does the {grandparent} have?",
        "how_many_cousins": "How many cousins does {name} have?",
        "how_many_family": "How many children are there in this family?",
        "how_many_children_named_parent": "How many children does {name} have?",
    },
    "es": {
        "how_many_sisters": "¿Cuántas hermanas tiene {name}?",
        "how_many_brothers": "¿Cuántos hermanos tiene {name}?",
        "total_children_parents": "¿Cuántos hijos tienen los padres de {name} en total?",
        "how_many_children_parent": "¿Cuántos hijos tiene {parent}?",
        "how_many_children_named": "¿Cuántos hijos tiene {name} en total?",
        "how_many_grandchildren": "¿Cuántos nietos tiene {grandparent}?",
        "how_many_great_grandchildren": "¿Cuántos bisnietos tiene {grandparent}?",
        "how_many_cousins": "¿Cuántos primos tiene {name}?",
        "how_many_family": "¿Cuántos hijos hay en esta familia?",
        "how_many_children_named_parent": "¿Cuántos hijos tiene {name}?",
    },
    "fr": {
        "how_many_sisters": "Combien de soeurs a {name} ?",
        "how_many_brothers": "Combien de frères a {name} ?",
        "total_children_parents": "Combien d'enfants les parents de {name} ont-ils au total ?",
        "how_many_children_parent": "Combien d'enfants {parent} a-t-{pronoun} ?",
        "how_many_children_named": "Combien d'enfants {name} a-t-{pronoun} au total ?",
        "how_many_grandchildren": "Combien de petits-enfants {grandparent} a-t-{pronoun} ?",
        "how_many_great_grandchildren": "Combien d'arrière-petits-enfants {grandparent} a-t-{pronoun} ?",
        "how_many_cousins": "Combien de cousins a {name} ?",
        "how_many_family": "Combien d'enfants y a-t-il dans cette famille ?",
        "how_many_children_named_parent": "Combien d'enfants a {name} ?",
    },
    "de": {
        "how_many_sisters": "Wie viele Schwestern hat {name}?",
        "how_many_brothers": "Wie viele Brüder hat {name}?",
        "total_children_parents": "Wie viele Kinder haben {name}s Eltern insgesamt?",
        "how_many_children_parent": "Wie viele Kinder hat {parent}?",
        "how_many_children_named": "Wie viele Kinder hat {name} insgesamt?",
        "how_many_grandchildren": "Wie viele Enkel hat {grandparent}?",
        "how_many_great_grandchildren": "Wie viele Urenkel hat {grandparent}?",
        "how_many_cousins": "Wie viele Cousins hat {name}?",
        "how_many_family": "Wie viele Kinder gibt es in dieser Familie?",
        "how_many_children_named_parent": "Wie viele Kinder hat {name}?",
    },
    "zh": {
        "how_many_sisters": "{name}有几个姐妹？",
        "how_many_brothers": "{name}有几个兄弟？",
        "total_children_parents": "{name}的父母一共有几个孩子？",
        "how_many_children_parent": "这位{parent}有几个孩子？",
        "how_many_children_named": "{name}一共有几个孩子？",
        "how_many_grandchildren": "这位{grandparent}有几个孙子？",
        "how_many_great_grandchildren": "这位{grandparent}有几个曾孙？",
        "how_many_cousins": "{name}有几个表兄弟？",
        "how_many_family": "这个家庭有几个孩子？",
        "how_many_children_named_parent": "{name}有几个孩子？",
    },
    "ua": {
        "how_many_sisters": "Скільки сестер має {name}?",
        "how_many_brothers": "Скільки братів має {name}?",
        "total_children_parents": "Скільки всього дітей мають батьки {name}?",
        "how_many_children_parent": "Скільки дітей має {parent}?",
        "how_many_children_named": "Скільки всього дітей має {name}?",
        "how_many_grandchildren": "Скільки онуків має {grandparent}?",
        "how_many_great_grandchildren": "Скільки правнуків має {grandparent}?",
        "how_many_cousins": "Скільки двоюрідних братів і сестер має {name}?",
        "how_many_family": "Скільки дітей у цій родині?",
        "how_many_children_named_parent": "Скільки дітей має {name}?",
    },
}

# ---------------------------------------------------------------------------
# Narrative sentence templates
# ---------------------------------------------------------------------------

NARRATIVE_TEMPLATES: Dict[str, Dict[str, str]] = {
    "en": {
        "has_n_rel": "{name} has {n} {relation}.",
        "has_n_and_m": "{name} has {n} {rel_a} and {m} {rel_b}.",
        "each_has_n": "Each {rel_type} has {n} {relation}.",
        "each_has_exactly_n": "Each of {possessive} {rel_type} has exactly {n} {relation}.",
        "is_parent_with_n": "{name} is a {parent_label} with {n} {relation}.",
        "is_only_child": "{name} is an only child.",
        "has_n_children": "{gp_label} has {n} {relation}.",
        "each_child_has_n": "Each of {possessive} {rel_type} has {n} {relation}.",
        "each_grandchild_has_n": "Each grandchild has {n} {relation} of their own.",
        "sibling_text": "{name} has {n} {relation}. ",
        "parent_has_one_sibling": "{possessive} {parent_label} has exactly one sibling — an {aunt_uncle} — who has {n} {relation}.",
        "says_equal": "{name} says: \"I have as many {rel_a} as {rel_b}.\"",
        "says_multiplier": "{name}, {narrator}'s {sibling_label}, says: \"I have {multiplier} as many {rel_a} as {rel_b}.\"",
        "says_one_more_m": "{name} says: \"I have one more brother than I have sisters.\"",
        "says_one_more_f": "{name}, {sibling_name}'s brother, says: \"I have one more sister than I have brothers.\"",
        "parent_says_sons": "{name} says:\n\"Each of my sons has as many brothers as sisters. Each of my daughters has {multiplier} as many brothers as sisters.\"",
    },
    "es": {
        "has_n_rel": "{name} tiene {n} {relation}.",
        "has_n_and_m": "{name} tiene {n} {rel_a} y {m} {rel_b}.",
        "each_has_n": "Cada {rel_type} tiene {n} {relation}.",
        "each_has_exactly_n": "Cada una de {possessive} {rel_type} tiene exactamente {n} {relation}.",
        "is_parent_with_n": "{name} es {parent_label} con {n} {relation}.",
        "is_only_child_m": "{name} es hijo único.",
        "is_only_child_f": "{name} es hija única.",
        "has_n_children": "{gp_label} tiene {n} {relation}.",
        "each_child_has_n": "Cada uno de {possessive} {rel_type} tiene {n} {relation}.",
        "each_grandchild_has_n": "Cada nieto tiene {n} {relation} propios.",
        "sibling_text": "{name} tiene {n} {relation}. ",
        "parent_has_one_sibling": "{parent_label_art} de {name_ref} tiene exactamente un hermano — {aunt_uncle} — que tiene {n} {relation}.",
        "says_equal": "{name} dice: \"Tengo tantos {rel_a} como {rel_b}.\"",
        "says_multiplier": "{name}, la hermana de {narrator}, dice: \"Tengo {multiplier} {rel_a} que {rel_b}.\"",
        "says_one_more_m": "{name} dice: \"Tengo un hermano más que hermanas.\"",
        "says_one_more_f": "{name}, el hermano de {sibling_name}, dice: \"Tengo una hermana más que hermanos.\"",
        "parent_says_sons": "{name} dice:\n\"Cada uno de mis hijos tiene tantos hermanos como hermanas. Cada una de mis hijas tiene {multiplier} hermanos que hermanas.\"",
    },
    "fr": {
        "has_n_rel": "{name} a {n} {relation}.",
        "has_n_and_m": "{name} a {n} {rel_a} et {m} {rel_b}.",
        "each_has_n": "Chaque {rel_type} a {n} {relation}.",
        "each_has_exactly_n": "Chacune de {possessive} {rel_type} a exactement {n} {relation}.",
        "is_parent_with_n": "{name} est {parent_label} avec {n} {relation}.",
        "is_only_child": "{name} est enfant unique.",
        "has_n_children": "{gp_label} a {n} {relation}.",
        "each_child_has_n": "Chacun de {possessive} {rel_type} a {n} {relation}.",
        "each_grandchild_has_n": "Chaque petit-enfant a {n} {relation} à son tour.",
        "sibling_text": "{name} a {n} {relation}. ",
        "parent_has_one_sibling": "{parent_label_art} de {name_ref} a exactement un frère ou une soeur — {aunt_uncle} — qui a {n} {relation}.",
        "says_equal": "{name} dit : \"J'ai autant de {rel_a} que de {rel_b}.\"",
        "says_multiplier": "{name}, la soeur de {narrator}, dit : \"J'ai {multiplier} plus de {rel_a} que de {rel_b}.\"",
        "says_one_more_m": "{name} dit : \"J'ai un frère de plus que de soeurs.\"",
        "says_one_more_f": "{name}, le frère de {sibling_name}, dit : \"J'ai une soeur de plus que de frères.\"",
        "parent_says_sons": "{name} dit :\n\"Chacun de mes fils a autant de frères que de soeurs. Chacune de mes filles a {multiplier} plus de frères que de soeurs.\"",
    },
    "de": {
        "has_n_rel": "{name} hat {n} {relation}.",
        "has_n_and_m": "{name} hat {n} {rel_a} und {m} {rel_b}.",
        "each_has_n": "Jeder {rel_type} hat {n} {relation}.",
        "each_has_exactly_n": "Jede von {possessive} {rel_type} hat genau {n} {relation}.",
        "is_parent_with_n": "{name} ist {parent_label} mit {n} {relation}.",
        "is_only_child": "{name} ist ein Einzelkind.",
        "has_n_children": "{gp_label} hat {n} {relation}.",
        "each_child_has_n": "Jedes von {possessive} {rel_type} hat {n} {relation}.",
        "each_grandchild_has_n": "Jeder Enkel hat {n} eigene {relation}.",
        "sibling_text": "{name} hat {n} {relation}. ",
        "parent_has_one_sibling": "{possessive_cap} {parent_label} hat genau ein Geschwister — {aunt_uncle} — {rel_pronoun} {n} {relation} hat.",
        "says_equal": "{name} sagt: \"Ich habe genauso viele {rel_a} wie {rel_b}.\"",
        "says_multiplier": "{name}, {narrator}s Schwester, sagt: \"Ich habe {multiplier} so viele {rel_a} wie {rel_b}.\"",
        "says_one_more_m": "{name} sagt: \"Ich habe einen Bruder mehr als Schwestern.\"",
        "says_one_more_f": "{name}, {sibling_name}s Bruder, sagt: \"Ich habe eine Schwester mehr als Brüder.\"",
        "parent_says_sons": "{name} sagt:\n\"Jeder meiner Söhne hat genauso viele Brüder wie Schwestern. Jede meiner Töchter hat {multiplier} so viele Brüder wie Schwestern.\"",
    },
    "zh": {
        "has_n_rel": "{name}\u6709{n}\u4e2a{relation}\u3002",
        "has_n_and_m": "{name}\u6709{n}\u4e2a{rel_a}\u548c{m}\u4e2a{rel_b}\u3002",
        "each_has_n": "\u6bcf\u4e2a{rel_type}\u6709{n}\u4e2a{relation}\u3002",
        "each_has_exactly_n": "{possessive}\u6bcf\u4e2a{rel_type}\u6070\u597d\u6709{n}\u4e2a{relation}\u3002",
        "is_parent_with_n": "{name}\u662f\u4e00\u4f4d{parent_label}\uff0c\u6709{n}\u4e2a{relation}\u3002",
        "is_only_child": "{name}\u662f\u72ec\u751f\u5b50\u5973\u3002",
        "has_n_children": "\u4e00\u4f4d{gp_label}\u6709{n}\u4e2a{relation}\u3002",
        "each_child_has_n": "{possessive}\u6bcf\u4e2a{rel_type}\u6709{n}\u4e2a{relation}\u3002",
        "each_grandchild_has_n": "\u6bcf\u4e2a\u5b59\u5b50\u6709{n}\u4e2a\u81ea\u5df1\u7684{relation}\u3002",
        "sibling_text": "{name}\u6709{n}\u4e2a{relation}\u3002",
        "parent_has_one_sibling": "{name}\u7684{parent_label}\u6709\u4e14\u53ea\u6709\u4e00\u4e2a\u5144\u5f1f\u59d0\u59b9\u2014\u2014\u4e00\u4e2a{aunt_uncle}\u2014\u2014\u6709{n}\u4e2a{relation}\u3002",
        "says_equal": '{name}\u8bf4\uff1a\u201c\u6211\u7684{rel_a}\u548c{rel_b}\u4e00\u6837\u591a\u3002\u201d',
        "says_multiplier": '{name}\uff0c{narrator}\u7684\u59d0\u59b9\uff0c\u8bf4\uff1a\u201c\u6211\u7684{rel_a}\u662f{rel_b}\u7684{multiplier}\u3002\u201d',
        "says_one_more_m": '{name}\u8bf4\uff1a\u201c\u6211\u7684\u5144\u5f1f\u6bd4\u59d0\u59b9\u591a\u4e00\u4e2a\u3002\u201d',
        "says_one_more_f": '{name}\uff0c{sibling_name}\u7684\u5144\u5f1f\uff0c\u8bf4\uff1a\u201c\u6211\u7684\u59d0\u59b9\u6bd4\u5144\u5f1f\u591a\u4e00\u4e2a\u3002\u201d',
        "parent_says_sons": '{name}\u8bf4\uff1a\n\u201c\u6211\u7684\u6bcf\u4e2a\u513f\u5b50\u7684\u5144\u5f1f\u548c\u59d0\u59b9\u4e00\u6837\u591a\u3002\u6211\u7684\u6bcf\u4e2a\u5973\u513f\u7684\u5144\u5f1f\u662f\u59d0\u59b9\u7684{multiplier}\u3002\u201d',
    },
    "ua": {
        "has_n_rel": "{name} має {n} {relation}.",
        "has_n_and_m": "{name} має {n} {rel_a} і {m} {rel_b}.",
        "each_has_n": "Кожен {rel_type} має {n} {relation}.",
        "each_has_exactly_n": "Кожна з {possessive} {rel_type} має рівно {n} {relation}.",
        "is_parent_with_n": "{name} — {parent_label}, у якого {n} {relation}.",
        "is_only_child": "{name} — єдина дитина.",
        "has_n_children": "{gp_label} має {n} {relation}.",
        "each_child_has_n": "Кожен з {possessive} {rel_type} має {n} {relation}.",
        "each_grandchild_has_n": "Кожен онук має {n} власних {relation}.",
        "sibling_text": "{name} має {n} {relation}. ",
        "parent_has_one_sibling": "{parent_label} {name_ref} має рівно одного брата чи сестру — {aunt_uncle} — у якого {n} {relation}.",
        "says_equal": "{name} каже: \"У мене стільки ж {rel_a}, скільки {rel_b}.\"",
        "says_multiplier": "{name}, сестра {narrator}, каже: \"У мене {multiplier} більше {rel_a}, ніж {rel_b}.\"",
        "says_one_more_m": "{name} каже: \"У мене на одного брата більше, ніж сестер.\"",
        "says_one_more_f": "{name}, брат {sibling_name}, каже: \"У мене на одну сестру більше, ніж братів.\"",
        "parent_says_sons": "{name} каже:\n\"Кожен з моїх синів має стільки ж братів, скільки сестер. Кожна з моїх дочок має {multiplier} більше братів, ніж сестер.\"",
    },
}

# ---------------------------------------------------------------------------
# Multiplier words (for "twice", "three times")
# ---------------------------------------------------------------------------

MULTIPLIER_WORDS: Dict[str, Dict[int, str]] = {
    "en": {2: "twice", 3: "three times"},
    "es": {2: "el doble de", 3: "el triple de"},
    "fr": {2: "deux fois", 3: "trois fois"},
    "de": {2: "doppelt", 3: "dreimal"},
    "zh": {2: "两倍", 3: "三倍"},
    "ua": {2: "вдвічі", 3: "втричі"},
}

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def rel(en_word: str, language: str, n: int = 1) -> str:
    """Get localized relationship label, with plural if n != 1.

    For Chinese (zh), singular and plural forms are identical so no
    pluralisation logic is needed.
    """
    labels = RELATIONSHIP_LABELS.get(language, RELATIONSHIP_LABELS["en"])
    word = labels.get(en_word, en_word)
    if n != 1:
        plurals = PLURAL_FORMS.get(language, PLURAL_FORMS["en"])
        word = plurals.get(en_word, word + "s")
    return word


def get_name(gender: str, rng: random.Random, language: str = "en") -> str:
    """Get a random name for the given gender and language."""
    lang_names = NAMES.get(language, NAMES["en"])
    pool = lang_names.get(gender, lang_names["m"])
    return rng.choice(pool)


def get_unique_names(genders: List[str], rng: random.Random, language: str = "en") -> List[str]:
    """Return len(genders) unique names matching requested genders."""
    seen: set = set()
    result: list = []
    for g in genders:
        for _ in range(40):
            n = get_name(g, rng, language)
            if n not in seen:
                seen.add(n)
                result.append(n)
                break
        else:
            fallback = f"Person{len(result)+1}"
            result.append(fallback)
    return result


def pron(gender: str, form: str, language: str = "en") -> str:
    """Get a pronoun.  *form* is 'subject', 'object', or 'possessive'."""
    lang_pronouns = PRONOUNS.get(language, PRONOUNS["en"])
    return lang_pronouns.get(gender, lang_pronouns["m"]).get(form, "")


def parent_label(gender: str, language: str = "en") -> str:
    """Get localized parent label (father/mother) for the given gender."""
    return PARENT_LABEL.get(language, PARENT_LABEL["en"]).get(gender, "parent")


def grandparent_label(gender: str, language: str = "en") -> str:
    """Get localized grandparent label."""
    return GRANDPARENT_LABEL.get(language, GRANDPARENT_LABEL["en"]).get(gender, "grandparent")


def aunt_uncle_label(gender: str, language: str = "en") -> str:
    """Get localized aunt/uncle label."""
    return AUNT_UNCLE_LABEL.get(language, AUNT_UNCLE_LABEL["en"]).get(gender, "uncle")


def multiplier_word(k: int, language: str = "en") -> str:
    """Get localized multiplier word (twice/three times)."""
    words = MULTIPLIER_WORDS.get(language, MULTIPLIER_WORDS["en"])
    return words.get(k, str(k))


def label_with_article(label: str, gender: str, language: str,
                       definite: bool = True, case: str = "nom",
                       capitalize: bool = False) -> str:
    """Return *label* prefixed with the correct article for gendered languages.

    For languages without grammatical articles (en, zh, ua) the label is
    returned unchanged.  For ES/FR/DE the appropriate article from
    ``grammar_utils.article`` is prepended.

    Parameters
    ----------
    label : str
        The bare noun (e.g. "padre", "père", "Vater").
    gender : str
        Grammatical gender of the noun ("m" or "f").
    language : str
        ISO language code.
    definite : bool
        True for definite article (el/le/der), False for indefinite (un/une/ein).
    case : str
        Grammatical case (only relevant for German: "nom", "acc", "dat").
    capitalize : bool
        If True, capitalize the first letter of the resulting string.
    """
    art = _get_article(language, gender, definite, case)
    if not art:
        return label
    result = f"{art} {label}"
    if capitalize:
        result = result[0].upper() + result[1:]
    return result


def fr_pronoun(gender: str) -> str:
    """Return French 3rd-person subject pronoun for verb inversion ('il'/'elle')."""
    return "elle" if gender == "f" else "il"


def de_rel_pronoun(gender: str) -> str:
    """Return German relative pronoun for aunt/uncle ('der'/'die')."""
    return "die" if gender == "f" else "der"


def narr(key: str, language: str, **kwargs) -> str:
    """Get a localized narrative sentence."""
    templates = NARRATIVE_TEMPLATES.get(language, NARRATIVE_TEMPLATES["en"])
    template = templates.get(key, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        # Fall back to English if template variable mismatch
        en_template = NARRATIVE_TEMPLATES["en"].get(key, "")
        return en_template.format(**kwargs)


def question(key: str, language: str, **kwargs) -> str:
    """Get a localized question."""
    templates = QUESTION_TEMPLATES.get(language, QUESTION_TEMPLATES["en"])
    template = templates.get(key, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        en_template = QUESTION_TEMPLATES["en"].get(key, "")
        return en_template.format(**kwargs)
