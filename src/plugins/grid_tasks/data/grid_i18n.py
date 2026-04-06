"""Multilingual translations for Grid Tasks plugin — headers, data values, questions."""

# ── Column headers per generator type ────────────────────────────────────

HEADERS = {
    "sales": {
        "en": {"Product": "Product", "Salesperson": "Salesperson", "Region": "Region", "Month": "Month", "Quantity": "Quantity", "Revenue": "Revenue", "Commission": "Commission", "Quarter": "Quarter"},
        "es": {"Product": "Producto", "Salesperson": "Vendedor", "Region": "Región", "Month": "Mes", "Quantity": "Cantidad", "Revenue": "Ingresos", "Commission": "Comisión", "Quarter": "Trimestre"},
        "fr": {"Product": "Produit", "Salesperson": "Vendeur", "Region": "Région", "Month": "Mois", "Quantity": "Quantité", "Revenue": "Revenus", "Commission": "Commission", "Quarter": "Trimestre"},
        "de": {"Product": "Produkt", "Salesperson": "Verkäufer", "Region": "Region", "Month": "Monat", "Quantity": "Menge", "Revenue": "Umsatz", "Commission": "Provision", "Quarter": "Quartal"},
        "zh": {"Product": "产品", "Salesperson": "销售员", "Region": "地区", "Month": "月份", "Quantity": "数量", "Revenue": "收入", "Commission": "佣金", "Quarter": "季度"},
        "ua": {"Product": "Продукт", "Salesperson": "Продавець", "Region": "Регіон", "Month": "Місяць", "Quantity": "Кількість", "Revenue": "Дохід", "Commission": "Комісія", "Quarter": "Квартал"},
    },
    "hr": {
        "en": {"Employee": "Employee", "Department": "Department", "Position": "Position", "Salary": "Salary", "Years": "Years", "Location": "Location"},
        "es": {"Employee": "Empleado", "Department": "Departamento", "Position": "Puesto", "Salary": "Salario", "Years": "Años", "Location": "Ubicación"},
        "fr": {"Employee": "Employé", "Department": "Département", "Position": "Poste", "Salary": "Salaire", "Years": "Années", "Location": "Lieu"},
        "de": {"Employee": "Mitarbeiter", "Department": "Abteilung", "Position": "Position", "Salary": "Gehalt", "Years": "Jahre", "Location": "Standort"},
        "zh": {"Employee": "员工", "Department": "部门", "Position": "职位", "Salary": "薪资", "Years": "工龄", "Location": "地点"},
        "ua": {"Employee": "Працівник", "Department": "Відділ", "Position": "Посада", "Salary": "Зарплата", "Years": "Роки", "Location": "Місце"},
    },
    "grades": {
        "en": {"Student": "Student", "Math": "Math", "Science": "Science", "English": "English", "History": "History", "Art": "Art", "Grade": "Grade"},
        "es": {"Student": "Estudiante", "Math": "Matemáticas", "Science": "Ciencias", "English": "Inglés", "History": "Historia", "Art": "Arte", "Grade": "Curso"},
        "fr": {"Student": "Élève", "Math": "Maths", "Science": "Sciences", "English": "Anglais", "History": "Histoire", "Art": "Arts", "Grade": "Classe"},
        "de": {"Student": "Schüler", "Math": "Mathe", "Science": "Naturwiss.", "English": "Englisch", "History": "Geschichte", "Art": "Kunst", "Grade": "Klasse"},
        "zh": {"Student": "学生", "Math": "数学", "Science": "科学", "English": "英语", "History": "历史", "Art": "美术", "Grade": "年级"},
        "ua": {"Student": "Учень", "Math": "Математика", "Science": "Природознавство", "English": "Англійська", "History": "Історія", "Art": "Мистецтво", "Grade": "Клас"},
    },
    "inventory": {
        "en": {"Item": "Item", "SKU": "SKU", "Quantity": "Quantity", "Price": "Price", "Supplier": "Supplier", "Category": "Category"},
        "es": {"Item": "Artículo", "SKU": "SKU", "Quantity": "Cantidad", "Price": "Precio", "Supplier": "Proveedor", "Category": "Categoría"},
        "fr": {"Item": "Article", "SKU": "SKU", "Quantity": "Quantité", "Price": "Prix", "Supplier": "Fournisseur", "Category": "Catégorie"},
        "de": {"Item": "Artikel", "SKU": "SKU", "Quantity": "Menge", "Price": "Preis", "Supplier": "Lieferant", "Category": "Kategorie"},
        "zh": {"Item": "物品", "SKU": "SKU", "Quantity": "数量", "Price": "价格", "Supplier": "供应商", "Category": "类别"},
        "ua": {"Item": "Товар", "SKU": "SKU", "Quantity": "Кількість", "Price": "Ціна", "Supplier": "Постачальник", "Category": "Категорія"},
    },
}


def translate_header(en_header: str, data_type: str, language: str) -> str:
    """Translate a header from English to the target language."""
    return HEADERS.get(data_type, {}).get(language, {}).get(en_header, en_header)


# ── Data values per language ─────────────────────────────────────────────

PRODUCTS = {
    "en": ["Laptop", "Phone", "Tablet", "Monitor", "Keyboard", "Mouse", "Headset", "Camera"],
    "es": ["Portátil", "Teléfono", "Tableta", "Monitor", "Teclado", "Ratón", "Auriculares", "Cámara"],
    "fr": ["Ordinateur", "Téléphone", "Tablette", "Écran", "Clavier", "Souris", "Casque", "Caméra"],
    "de": ["Laptop", "Handy", "Tablet", "Monitor", "Tastatur", "Maus", "Headset", "Kamera"],
    "zh": ["笔记本", "手机", "平板", "显示器", "键盘", "鼠标", "耳机", "相机"],
    "ua": ["Ноутбук", "Телефон", "Планшет", "Монітор", "Клавіатура", "Мишка", "Гарнітура", "Камера"],
}

REGIONS = {
    "en": ["North", "South", "East", "West", "Central"],
    "es": ["Norte", "Sur", "Este", "Oeste", "Centro"],
    "fr": ["Nord", "Sud", "Est", "Ouest", "Centre"],
    "de": ["Nord", "Süd", "Ost", "West", "Zentral"],
    "zh": ["北部", "南部", "东部", "西部", "中部"],
    "ua": ["Північ", "Південь", "Схід", "Захід", "Центр"],
}

MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    "es": ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"],
    "fr": ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"],
    "de": ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"],
    "zh": ["一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"],
    "ua": ["Січень", "Лютий", "Березень", "Квітень", "Травень", "Червень", "Липень", "Серпень", "Вересень", "Жовтень", "Листопад", "Грудень"],
}

QUARTERS = {
    "en": ["Q1", "Q2", "Q3", "Q4"],
    "es": ["T1", "T2", "T3", "T4"],
    "fr": ["T1", "T2", "T3", "T4"],
    "de": ["Q1", "Q2", "Q3", "Q4"],
    "zh": ["第一季度", "第二季度", "第三季度", "第四季度"],
    "ua": ["К1", "К2", "К3", "К4"],
}

DEPARTMENTS = {
    "en": ["Engineering", "Sales", "Marketing", "HR", "Finance", "Operations"],
    "es": ["Ingeniería", "Ventas", "Marketing", "RRHH", "Finanzas", "Operaciones"],
    "fr": ["Ingénierie", "Ventes", "Marketing", "RH", "Finances", "Opérations"],
    "de": ["Technik", "Vertrieb", "Marketing", "Personal", "Finanzen", "Betrieb"],
    "zh": ["工程", "销售", "市场", "人力资源", "财务", "运营"],
    "ua": ["Інженерія", "Продажі", "Маркетинг", "Кадри", "Фінанси", "Операції"],
}

POSITIONS = {
    "en": ["Manager", "Senior", "Junior", "Lead", "Associate", "Director"],
    "es": ["Gerente", "Sénior", "Júnior", "Líder", "Asociado", "Director"],
    "fr": ["Responsable", "Sénior", "Junior", "Chef", "Associé", "Directeur"],
    "de": ["Manager", "Senior", "Junior", "Leiter", "Mitarbeiter", "Direktor"],
    "zh": ["经理", "高级", "初级", "主管", "助理", "总监"],
    "ua": ["Менеджер", "Старший", "Молодший", "Керівник", "Асоціат", "Директор"],
}

CITIES = {
    "en": ["New York", "San Francisco", "Chicago", "Austin", "Seattle", "Boston"],
    "es": ["Madrid", "Barcelona", "Sevilla", "Valencia", "Bilbao", "Málaga"],
    "fr": ["Paris", "Lyon", "Marseille", "Toulouse", "Nice", "Bordeaux"],
    "de": ["Berlin", "München", "Hamburg", "Köln", "Frankfurt", "Stuttgart"],
    "zh": ["北京", "上海", "广州", "深圳", "杭州", "成都"],
    "ua": ["Київ", "Львів", "Одеса", "Харків", "Дніпро", "Запоріжжя"],
}

GRADE_YEARS = {
    "en": ["9th", "10th", "11th", "12th"],
    "es": ["3.º ESO", "4.º ESO", "1.º Bach.", "2.º Bach."],
    "fr": ["3ème", "2nde", "1ère", "Terminale"],
    "de": ["9. Klasse", "10. Klasse", "11. Klasse", "12. Klasse"],
    "zh": ["初三", "高一", "高二", "高三"],
    "ua": ["9 клас", "10 клас", "11 клас", "12 клас"],
}

ITEMS = {
    "en": ["Widget", "Gadget", "Gizmo", "Tool", "Part", "Component", "Module", "Device"],
    "es": ["Widget", "Gadget", "Aparato", "Herramienta", "Pieza", "Componente", "Módulo", "Dispositivo"],
    "fr": ["Widget", "Gadget", "Bidule", "Outil", "Pièce", "Composant", "Module", "Appareil"],
    "de": ["Widget", "Gadget", "Gerät", "Werkzeug", "Teil", "Komponente", "Modul", "Gerät"],
    "zh": ["部件", "小工具", "装置", "工具", "零件", "组件", "模块", "设备"],
    "ua": ["Віджет", "Гаджет", "Пристрій", "Інструмент", "Деталь", "Компонент", "Модуль", "Прилад"],
}

SUPPLIERS = {
    "en": ["Acme Corp", "Global Inc", "TechSupply", "Parts Plus", "Supply Chain Co"],
    "es": ["Acme SA", "Global SL", "TechSupply", "Repuestos Plus", "Cadena SL"],
    "fr": ["Acme SA", "Global SAS", "TechSupply", "Pièces Plus", "Supply Chain"],
    "de": ["Acme GmbH", "Global AG", "TechSupply", "Teile Plus", "Lieferkette GmbH"],
    "zh": ["先锋公司", "环球公司", "科技供应", "零件之家", "供应链公司"],
    "ua": ["Acme ТОВ", "Глобал ТОВ", "TechSupply", "Деталі Плюс", "Ланцюг ТОВ"],
}

CATEGORIES = {
    "en": ["Electronics", "Hardware", "Software", "Office", "Industrial"],
    "es": ["Electrónica", "Hardware", "Software", "Oficina", "Industrial"],
    "fr": ["Électronique", "Matériel", "Logiciel", "Bureau", "Industriel"],
    "de": ["Elektronik", "Hardware", "Software", "Büro", "Industrie"],
    "zh": ["电子产品", "硬件", "软件", "办公用品", "工业"],
    "ua": ["Електроніка", "Обладнання", "Програми", "Офіс", "Промисловість"],
}

# Name lists kept per-language for cultural context
FALLBACK_NAMES = {
    "en": ["Alice Smith", "Bob Johnson", "Carol White", "David Brown"],
    "es": ["Ana García", "Carlos López", "María Fernández", "Juan Martínez"],
    "fr": ["Marie Dupont", "Jean Martin", "Claire Bernard", "Pierre Durand"],
    "de": ["Anna Müller", "Hans Schmidt", "Klara Fischer", "Thomas Weber"],
    "zh": ["李明", "王芳", "张伟", "刘洋"],
    "ua": ["Олена Коваленко", "Андрій Шевченко", "Марія Бондаренко", "Іван Мельник"],
}


def get_list(name: str, language: str) -> list:
    """Get a localized data list by name with English fallback."""
    table = globals().get(name.upper())
    if table is None:
        return []
    return table.get(language, table.get("en", []))


# ── Question templates ───────────────────────────────────────────────────

QUESTION_TEMPLATES = {
    "en": {
        "cell_lookup": "What is {identifier}'s {column}?",
        "row_sum": "What is the total {column} across all entries?",
        "column_count": "How many entries have {column} equal to {value}?",
        "filter_count": "How many entries have {column} greater than {threshold}?",
        "max_min": "Which {id_col} has the highest {value_col}?",
        "fallback_cell": "What is the value?",
        "fallback_sum": "What is the total?",
        "fallback_count": "How many entries are there?",
        "fallback_max": "Who has the maximum?",
    },
    "es": {
        "cell_lookup": "¿Cuál es el valor de {column} para {identifier}?",
        "row_sum": "¿Cuál es el total de {column} en todas las entradas?",
        "column_count": "¿Cuántas entradas tienen {column} igual a {value}?",
        "filter_count": "¿Cuántas entradas tienen {column} mayor que {threshold}?",
        "max_min": "¿Qué {id_col} tiene el valor más alto de {value_col}?",
        "fallback_cell": "¿Cuál es el valor?",
        "fallback_sum": "¿Cuál es el total?",
        "fallback_count": "¿Cuántas entradas hay?",
        "fallback_max": "¿Quién tiene el máximo?",
    },
    "fr": {
        "cell_lookup": "Quelle est la valeur de {column} pour {identifier} ?",
        "row_sum": "Quel est le total de {column} pour toutes les entrées ?",
        "column_count": "Combien d'entrées ont {column} égal à {value} ?",
        "filter_count": "Combien d'entrées ont {column} supérieur à {threshold} ?",
        "max_min": "Quel {id_col} a la valeur la plus élevée de {value_col} ?",
        "fallback_cell": "Quelle est la valeur ?",
        "fallback_sum": "Quel est le total ?",
        "fallback_count": "Combien d'entrées y a-t-il ?",
        "fallback_max": "Qui a le maximum ?",
    },
    "de": {
        "cell_lookup": "Was ist der Wert von {column} für {identifier}?",
        "row_sum": "Was ist die Summe von {column} über alle Einträge?",
        "column_count": "Wie viele Einträge haben {column} gleich {value}?",
        "filter_count": "Wie viele Einträge haben {column} größer als {threshold}?",
        "max_min": "Welche Zeile hat den höchsten Wert bei {value_col}?",
        "fallback_cell": "Was ist der Wert?",
        "fallback_sum": "Was ist die Summe?",
        "fallback_count": "Wie viele Einträge gibt es?",
        "fallback_max": "Wer hat das Maximum?",
    },
    "zh": {
        "cell_lookup": "{identifier}的{column}是什么？",
        "row_sum": "所有条目的{column}总计是多少？",
        "column_count": "有多少条目的{column}等于{value}？",
        "filter_count": "有多少条目的{column}大于{threshold}？",
        "max_min": "哪个{id_col}的{value_col}最高？",
        "fallback_cell": "值是什么？",
        "fallback_sum": "总计是多少？",
        "fallback_count": "有多少条目？",
        "fallback_max": "谁最高？",
    },
    "ua": {
        "cell_lookup": "Яке значення {column} у {identifier}?",
        "row_sum": "Яка загальна сума {column} по всіх записах?",
        "column_count": "Скільки записів мають {column} рівне {value}?",
        "filter_count": "Скільки записів мають {column} більше ніж {threshold}?",
        "max_min": "Який {id_col} має найвище значення {value_col}?",
        "fallback_cell": "Яке значення?",
        "fallback_sum": "Яка сума?",
        "fallback_count": "Скільки записів?",
        "fallback_max": "Хто має максимум?",
    },
}


def get_question_template(question_type: str, language: str, fallback_key: str = "") -> str:
    """Get a localized question template."""
    lang_q = QUESTION_TEMPLATES.get(language, QUESTION_TEMPLATES["en"])
    return lang_q.get(question_type, lang_q.get(fallback_key, ""))
