"""User prompt templates for the Carwash Paradox plugin."""

USER_PROMPT_TEMPLATES = {
    "en": {
        "minimal": "{setup} The carwash is {distance}. {question}",
        "casual": "Hey, quick question: {setup}  The carwash is {distance}.  {question}",
        "linguistic": (
            "I have an everyday logistics question and I'd appreciate your honest advice.\n\n"
            "{setup}  The carwash is {distance}.  {weather}{urgency}{transport}\n\n{question}"
        ),
    },
    "es": {
        "minimal": "{setup} El lavado de autos está {distance}. {question}",
        "casual": "¡Hola! Tengo una pregunta rápida: {setup} El lavado de autos está {distance}. {question}",
        "linguistic": (
            "Tengo una pregunta logística cotidiana y agradecería tu consejo honesto.\n\n"
            "{setup} El lavado de autos está {distance}. {weather}{urgency}{transport}\n\n{question}"
        ),
    },
    "fr": {
        "minimal": "{setup} Le lavage de voiture est {distance}. {question}",
        "casual": "Salut! J'ai une question rapide : {setup} Le lavage de voiture est {distance}. {question}",
        "linguistic": (
            "J'ai une question logistique quotidienne et j'apprécierais ton conseil honnête.\n\n"
            "{setup} Le lavage de voiture est {distance}. {weather}{urgency}{transport}\n\n{question}"
        ),
    },
    "de": {
        "minimal": "{setup} Die Autowäsche ist {distance}. {question}",
        "casual": "Hey, kurze Frage: {setup} Die Autowäsche ist {distance}. {question}",
        "linguistic": (
            "Ich habe eine alltägliche logistische Frage und würde deinen ehrlichen Rat schätzen.\n\n"
            "{setup} Die Autowäsche ist {distance}. {weather}{urgency}{transport}\n\n{question}"
        ),
    },
    "zh": {
        "minimal": "{setup} 洗车店在{distance}。{question}",
        "casual": "嘿，有个快速问题：{setup} 洗车店在{distance}。{question}",
        "linguistic": (
            "我有一个日常的物流问题，希望能得到你的诚实建议。\n\n"
            "{setup} 洗车店在{distance}。{weather}{urgency}{transport}\n\n{question}"
        ),
    },
    "ua": {
        "minimal": "{setup} Мийка автомобілів знаходиться {distance}. {question}",
        "casual": "Привіт! У мене швидке питання: {setup} Мийка автомобілів знаходиться {distance}. {question}",
        "linguistic": (
            "У мене є повсякденне логістичне питання, і я був би вдячний за твою чесну пораду.\n\n"
            "{setup} Мийка автомобілів знаходиться {distance}. {weather}{urgency}{transport}\n\n{question}"
        ),
    },
}

# ---------------------------------------------------------------------------
# Scenario templates
# ---------------------------------------------------------------------------

DISTANCES = {
    "en": [
        {"label": "50m",          "desc": "just 50 metres away", "colloquial": "right around the corner"},
        {"label": "100m",         "desc": "only 100 metres away", "colloquial": "a stone's throw away"},
        {"label": "200m",         "desc": "barely 200 metres away", "colloquial": "a very short walk away"},
        {"label": "corner",       "desc": "literally around the corner", "colloquial": "just around the corner"},
        {"label": "2min_walk",    "desc": "only a two-minute walk away", "colloquial": "two minutes on foot"},
    ],
    "es": [
        {"label": "50m",          "desc": "a solo 50 metros de distancia", "colloquial": "justo a la vuelta de la esquina"},
        {"label": "100m",         "desc": "a solo 100 metros de distancia", "colloquial": "a un paso de distancia"},
        {"label": "200m",         "desc": "a apenas 200 metros de distancia", "colloquial": "a un corto paseo de distancia"},
        {"label": "corner",       "desc": "literalmente a la vuelta de la esquina", "colloquial": "justo a la vuelta de la esquina"},
        {"label": "2min_walk",    "desc": "a solo a dos minutos caminando", "colloquial": "dos minutos a pie"},
    ],
    "fr": [
        {"label": "50m",          "desc": "à seulement 50 mètres", "colloquial": "juste au coin de la rue"},
        {"label": "100m",         "desc": "à seulement 100 mètres", "colloquial": "à un jet de pierre"},
        {"label": "200m",         "desc": "à peine à 200 mètres", "colloquial": "à une très courte distance à pied"},
        {"label": "corner",       "desc": "littéralement au coin de la rue", "colloquial": "juste au coin de la rue"},
        {"label": "2min_walk",    "desc": "à seulement deux minutes à pied", "colloquial": "deux minutes à pied"},
    ],
    "de": [
        {"label": "50m",          "desc": "nur 50 Meter entfernt", "colloquial": "gleich um die Ecke"},
        {"label": "100m",         "desc": "nur 100 Meter entfernt", "colloquial": "in Reichweiteeiner Hand"},
        {"label": "200m",         "desc": "kaum 200 Meter entfernt", "colloquial": "nur einen kurzen Spaziergang entfernt"},
        {"label": "corner",       "desc": "buchstäblich um die Ecke", "colloquial": "gleich um die Ecke"},
        {"label": "2min_walk",    "desc": "nur zwei Minuten zu Fuß entfernt", "colloquial": "zwei Minuten zu Fuß"},
    ],
    "zh": [
        {"label": "50m",          "desc": "仅有50米远", "colloquial": "就在拐角处"},
        {"label": "100m",         "desc": "仅有100米远", "colloquial": "近在咫尺"},
        {"label": "200m",         "desc": "仅有200米远", "colloquial": "步行非常近"},
        {"label": "corner",       "desc": "字面意思就在拐角处", "colloquial": "就在拐角处"},
        {"label": "2min_walk",    "desc": "仅有两分钟步行路程", "colloquial": "步行两分钟"},
    ],
    "ua": [
        {"label": "50m",          "desc": "всього 50 метрів", "colloquial": "прямо за рогом"},
        {"label": "100m",         "desc": "всього 100 метрів", "colloquial": "на відстані витягнутої руки"},
        {"label": "200m",         "desc": "лише 200 метрів", "colloquial": "дуже близько пішки"},
        {"label": "corner",       "desc": "буквально за рогом", "colloquial": "прямо за рогом"},
        {"label": "2min_walk",    "desc": "всього дві хвилини пішки", "colloquial": "дві хвилини пішки"},
    ],
}

FRAMINGS = {
    "en": [
        "My car is quite dirty and I'd like to wash it.",
        "I need to get my car cleaned today.",
        "I want to take my car to the carwash.",
        "My car desperately needs a wash — it's covered in mud.",
        "I've been meaning to wash my car for weeks.",
        "I just noticed how dirty my car is.",
    ],
    "es": [
        "Mi coche está bastante sucio y me gustaría lavarlo.",
        "Necesito limpiar mi coche hoy.",
        "Quiero llevar mi coche al lavado de autos.",
        "Mi coche necesita desesperadamente un lavado — está cubierto de barro.",
        "He estado pensando en lavar mi coche durante semanas.",
        "Acabo de notar lo sucio que está mi coche.",
    ],
    "fr": [
        "Ma voiture est assez sale et j'aimerais la laver.",
        "J'ai besoin de nettoyer ma voiture aujourd'hui.",
        "Je veux emmener ma voiture au lavage.",
        "Ma voiture a désespérément besoin d'un lavage — elle est couverte de boue.",
        "Je prévois de laver ma voiture depuis des semaines.",
        "Je viens de remarquer à quel point ma voiture est sale.",
    ],
    "de": [
        "Mein Auto ist ziemlich schmutzig und ich würde es gerne waschen.",
        "Ich muss mein Auto heute reinigen.",
        "Ich möchte mein Auto zur Autowäsche bringen.",
        "Mein Auto braucht dringend eine Wäsche — es ist mit Schlamm bedeckt.",
        "Ich habe vor, mein Auto seit Wochen zu waschen.",
        "Mir ist gerade aufgefallen, wie schmutzig mein Auto ist.",
    ],
    "zh": [
        "我的车很脏，我想洗一下。",
        "我需要今天把车洗了。",
        "我想把车开去洗车店。",
        "我的车非常需要洗一下——它上面全是泥。",
        "我已经想洗车好几周了。",
        "我刚注意到我的车有多脏。",
    ],
    "ua": [
        "Моя машина доволі брудна, і я хотів би її помити.",
        "Мені потрібно сьогодні помити машину.",
        "Я хотів би помити машину на автомийці.",
        "Моя машина, вона уся в багнюці. Мені терміново потрібно її помити.",
        "Я вже кілька тижнів збираюся помити машину.",
        "Я тільки що помітив, наскільки брудна моя машина.",
    ],
}

WEATHER_CONTEXTS = {
    "en": [
        "",                                          # no weather context
        "The weather is nice, perfect for a walk. ",
        "It's a sunny day outside. ",
        "It's a bit cold but dry. ",
    ],
    "es": [
        "",                                          # no weather context
        "El clima es agradable, perfecto para un paseo. ",
        "Hace sol afuera. ",
        "Hace un poco de frío pero está seco. ",
    ],
    "fr": [
        "",                                          # no weather context
        "Le temps est agréable, parfait pour une promenade. ",
        "Il fait soleil dehors. ",
        "Il fait un peu froid mais sec. ",
    ],
    "de": [
        "",                                          # no weather context
        "Das Wetter ist schön, perfekt für einen Spaziergang. ",
        "Es ist sonnig draußen. ",
        "Es ist ein bisschen kalt, aber trocken. ",
    ],
    "zh": [
        "",                                          # no weather context
        "天气很好，适合散步。 ",
        "外面阳光明媚。 ",
        "有点冷但干燥。 ",
    ],
    "ua": [
        "",                                          # no weather context
        "Погода гарна, ідеальна для прогулянки. ",
        "На вулиці сонячно. ",
        "Трохи прохолодно, але сухо. ",
    ],
}

URGENCY_PHRASES = {
    "en": [
        "",
        "I'm not in a rush. ",
        "I have some free time right now. ",
        "I want to do it as quickly as possible. ",
    ],
    "es": [
        "",
        "No tengo prisa. ",
        "Tengo algo de tiempo libre ahora mismo. ",
        "Quiero hacerlo lo más rápido posible. ",
    ],
    "fr": [
        "",
        "Je ne suis pas pressé. ",
        "J'ai un peu de temps libre en ce moment. ",
        "Je veux le faire aussi vite que possible. ",
    ],
    "de": [
        "",
        "Ich habe es nicht eilig. ",
        "Ich habe gerade etwas Freizeit. ",
        "Ich möchte es so schnell wie möglich erledigen. ",
    ],
    "zh": [
        "",
        "我不着急。 ",
        "我现在有一些空闲时间。 ",
        "我想尽快完成。 ",
    ],
    "ua": [
        "",
        "Я не поспішаю. ",
        "У мене зараз є трохи вільного часу. ",
        "Я хочу зробити це якнайшвидше. ",
    ],

}

TRANSPORT_DETAILS = {
    "en": [
        "",                                          # nothing extra
        "My car is parked right outside my house. ",
        "My car is sitting in the driveway. ",
    ],
    "es": [
        "",                                          # nothing extra
        "Mi coche está estacionado justo afuera de mi casa. ",
        "Mi coche está en la entrada de mi casa. ",
    ],
    "fr": [
        "",                                          # nothing extra
        "Ma voiture est garée juste devant ma maison. ",
        "Ma voiture est dans l'allée de ma maison. ",
    ],
    "de": [
        "",                                          # nothing extra
        "Mein Auto steht direkt vor meinem Haus. ",
        "Mein Auto steht in der Einfahrt. ",
    ],
    "zh": [
        "",                                          # nothing extra
        "我的车就停在我家门外。 ",
        "我的车停在我家的车道上。 ",
    ],
    "ua": [
        "",                                          # nothing extra
        "Моя машина припаркована прямо перед моїм домом. ",
        "Моя машина стоїть на під'їзній доріжці мого дому. ",
    ],
}

QUESTION_VARIANTS = {
    "en": [
        "Should I walk or drive to the carwash?",
        "Is it better to walk or drive there?",
        "What's the best way to get to the carwash — on foot or by car?",
        "Would you walk or drive in this situation?",
        "Walk or drive — what would you recommend?",
        "How should I travel to the carwash — walking or driving?",
    ],
    "es": [
        "¿Debería caminar o conducir hasta el lavado de autos?",
        "¿Es mejor caminar o conducir hasta allí?",
        "¿Cuál es la mejor manera de llegar al lavado de autos — a pie o en coche?",
        "¿Caminarías o conducirías en esta situación?",
        "Caminar o conducir — ¿qué recomendarías?",
        "¿Cómo debería viajar al lavado de autos — caminando o conduciendo?",
    ],
    "fr": [
        "Devrais-je marcher ou conduire jusqu'au lavage de voiture ?",
        "Est-il préférable de marcher ou de conduire jusqu'à là-bas ?",
        "Quelle est la meilleure façon d'aller au lavage de voiture — à pied ou en voiture ?",
        "Marcherais-tu ou conduirais-tu dans cette situation ?",
        "Marcher ou conduire — que recommanderais-tu ?",
        "Comment devrais-je me rendre au lavage de voiture — en marchant ou en conduisant ?",
    ],
    "de": [
        "Soll ich zum Autowaschen laufen oder fahren?",
        "Ist es besser, dorthin zu laufen oder zu fahren?",
        "Was ist der beste Weg, um zum Autowaschen zu kommen — zu Fuß oder mit dem Auto?",
        "Würdest du in dieser Situation laufen oder fahren?",
        "Laufen oder fahren — was würdest du empfehlen?",
        "Wie sollte ich zum Autowaschen reisen — zu Fuß oder mit dem Auto?",
    ],
    "zh": [
        "我应该走路还是开车去洗车店？",
        "走路还是开车去那里更好？",
        "去洗车店的最佳方式是什么——步行还是开车？",
        "在这种情况下你会走路还是开车？",
        "走路还是开车——你会推荐什么？",
        "我应该如何去洗车店——走路还是开车？",
    ],
    "ua": [
        "Мені слід йти пішки, чи їхати на машині до автомийки?",
        "Що краще — йти пішки чи їхати на машині до автомийки?",
        "Який найкращий спосіб дістатися до автомийки — пішки чи на машині?",
        "Що б ти вибрав у цій ситуації — йти пішки чи їхати на машині?",
        "Йти пішки чи їхати на машині — що б ти порекомендував?",
        "Як мені добиратися до автомийки — йти пішки чи їхати на машині?",
    ],
}
