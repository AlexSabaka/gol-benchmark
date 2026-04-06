"""Multilingual translations for the Linda Fallacy plugin.

Provides per-language persona templates, distractor pools,
component statement templates, and conjunction connectors used
by both the plugin generator and the legacy ``linda_eval.py``.

Supported languages: en, es, fr, de, zh, ua.
"""

from __future__ import annotations

from typing import Dict, List

# ---------------------------------------------------------------------------
# Persona description template  (wraps name, age, traits, background, activities)
# ---------------------------------------------------------------------------

PERSONA_TEMPLATES: Dict[str, str] = {
    "en": "{name} is {age} years old, {traits}. {background}. As a student, {activities}.",
    "es": "{name} tiene {age} años, {traits}. {background}. Como estudiante, {activities}.",
    "fr": "{name} a {age} ans, {traits}. {background}. En tant qu'étudiant(e), {activities}.",
    "de": "{name} ist {age} Jahre alt, {traits}. {background}. Als Student(in) {activities}.",
    "zh": "{name}今年{age}岁，{traits}。{background}。作为学生，{activities}。",
    "ua": "{name} — {age} років, {traits}. {background}. Як студент(ка), {activities}.",
}

# ---------------------------------------------------------------------------
# Conjunction connectors  (join component_a + component_b)
# ---------------------------------------------------------------------------

CONJUNCTION_CONNECTORS: Dict[str, str] = {
    "en": " and ",
    "es": " y ",
    "fr": " et ",
    "de": " und ",
    "zh": "并且",
    "ua": " і ",
}

# ---------------------------------------------------------------------------
# Activities connectors  (join activity list items inside persona description)
# ---------------------------------------------------------------------------

ACTIVITIES_CONNECTORS: Dict[str, str] = {
    "en": " and ",
    "es": " y ",
    "fr": " et ",
    "de": " und ",
    "zh": "和",
    "ua": " та ",
}

# ---------------------------------------------------------------------------
# Component templates  — per-language, per-background
#
# Keys match the background keywords checked in generate_test_item():
#   environmental_science, computer_science, fine_arts, engineering,
#   business, philosophy, literature, history, default
#
# Each entry has "a" and "b" with a ``{name}`` placeholder.
# ---------------------------------------------------------------------------

COMPONENT_TEMPLATES: Dict[str, Dict[str, Dict[str, str]]] = {
    # ---- English ----
    "en": {
        "environmental_science": {
            "a": "{name} works for an environmental consulting firm",
            "b": "{name} is active in the environmental movement",
        },
        "computer_science": {
            "a": "{name} is a software engineer",
            "b": "{name} contributes to AI safety research",
        },
        "fine_arts": {
            "a": "{name} works as a graphic designer",
            "b": "{name} is involved in local arts advocacy",
        },
        "engineering": {
            "a": "{name} works as an engineer at a tech company",
            "b": "{name} participates in corporate social responsibility initiatives",
        },
        "business": {
            "a": "{name} works in business development",
            "b": "{name} volunteers for microfinance programs",
        },
        "philosophy": {
            "a": "{name} teaches philosophy at a community college",
            "b": "{name} writes for an online magazine on social issues",
        },
        "literature": {
            "a": "{name} works as a journalist",
            "b": "{name} runs a local book club",
        },
        "history": {
            "a": "{name} works as a museum curator",
            "b": "{name} gives lectures on cultural heritage",
        },
        "default": {
            "a": "{name} works in a bookstore",
            "b": "{name} attends social justice workshops",
        },
    },
    # ---- Spanish ----
    "es": {
        "environmental_science": {
            "a": "{name} trabaja en una consultora medioambiental",
            "b": "{name} participa activamente en el movimiento ecologista",
        },
        "computer_science": {
            "a": "{name} es ingeniero/a de software",
            "b": "{name} contribuye a la investigación sobre seguridad de la IA",
        },
        "fine_arts": {
            "a": "{name} trabaja como diseñador/a gráfico/a",
            "b": "{name} participa en la defensa del arte local",
        },
        "engineering": {
            "a": "{name} trabaja como ingeniero/a en una empresa tecnológica",
            "b": "{name} participa en iniciativas de responsabilidad social corporativa",
        },
        "business": {
            "a": "{name} trabaja en desarrollo de negocios",
            "b": "{name} es voluntario/a en programas de microfinanzas",
        },
        "philosophy": {
            "a": "{name} enseña filosofía en una universidad comunitaria",
            "b": "{name} escribe para una revista digital sobre temas sociales",
        },
        "literature": {
            "a": "{name} trabaja como periodista",
            "b": "{name} dirige un club de lectura local",
        },
        "history": {
            "a": "{name} trabaja como curador/a de museo",
            "b": "{name} da conferencias sobre patrimonio cultural",
        },
        "default": {
            "a": "{name} trabaja en una librería",
            "b": "{name} asiste a talleres de justicia social",
        },
    },
    # ---- French ----
    "fr": {
        "environmental_science": {
            "a": "{name} travaille dans un cabinet de conseil en environnement",
            "b": "{name} est actif/active dans le mouvement écologiste",
        },
        "computer_science": {
            "a": "{name} est ingénieur(e) en informatique",
            "b": "{name} contribue à la recherche sur la sécurité de l'IA",
        },
        "fine_arts": {
            "a": "{name} travaille comme graphiste",
            "b": "{name} s'implique dans la défense des arts locaux",
        },
        "engineering": {
            "a": "{name} travaille comme ingénieur(e) dans une entreprise technologique",
            "b": "{name} participe à des initiatives de responsabilité sociale des entreprises",
        },
        "business": {
            "a": "{name} travaille dans le développement commercial",
            "b": "{name} fait du bénévolat pour des programmes de microfinance",
        },
        "philosophy": {
            "a": "{name} enseigne la philosophie dans un établissement communautaire",
            "b": "{name} écrit pour un magazine en ligne sur les questions sociales",
        },
        "literature": {
            "a": "{name} travaille comme journaliste",
            "b": "{name} anime un club de lecture local",
        },
        "history": {
            "a": "{name} travaille comme conservateur/conservatrice de musée",
            "b": "{name} donne des conférences sur le patrimoine culturel",
        },
        "default": {
            "a": "{name} travaille dans une librairie",
            "b": "{name} participe à des ateliers de justice sociale",
        },
    },
    # ---- German ----
    "de": {
        "environmental_science": {
            "a": "{name} arbeitet bei einer Umweltberatungsfirma",
            "b": "{name} engagiert sich aktiv in der Umweltbewegung",
        },
        "computer_science": {
            "a": "{name} ist Softwareentwickler(in)",
            "b": "{name} forscht im Bereich KI-Sicherheit",
        },
        "fine_arts": {
            "a": "{name} arbeitet als Grafikdesigner(in)",
            "b": "{name} setzt sich für lokale Kunstförderung ein",
        },
        "engineering": {
            "a": "{name} arbeitet als Ingenieur(in) bei einem Technologieunternehmen",
            "b": "{name} beteiligt sich an Initiativen zur sozialen Unternehmensverantwortung",
        },
        "business": {
            "a": "{name} arbeitet in der Geschäftsentwicklung",
            "b": "{name} engagiert sich ehrenamtlich bei Mikrokreditprogrammen",
        },
        "philosophy": {
            "a": "{name} unterrichtet Philosophie an einer Volkshochschule",
            "b": "{name} schreibt für ein Online-Magazin über soziale Themen",
        },
        "literature": {
            "a": "{name} arbeitet als Journalist(in)",
            "b": "{name} leitet einen lokalen Buchclub",
        },
        "history": {
            "a": "{name} arbeitet als Museumskurator(in)",
            "b": "{name} hält Vorträge über kulturelles Erbe",
        },
        "default": {
            "a": "{name} arbeitet in einer Buchhandlung",
            "b": "{name} besucht Workshops für soziale Gerechtigkeit",
        },
    },
    # ---- Chinese ----
    "zh": {
        "environmental_science": {
            "a": "{name}在一家环境咨询公司工作",
            "b": "{name}积极参与环保运动",
        },
        "computer_science": {
            "a": "{name}是一名软件工程师",
            "b": "{name}为AI安全研究做贡献",
        },
        "fine_arts": {
            "a": "{name}从事平面设计工作",
            "b": "{name}参与本地艺术倡导活动",
        },
        "engineering": {
            "a": "{name}在一家科技公司担任工程师",
            "b": "{name}参与企业社会责任项目",
        },
        "business": {
            "a": "{name}从事商业开发工作",
            "b": "{name}参与小额贷款志愿项目",
        },
        "philosophy": {
            "a": "{name}在社区学院教授哲学",
            "b": "{name}为社会议题类网络杂志撰稿",
        },
        "literature": {
            "a": "{name}是一名记者",
            "b": "{name}经营一个本地读书俱乐部",
        },
        "history": {
            "a": "{name}是一名博物馆策展人",
            "b": "{name}做文化遗产方面的讲座",
        },
        "default": {
            "a": "{name}在一家书店工作",
            "b": "{name}参加社会正义工作坊",
        },
    },
    # ---- Ukrainian ----
    "ua": {
        "environmental_science": {
            "a": "{name} працює в екологічній консалтинговій фірмі",
            "b": "{name} бере активну участь в екологічному русі",
        },
        "computer_science": {
            "a": "{name} — інженер(ка) з програмного забезпечення",
            "b": "{name} робить внесок у дослідження безпеки ШІ",
        },
        "fine_arts": {
            "a": "{name} працює графічним дизайнером(кою)",
            "b": "{name} бере участь у підтримці місцевого мистецтва",
        },
        "engineering": {
            "a": "{name} працює інженером(кою) у технологічній компанії",
            "b": "{name} бере участь в ініціативах корпоративної соціальної відповідальності",
        },
        "business": {
            "a": "{name} працює у сфері розвитку бізнесу",
            "b": "{name} волонтерить у програмах мікрофінансування",
        },
        "philosophy": {
            "a": "{name} викладає філософію в громадському коледжі",
            "b": "{name} пише для онлайн-журналу про соціальні питання",
        },
        "literature": {
            "a": "{name} працює журналістом(кою)",
            "b": "{name} веде місцевий книжковий клуб",
        },
        "history": {
            "a": "{name} працює куратором(кою) музею",
            "b": "{name} читає лекції про культурну спадщину",
        },
        "default": {
            "a": "{name} працює в книгарні",
            "b": "{name} відвідує семінари з соціальної справедливості",
        },
    },
}

# ---------------------------------------------------------------------------
# Distractor pools — generic per-language, with ``{name}`` placeholder.
#
# Used as the default / fallback pool regardless of background.
# Background-specific pools are only implemented for English in the legacy
# code; all other languages use this generic pool (which contains the same
# occupations as the English default pool).
# ---------------------------------------------------------------------------

DISTRACTOR_POOLS: Dict[str, List[str]] = {
    "en": [
        "{name} is a bank teller",
        "{name} works in accounting",
        "{name} is a librarian",
        "{name} works in customer service",
        "{name} is a security guard",
        "{name} works in marketing",
        "{name} is a nurse",
        "{name} works in retail",
        "{name} is a chef",
        "{name} works as a teacher",
        "{name} is a fitness instructor",
        "{name} works in insurance",
    ],
    "es": [
        "{name} es cajero/a de banco",
        "{name} trabaja en contabilidad",
        "{name} es maestro/a de primaria",
        "{name} vende seguros",
        "{name} es bibliotecario/a",
        "{name} trabaja en ventas",
        "{name} es guardia de seguridad",
        "{name} trabaja en marketing",
        "{name} es enfermero/a",
        "{name} trabaja en atención al cliente",
        "{name} es chef",
        "{name} es instructor/a de fitness",
    ],
    "fr": [
        "{name} est caissier/caissière de banque",
        "{name} travaille en comptabilité",
        "{name} est instituteur/institutrice",
        "{name} vend des assurances",
        "{name} est bibliothécaire",
        "{name} travaille dans la vente au détail",
        "{name} est agent de sécurité",
        "{name} travaille dans le marketing",
        "{name} est infirmier/infirmière",
        "{name} travaille dans le service client",
        "{name} est chef cuisinier",
        "{name} est coach sportif",
    ],
    "de": [
        "{name} ist Bankangestellte(r)",
        "{name} arbeitet in der Buchhaltung",
        "{name} ist Grundschullehrer(in)",
        "{name} verkauft Versicherungen",
        "{name} ist Bibliothekar(in)",
        "{name} arbeitet im Einzelhandel",
        "{name} ist Sicherheitsbeauftragte(r)",
        "{name} arbeitet im Marketing",
        "{name} ist Krankenpfleger(in)",
        "{name} arbeitet im Kundendienst",
        "{name} ist Koch/Köchin",
        "{name} ist Fitnesstrainer(in)",
    ],
    "zh": [
        "{name}是银行出纳员",
        "{name}从事会计工作",
        "{name}是小学教师",
        "{name}从事保险销售",
        "{name}是图书管理员",
        "{name}在零售业工作",
        "{name}是保安",
        "{name}在市场营销部门工作",
        "{name}是护士",
        "{name}在客服部门工作",
        "{name}是厨师",
        "{name}是健身教练",
    ],
    "ua": [
        "{name} — банківський касир",
        "{name} працює в бухгалтерії",
        "{name} — вчитель(ка) початкових класів",
        "{name} продає страхові поліси",
        "{name} — бібліотекар(ка)",
        "{name} працює в роздрібній торгівлі",
        "{name} — охоронець",
        "{name} працює в маркетингу",
        "{name} — медсестра/медбрат",
        "{name} працює у відділі обслуговування клієнтів",
        "{name} — кухар(ка)",
        "{name} — фітнес-тренер(ка)",
    ],
}

# ---------------------------------------------------------------------------
# Background-specific distractor pools (English only, matching legacy code)
#
# For non-English languages the generic DISTRACTOR_POOLS is used.
# ---------------------------------------------------------------------------

EN_BACKGROUND_DISTRACTOR_POOLS: Dict[str, List[str]] = {
    "environmental_science": [
        "{name} is a bank teller",
        "{name} works in software development",
        "{name} is a high school teacher",
        "{name} works in marketing",
        "{name} is a fitness instructor",
        "{name} works as a librarian",
        "{name} is a chef",
        "{name} works in accounting",
        "{name} is a nurse",
        "{name} works in retail",
    ],
    "computer_science": [
        "{name} is a bank teller",
        "{name} works in retail management",
        "{name} is an elementary school teacher",
        "{name} works as a chef",
        "{name} is a personal trainer",
        "{name} works in marketing",
        "{name} is a librarian",
        "{name} works in accounting",
        "{name} is a nurse",
        "{name} works in insurance",
    ],
    "fine_arts": [
        "{name} is a bank teller",
        "{name} works in insurance sales",
        "{name} is a middle school teacher",
        "{name} works as a nurse",
        "{name} is a real estate agent",
        "{name} works in accounting",
        "{name} is a librarian",
        "{name} works in customer service",
        "{name} is a chef",
        "{name} works in marketing",
    ],
    "engineering": [
        "{name} is a bank teller",
        "{name} works in accounting",
        "{name} is a librarian",
        "{name} works in customer service",
        "{name} is a security guard",
        "{name} works in marketing",
        "{name} is a nurse",
        "{name} works in retail",
        "{name} is a chef",
        "{name} works as a teacher",
    ],
    "philosophy": [
        "{name} is a bank teller",
        "{name} works in marketing",
        "{name} is a librarian",
        "{name} works as a teacher",
        "{name} is a nurse",
        "{name} works in accounting",
        "{name} works in customer service",
        "{name} is a chef",
        "{name} works in retail",
        "{name} is a security guard",
    ],
}

# Aliases: some backgrounds share the same pool in legacy code
EN_BACKGROUND_DISTRACTOR_POOLS["literature"] = EN_BACKGROUND_DISTRACTOR_POOLS["fine_arts"]
EN_BACKGROUND_DISTRACTOR_POOLS["business"] = EN_BACKGROUND_DISTRACTOR_POOLS["engineering"]
EN_BACKGROUND_DISTRACTOR_POOLS["history"] = EN_BACKGROUND_DISTRACTOR_POOLS["philosophy"]


# ---------------------------------------------------------------------------
# Helper: resolve background keyword from persona background text
# ---------------------------------------------------------------------------

_BACKGROUND_KEYWORDS = [
    "environmental science",
    "computer science",
    "fine arts",
    "engineering",
    "business",
    "philosophy",
    "literature",
    "history",
]


def resolve_background_key(background_str: str) -> str:
    """Return the canonical background key for *background_str*, or ``"default"``."""
    lower = background_str.lower()
    for kw in _BACKGROUND_KEYWORDS:
        if kw in lower:
            return kw.replace(" ", "_")
    return "default"


def get_component_templates(language: str, background_key: str) -> Dict[str, str]:
    """Return ``{"a": ..., "b": ...}`` for the given language and background.

    Falls back to English, then to the ``"default"`` background.
    """
    lang_templates = COMPONENT_TEMPLATES.get(language, COMPONENT_TEMPLATES["en"])
    return lang_templates.get(background_key, lang_templates["default"])


def get_distractor_pool(language: str, background_key: str) -> List[str]:
    """Return distractor pool for the given language and background.

    English uses background-specific pools when available; all other
    languages use the generic ``DISTRACTOR_POOLS``.
    """
    if language == "en":
        pool = EN_BACKGROUND_DISTRACTOR_POOLS.get(background_key)
        if pool:
            return list(pool)
    # All other languages (and English default) use the generic pool
    return list(DISTRACTOR_POOLS.get(language, DISTRACTOR_POOLS["en"]))
