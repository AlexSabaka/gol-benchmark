"""
Inverted Cup – Test Case Generator

Generates variations of the "sealed top / open bottom cup" puzzle.

Parametrisation axes:
- source: how the person came to have the cup (gift, found, bought, etc.)
- description_style: how the unusual orientation is described
- action_question: what the person wants to do with it
- extra_context: optional extra detail (unusual material, purpose)
"""
from __future__ import annotations

import itertools
import random
from typing import Any, Dict, List

from src.plugins.base import TestCaseGenerator, TestCase, ConfigField
from src.plugins.inverted_cup.prompts import USER_PROMPT_TEMPLATES


# ---------------------------------------------------------------------------
# Scenario building blocks
# ---------------------------------------------------------------------------

SOURCES = {
    "en": [
        "My friend gifted me this unusual cup.",
        "I bought this novelty cup online.",
        "I found this strange cup at a garage sale.",
        "Someone left this cup on my desk as a joke.",
        "I received this cup as a birthday present.",
        "I picked up this curious cup at a souvenir shop.",
        "I won this cup in a competition.",
    ],
    "es": [
        "Mi amigo me regaló esta taza inusual.",
        "Compré esta taza novedosa por internet.",
        "Encontré esta taza extraña en una venta de garaje.",
        "Alguien dejó esta taza en mi escritorio como broma.",
        "Recibí esta taza como regalo de cumpleaños.",
        "Compré esta curiosa taza en una tienda de recuerdos.",
        "Gané esta taza en una competencia.",
    ],
    "fr": [
        "Mon ami m'a offert cette tasse inhabituelle.",
        "J'ai acheté cette tasse originale en ligne.",
        "J'ai trouvé cette tasse étrange dans un vide-grenier.",
        "Quelqu'un a laissé cette tasse sur mon bureau pour plaisanter.",
        "J'ai reçu cette tasse comme cadeau d'anniversaire.",
        "J'ai trouvé cette curieuse tasse dans une boutique de souvenirs.",
        "J'ai gagné cette tasse lors d'une compétition.",
    ],
    "de": [
        "Mein Freund hat mir diese ungewöhnliche Tasse geschenkt.",
        "Ich habe diese kuriose Tasse online gekauft.",
        "Ich habe diese seltsame Tasse auf einem Flohmarkt gefunden.",
        "Jemand hat diese Tasse als Scherz auf meinen Schreibtisch gestellt.",
        "Ich habe diese Tasse als Geburtstagsgeschenk bekommen.",
        "Ich habe diese kuriose Tasse in einem Souvenirladen gekauft.",
        "Ich habe diese Tasse bei einem Wettbewerb gewonnen.",
    ],
    "zh": [
        "我的朋友送了我这个不寻常的杯子。",
        "我在网上买了这个新奇的杯子。",
        "我在旧货市场发现了这个奇怪的杯子。",
        "有人开玩笑地把这个杯子放在我桌上。",
        "我收到这个杯子作为生日礼物。",
        "我在纪念品商店买了这个奇特的杯子。",
        "我在比赛中赢得了这个杯子。",
    ],
    "ua": {
        "m": [
            "Мій друг подарував мені цю незвичайну чашку.",
            "Я купив цю оригінальну чашку в інтернеті.",
            "Я знайшов цю дивну чашку на барахолці.",
            "Хтось залишив цю чашку на моєму столі як жарт.",
            "Я отримав цю чашку як подарунок на день народження.",
            "Я знайшов цю цікаву чашку в сувенірній крамниці.",
            "Я виграв цю чашку на конкурсі.",
        ],
        "f": [
            "Моя подруга подарувала мені цю незвичайну чашку.",
            "Я купила цю оригінальну чашку в інтернеті.",
            "Я знайшла цю дивну чашку на барахолці.",
            "Хтось залишив цю чашку на моєму столі як жарт.",
            "Я отримала цю чашку як подарунок на день народження.",
            "Я знайшла цю цікаву чашку в сувенірній крамниці.",
            "Я виграла цю чашку на конкурсі.",
        ],
    },
}

# Tags are language-independent identifiers; description text is localized
DESCRIPTION_STYLES = {
    "en": [
        ("The top is completely sealed and the bottom is open.", "sealed_top_open_bottom"),
        ("It has a solid, sealed lid on top and an open hole at the bottom.", "lid_top_hole_bottom"),
        ("The cup is upside-down: the opening faces down and the base is at the top.", "upside_down_explicit"),
        ("The rim (opening) is at the bottom, and the solid closed end is at the top.", "rim_at_bottom"),
        ("It looks like a normal cup but inverted: closed on top, open on the bottom.", "inverted_normal"),
        ("The cup's mouth points downward and the sealed end is on top.", "mouth_down"),
        ("When placed on a table, the closed end sits on top and the opening faces the table.", "closed_on_top"),
    ],
    "es": [
        ("La parte superior está completamente sellada y el fondo está abierto.", "sealed_top_open_bottom"),
        ("Tiene una tapa sólida y sellada arriba y un agujero abierto abajo.", "lid_top_hole_bottom"),
        ("La taza está al revés: la abertura mira hacia abajo y la base está arriba.", "upside_down_explicit"),
        ("El borde (abertura) está abajo y el extremo cerrado está arriba.", "rim_at_bottom"),
        ("Parece una taza normal pero invertida: cerrada arriba, abierta abajo.", "inverted_normal"),
        ("La boca de la taza apunta hacia abajo y el extremo sellado está arriba.", "mouth_down"),
        ("Al colocarla en una mesa, el extremo cerrado queda arriba y la abertura mira hacia la mesa.", "closed_on_top"),
    ],
    "fr": [
        ("Le dessus est complètement scellé et le fond est ouvert.", "sealed_top_open_bottom"),
        ("Elle a un couvercle solide et scellé en haut et un trou ouvert en bas.", "lid_top_hole_bottom"),
        ("La tasse est à l'envers : l'ouverture est vers le bas et la base est en haut.", "upside_down_explicit"),
        ("Le bord (ouverture) est en bas et l'extrémité fermée est en haut.", "rim_at_bottom"),
        ("Elle ressemble à une tasse normale mais inversée : fermée en haut, ouverte en bas.", "inverted_normal"),
        ("L'embouchure de la tasse pointe vers le bas et l'extrémité scellée est en haut.", "mouth_down"),
        ("Posée sur une table, l'extrémité fermée est en haut et l'ouverture fait face à la table.", "closed_on_top"),
    ],
    "de": [
        ("Die Oberseite ist vollständig versiegelt und der Boden ist offen.", "sealed_top_open_bottom"),
        ("Sie hat oben einen festen, versiegelten Deckel und unten ein offenes Loch.", "lid_top_hole_bottom"),
        ("Die Tasse steht auf dem Kopf: die Öffnung zeigt nach unten und der Boden ist oben.", "upside_down_explicit"),
        ("Der Rand (Öffnung) ist unten und das geschlossene Ende ist oben.", "rim_at_bottom"),
        ("Sie sieht aus wie eine normale Tasse, aber umgedreht: oben geschlossen, unten offen.", "inverted_normal"),
        ("Die Öffnung der Tasse zeigt nach unten und das versiegelte Ende ist oben.", "mouth_down"),
        ("Auf einem Tisch stehend ist das geschlossene Ende oben und die Öffnung zeigt zum Tisch.", "closed_on_top"),
    ],
    "zh": [
        ("顶部完全密封，底部是开口的。", "sealed_top_open_bottom"),
        ("顶部有一个坚固的密封盖，底部有一个开口。", "lid_top_hole_bottom"),
        ("这个杯子是倒置的：开口朝下，底部在上面。", "upside_down_explicit"),
        ("杯沿（开口）在底部，封闭的那端在顶部。", "rim_at_bottom"),
        ("它看起来像一个普通杯子但是倒过来的：上面封闭，下面开口。", "inverted_normal"),
        ("杯口朝下，密封端在上面。", "mouth_down"),
        ("放在桌子上时，封闭端在上面，开口朝向桌面。", "closed_on_top"),
    ],
    "ua": [
        ("Верх повністю запечатаний, а дно відкрите.", "sealed_top_open_bottom"),
        ("Зверху міцна запечатана кришка, а знизу відкритий отвір.", "lid_top_hole_bottom"),
        ("Чашка перевернута: отвір дивиться вниз, а основа зв��рху.", "upside_down_explicit"),
        ("Край (отвір) знизу, а закритий кінець зверху.", "rim_at_bottom"),
        ("Виглядає як звичайна чашка, але перевернута: зверху закрита, знизу відкрита.", "inverted_normal"),
        ("Горлечко чашки дивиться вниз, а запечатаний кінець зверху.", "mouth_down"),
        ("Коли стоїть на столі, закритий кінець зверху, а отвір дивиться на стіл.", "closed_on_top"),
    ],
}

ACTION_QUESTIONS = {
    "en": [
        "How should I use this cup to drink from it?",
        "What's the correct way to use this cup?",
        "How do I drink from this cup?",
        "What should I do to be able to use this cup normally?",
        "How do I use this cup to hold a liquid?",
        "What do I need to do first before I can drink from this cup?",
        "I want to fill it with water — what should I do?",
    ],
    "es": [
        "¿Cómo debo usar esta taza para beber de ella?",
        "¿Cuál es la forma correcta de usar esta taza?",
        "¿Cómo bebo de esta taza?",
        "¿Qué debo hacer para poder usar esta taza normalmente?",
        "¿Cómo uso esta taza para contener líquido?",
        "¿Qué necesito hacer primero antes de poder beber de esta taza?",
        "Quiero llenarla con agua — ¿qu�� debo hacer?",
    ],
    "fr": [
        "Comment dois-je utiliser cette tasse pour boire ?",
        "Quelle est la bonne façon d'utiliser cette tasse ?",
        "Comment boire dans cette tasse ?",
        "Que dois-je faire pour pouvoir utiliser cette tasse normalement ?",
        "Comment utiliser cette tasse pour contenir un liquide ?",
        "Que dois-je faire en premier avant de pouvoir boire dans cette tasse ?",
        "Je veux la remplir d'eau — que dois-je faire ?",
    ],
    "de": [
        "Wie soll ich diese Tasse benutzen, um daraus zu trinken?",
        "Was ist die richtige Art, diese Tasse zu benutzen?",
        "Wie trinke ich aus dieser Tasse?",
        "Was muss ich tun, um diese Tasse normal benutzen zu können?",
        "Wie benutze ich diese Tasse, um eine Flüssigkeit aufzubewahren?",
        "Was muss ich zuerst tun, bevor ich aus dieser Tasse trinken kann?",
        "Ich möchte sie mit Wasser füllen — was soll ich tun?",
    ],
    "zh": [
        "我应该怎么用这个杯子来喝水？",
        "使用这个杯子的正确方法是什么？",
        "我怎么用这个杯子喝东西？",
        "我应该怎么做才能正常使用这个杯子？",
        "我怎么用这个杯子装液体？",
        "在用这个杯子喝水之前我需要先做什么？",
        "我想把它装满水——我该怎么做？",
    ],
    "ua": [
        "Як мені використовувати цю чашку, щоб з неї пити?",
        "Який правильний спосіб використання цієї чашки?",
        "Як мені пити з цієї чашки?",
        "Що мені потрібно зробити, щоб нормально користуватися цією чашкою?",
        "Як використовувати цю чашку для рідини?",
        "Що мені потрібно зробити спочатку, перш ніж пити з цієї чашки?",
        "Я хочу наповнити її водою — що мені робити?",
    ],
}

EXTRA_CONTEXTS = {
    "en": [
        "",
        "It's made of a transparent material so I can see it clearly. ",
        "It's a sturdy plastic cup. ",
        "The seal on the top is permanent and cannot be removed. ",
        "The cup is otherwise identical to a normal cup. ",
    ],
    "es": [
        "",
        "Está hecha de un material transparente así que la puedo ver claramente. ",
        "Es una taza resistente de plástico. ",
        "El sello en la parte superior es permanente y no se puede quitar. ",
        "La taza es por lo demás idéntica a una taza normal. ",
    ],
    "fr": [
        "",
        "Elle est faite d'un matériau transparent, donc je peux la voir clairement. ",
        "C'est une tasse en plastique solide. ",
        "Le scellé en haut est permanent et ne peut pas être retiré. ",
        "La tasse est par ailleurs identique à une tasse normale. ",
    ],
    "de": [
        "",
        "Sie ist aus einem transparenten Material, sodass ich sie deutlich sehen kann. ",
        "Es ist eine stabile Plastiktasse. ",
        "Die Versiegelung oben ist dauerhaft und kann nicht entfernt werden. ",
        "Die Tasse ist ansonsten identisch mit einer normalen Tasse. ",
    ],
    "zh": [
        "",
        "它是用透明材料做的，所以我可以清楚地看到它。",
        "这是一个结实的塑料杯。",
        "顶部的密封是永久性的，无法拆除。",
        "这个杯子其他方面和普通杯子完全一样。",
    ],
    "ua": [
        "",
        "Вона зроблена з прозорого матеріалу, тому я чітко її бачу. ",
        "Це міцна пластикова чашка. ",
        "Пломба зверху постійна і не може бути знята. ",
        "В іншому чашка ідентична звичайній чашці. ",
    ],
}

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------


# Templates moved to prompts.py


class InvertedCupGenerator(TestCaseGenerator):
    """Generates Inverted Cup test cases."""

    def __init__(self):
        pass  # base class helpers handle PromptEngine

    def get_config_schema(self) -> List[ConfigField]:
        return [
            ConfigField(name='count', label='Number of cases', field_type='number',
                        default=100, min_value=1, max_value=500,
                        help='Cases to generate per prompt configuration'),
            ConfigField(name='description_styles', label='Description styles', field_type='multi-select',
                        default=[d[1] for d in DESCRIPTION_STYLES["en"]],
                        options=[d[1] for d in DESCRIPTION_STYLES["en"]], group='advanced',
                        help='Which cup description styles to include'),
        ]

    def generate_batch(
        self,
        config: Dict[str, Any],
        prompt_config: Dict[str, Any],
        count: int,
        seed: int,
    ) -> List[TestCase]:
        rng = random.Random(seed)

        user_style = prompt_config.get("user_style", "casual")
        system_style = prompt_config.get("system_style", "analytical")
        language = prompt_config.get("language", "en")
        config_name = prompt_config.get("name", f"{user_style}_{system_style}")

        # Select language-specific content
        lang_sources_raw = SOURCES.get(language, SOURCES["en"])
        lang_descs = DESCRIPTION_STYLES.get(language, DESCRIPTION_STYLES["en"])
        lang_questions = ACTION_QUESTIONS.get(language, ACTION_QUESTIONS["en"])
        lang_extras = EXTRA_CONTEXTS.get(language, EXTRA_CONTEXTS["en"])

        # Filter descriptions if config restricts them
        allowed_desc = config.get("description_styles", None)
        descriptions = (
            [d for d in lang_descs if d[1] in allowed_desc]
            if allowed_desc
            else lang_descs
        ) or lang_descs

        # If sources is gender-split (dict with m/f), use the "m" list for
        # combination building; actual gender selection happens per test case.
        is_gendered_sources = isinstance(lang_sources_raw, dict) and "m" in lang_sources_raw
        lang_sources = lang_sources_raw["m"] if is_gendered_sources else lang_sources_raw

        combinations = list(itertools.product(
            range(len(lang_sources)),  # source indices
            descriptions,
            lang_questions,
            lang_extras,
        ))
        rng.shuffle(combinations)

        extended = (combinations * (count // len(combinations) + 2))[:count]

        test_cases: List[TestCase] = []
        for idx, (src_idx, (desc, desc_tag), question, extra) in enumerate(extended):
            # Random subject gender per test case
            subject_gender = rng.choice(["m", "f"])

            # Select source by gender
            if is_gendered_sources:
                source = lang_sources_raw[subject_gender][src_idx % len(lang_sources_raw[subject_gender])]
            else:
                source = lang_sources[src_idx % len(lang_sources)]

            tc = self._build_test_case(
                idx=idx,
                seed=seed,
                config_name=config_name,
                user_style=user_style,
                system_style=system_style,
                language=language,
                source=source,
                desc=desc,
                desc_tag=desc_tag,
                question=question,
                extra=extra,
                subject_gender=subject_gender,
            )
            test_cases.append(tc)

        return test_cases

    # ------------------------------------------------------------------
    def _build_test_case(
        self,
        idx: int,
        seed: int,
        config_name: str,
        user_style: str,
        system_style: str,
        language: str,
        source: str,
        desc: str,
        desc_tag: str,
        question: str,
        extra: str,
        subject_gender: str = "m",
    ) -> TestCase:
        user_prompt, system_prompt, full_prompt = self._build_prompts(
            USER_PROMPT_TEMPLATES, language, user_style, system_style,
            source=source, description=desc, extra=extra, question=question,
        )

        task_params = {
            "expected_answer": "flip",
            "source": source,
            "description": desc,
            "description_tag": desc_tag,
            "question": question,
            "extra": extra,
            "subject_gender": subject_gender,
        }

        return TestCase(
            test_id=f"inverted_cup_{seed}_{idx:04d}",
            task_type="inverted_cup",
            config_name=config_name,
            prompts={
                "system": system_prompt,
                "user": user_prompt,
                "full": full_prompt,
            },
            task_params=task_params,
            prompt_metadata={
                "user_style": user_style,
                "system_style": system_style,
                "language": language,
            },
            generation_metadata={
                "seed": seed,
                "index": idx,
                "description_tag": desc_tag,
            },
        )
