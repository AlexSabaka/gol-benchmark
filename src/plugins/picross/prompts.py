"""
Picross (Nonogram) Prompt Templates

6 languages × 3 styles.  Template variables:
  {row_clues}  — formatted row clue string
  {col_clues}  — formatted column clue string
  {rows}       — number of rows
  {cols}       — number of columns
  {f}          — filled cell marker
  {e}          — empty cell marker
"""

USER_PROMPT_TEMPLATES = {
    # ── English ──────────────────────────────────────────────────────
    "en": {
        "linguistic": (
            "This is a Nonogram (Picross) puzzle on a {rows}×{cols} grid.\n\n"
            "RULES:\n"
            "1. Each row and column has a list of clue numbers.\n"
            "2. Each number tells you the length of a consecutive group of filled cells ({f}) in that line.\n"
            "3. Groups appear in the given order, left-to-right for rows and top-to-bottom for columns.\n"
            "4. There must be at least one empty cell ({e}) between consecutive groups.\n"
            "5. All remaining cells are empty ({e}).\n\n"
            "CLUES:\n"
            "{row_clues}\n"
            "{col_clues}\n\n"
            "Solve the puzzle. Respond with ONLY the {rows}×{cols} grid, one row per line, "
            "cells separated by spaces, using {f} for filled and {e} for empty.\n"
            "Solution:"
        ),
        "casual": (
            "Nonogram time! {rows}×{cols} grid.\n\n"
            "The clue numbers tell you how many consecutive filled cells ({f}) "
            "are in each row/column, in order. Groups are separated by at least one empty cell ({e}).\n\n"
            "{row_clues}\n"
            "{col_clues}\n\n"
            "Show me the solved grid using {f} and {e}:"
        ),
        "minimal": (
            "Nonogram, {rows}×{cols}.\n\n"
            "{row_clues}\n"
            "{col_clues}\n\n"
            "Grid ({f}=filled, {e}=empty):"
        ),
    },
    # ── Spanish ──────────────────────────────────────────────────────
    "es": {
        "linguistic": (
            "Este es un Nonograma (Picross) en una cuadrícula de {rows}×{cols}.\n\n"
            "REGLAS:\n"
            "1. Cada fila y columna tiene una lista de números pista.\n"
            "2. Cada número indica la longitud de un grupo consecutivo de celdas rellenas ({f}).\n"
            "3. Los grupos aparecen en el orden dado (izquierda a derecha / arriba a abajo).\n"
            "4. Debe haber al menos una celda vacía ({e}) entre grupos consecutivos.\n"
            "5. Las celdas restantes están vacías ({e}).\n\n"
            "PISTAS:\n"
            "{row_clues}\n"
            "{col_clues}\n\n"
            "Resuelve el rompecabezas. Responde SOLO con la cuadrícula de {rows}×{cols}, "
            "una fila por línea, celdas separadas por espacios, usando {f} para rellena y {e} para vacía.\n"
            "Solución:"
        ),
        "casual": (
            "¡Hora del Nonograma! Cuadrícula de {rows}×{cols}.\n\n"
            "Los números indican cuántas celdas rellenas ({f}) consecutivas hay en cada fila/columna. "
            "Los grupos se separan por al menos una celda vacía ({e}).\n\n"
            "{row_clues}\n"
            "{col_clues}\n\n"
            "Muéstrame la cuadrícula resuelta usando {f} y {e}:"
        ),
        "minimal": (
            "Nonograma, {rows}×{cols}.\n\n"
            "{row_clues}\n"
            "{col_clues}\n\n"
            "Cuadrícula ({f}=rellena, {e}=vacía):"
        ),
    },
    # ── French ───────────────────────────────────────────────────────
    "fr": {
        "linguistic": (
            "Voici un Nonogramme (Picross) sur une grille de {rows}×{cols}.\n\n"
            "RÈGLES :\n"
            "1. Chaque ligne et colonne a une liste d'indices numériques.\n"
            "2. Chaque nombre indique la longueur d'un groupe consécutif de cases remplies ({f}).\n"
            "3. Les groupes apparaissent dans l'ordre donné (gauche à droite / haut en bas).\n"
            "4. Il doit y avoir au moins une case vide ({e}) entre les groupes consécutifs.\n"
            "5. Les cases restantes sont vides ({e}).\n\n"
            "INDICES :\n"
            "{row_clues}\n"
            "{col_clues}\n\n"
            "Résolvez le puzzle. Répondez UNIQUEMENT avec la grille {rows}×{cols}, "
            "une ligne par ligne, cases séparées par des espaces, {f} pour remplie et {e} pour vide.\n"
            "Solution :"
        ),
        "casual": (
            "C'est l'heure du Nonogramme ! Grille {rows}×{cols}.\n\n"
            "Les nombres indiquent combien de cases remplies ({f}) consécutives il y a "
            "dans chaque ligne/colonne. Les groupes sont séparés par au moins une case vide ({e}).\n\n"
            "{row_clues}\n"
            "{col_clues}\n\n"
            "Montrez-moi la grille résolue avec {f} et {e} :"
        ),
        "minimal": (
            "Nonogramme, {rows}×{cols}.\n\n"
            "{row_clues}\n"
            "{col_clues}\n\n"
            "Grille ({f}=remplie, {e}=vide) :"
        ),
    },
    # ── German ───────────────────────────────────────────────────────
    "de": {
        "linguistic": (
            "Dies ist ein Nonogramm (Picross) auf einem {rows}×{cols}-Raster.\n\n"
            "REGELN:\n"
            "1. Jede Zeile und Spalte hat eine Liste von Hinweiszahlen.\n"
            "2. Jede Zahl gibt die Länge einer aufeinanderfolgenden Gruppe gefüllter Zellen ({f}) an.\n"
            "3. Die Gruppen erscheinen in der angegebenen Reihenfolge (links nach rechts / oben nach unten).\n"
            "4. Zwischen aufeinanderfolgenden Gruppen muss mindestens eine leere Zelle ({e}) sein.\n"
            "5. Alle übrigen Zellen sind leer ({e}).\n\n"
            "HINWEISE:\n"
            "{row_clues}\n"
            "{col_clues}\n\n"
            "Lösen Sie das Rätsel. Antworten Sie NUR mit dem {rows}×{cols}-Raster, "
            "eine Zeile pro Zeile, Zellen durch Leerzeichen getrennt, {f} für gefüllt und {e} für leer.\n"
            "Lösung:"
        ),
        "casual": (
            "Nonogramm-Zeit! {rows}×{cols}-Raster.\n\n"
            "Die Zahlen geben an, wie viele aufeinanderfolgende gefüllte Zellen ({f}) "
            "in jeder Zeile/Spalte sind. Gruppen sind durch mindestens eine leere Zelle ({e}) getrennt.\n\n"
            "{row_clues}\n"
            "{col_clues}\n\n"
            "Zeigen Sie mir das gelöste Raster mit {f} und {e}:"
        ),
        "minimal": (
            "Nonogramm, {rows}×{cols}.\n\n"
            "{row_clues}\n"
            "{col_clues}\n\n"
            "Raster ({f}=gefüllt, {e}=leer):"
        ),
    },
    # ── Chinese ──────────────────────────────────────────────────────
    "zh": {
        "linguistic": (
            "这是一道 {rows}×{cols} 的数织（Nonogram/Picross）谜题。\n\n"
            "规则：\n"
            "1. 每行和每列都有一组提示数字。\n"
            "2. 每个数字表示该行/列中一组连续填充单元格（{f}）的长度。\n"
            "3. 各组按给定顺序排列（行从左到右，列从上到下）。\n"
            "4. 连续的组之间必须至少有一个空单元格（{e}）。\n"
            "5. 其余所有单元格为空（{e}）。\n\n"
            "提示：\n"
            "{row_clues}\n"
            "{col_clues}\n\n"
            "请解决这道谜题。仅回复 {rows}×{cols} 的网格，每行一行，"
            "单元格用空格分隔，{f} 表示填充，{e} 表示空。\n"
            "答案："
        ),
        "casual": (
            "数织时间！{rows}×{cols} 网格。\n\n"
            "提示数字表示每行/列中有多少连续的填充单元格（{f}），"
            "各组之间至少有一个空单元格（{e}）。\n\n"
            "{row_clues}\n"
            "{col_clues}\n\n"
            "请用 {f} 和 {e} 展示解答："
        ),
        "minimal": (
            "数织，{rows}×{cols}。\n\n"
            "{row_clues}\n"
            "{col_clues}\n\n"
            "网格（{f}=填充，{e}=空）："
        ),
    },
    # ── Ukrainian ────────────────────────────────────────────────────
    "ua": {
        "linguistic": (
            "Це нонограма (Picross) на сітці {rows}×{cols}.\n\n"
            "ПРАВИЛА:\n"
            "1. Кожен рядок і стовпець має список чисел-підказок.\n"
            "2. Кожне число вказує довжину групи послідовних заповнених клітинок ({f}).\n"
            "3. Групи з'являються у заданому порядку (зліва направо / зверху вниз).\n"
            "4. Між послідовними групами має бути щонайменше одна порожня клітинка ({e}).\n"
            "5. Усі інші клітинки порожні ({e}).\n\n"
            "ПІДКАЗКИ:\n"
            "{row_clues}\n"
            "{col_clues}\n\n"
            "Розв'яжіть головоломку. Відповідайте ЛИШЕ сіткою {rows}×{cols}, "
            "один рядок на лінію, клітинки через пробіли, {f} — заповнена, {e} — порожня.\n"
            "Розв'язок:"
        ),
        "casual": (
            "Час нонограми! Сітка {rows}×{cols}.\n\n"
            "Числа показують, скільки послідовних заповнених клітинок ({f}) "
            "є в кожному рядку/стовпці. Групи розділені щонайменше однією порожньою клітинкою ({e}).\n\n"
            "{row_clues}\n"
            "{col_clues}\n\n"
            "Покажіть мені розв'язану сітку з {f} та {e}:"
        ),
        "minimal": (
            "Нонограма, {rows}×{cols}.\n\n"
            "{row_clues}\n"
            "{col_clues}\n\n"
            "Сітка ({f}=заповнена, {e}=порожня):"
        ),
    },
}
