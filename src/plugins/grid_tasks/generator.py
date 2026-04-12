"""
Grid Tasks Test Case Generator

Generates test cases with formatted tables and questions about the data.
Supports multiple data types (sales, HR, grades, inventory) and question types.
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

try:
    from faker import Faker
except ImportError:
    Faker = None

try:
    import names
except ImportError:
    names = None

from src.plugins.base import TestCase, TestCaseGenerator, ConfigField
from src.plugins.i18n.loader import compose_user_prompt
from src.plugins.grid_tasks.data.grid_i18n import (
    translate_header, get_list, get_question_template, FALLBACK_NAMES,
)
from src.utils.text_table import create_table


class FakeDataGenerator:
    """Base class for fake data generators."""

    def __init__(self, seed: Optional[int] = None, language: str = "en"):
        self.seed = seed
        self.language = language
        self.rng = random.Random(seed)
        self.faker = Faker() if Faker else None
        if self.faker and seed:
            Faker.seed(seed)
    
    def generate(self, rows: int, cols: int) -> Tuple[List[str], List[List[Any]], Dict[str, Any]]:
        """
        Generate fake data.
        
        Returns:
            Tuple of (headers, rows, metadata)
            - headers: List of column names
            - rows: List of row data
            - metadata: Dict with type info for question generation
        """
        raise NotImplementedError


class SalesDataGenerator(FakeDataGenerator):
    """Generate sales report data."""

    def generate(self, rows: int, cols: int) -> Tuple[List[str], List[List[Any]], Dict[str, Any]]:
        lang = self.language
        possible_columns = [
            ('Product', 'product'), ('Salesperson', 'name'), ('Region', 'region'),
            ('Month', 'month'), ('Quantity', 'int'), ('Revenue', 'float'),
            ('Commission', 'float'), ('Quarter', 'quarter'),
        ]
        selected = self.rng.sample(possible_columns, min(cols, len(possible_columns)))
        en_headers = [col[0] for col in selected]
        headers = [translate_header(h, "sales", lang) for h in en_headers]
        col_types = [col[1] for col in selected]

        products = get_list("products", lang)
        regions = get_list("regions", lang)
        months = get_list("months", lang)
        quarters = get_list("quarters", lang)
        fallback_names = FALLBACK_NAMES.get(lang, FALLBACK_NAMES["en"])

        data_rows = []
        for _ in range(rows):
            row = []
            for col_type in col_types:
                if col_type == 'product':
                    row.append(self.rng.choice(products))
                elif col_type == 'name':
                    if names:
                        row.append(names.get_full_name())
                    else:
                        row.append(self.rng.choice(fallback_names))
                elif col_type == 'region':
                    row.append(self.rng.choice(regions))
                elif col_type == 'month':
                    row.append(self.rng.choice(months))
                elif col_type == 'quarter':
                    row.append(self.rng.choice(quarters))
                elif col_type == 'int':
                    row.append(str(self.rng.randint(1, 100)))
                elif col_type == 'float':
                    row.append(f"{self.rng.uniform(100, 10000):.2f}")
            data_rows.append(row)

        metadata = {
            'data_type': 'sales', 'headers': headers, 'col_types': col_types,
            'numeric_columns': [i for i, t in enumerate(col_types) if t in ('int', 'float')],
            'text_columns': [i for i, t in enumerate(col_types) if t not in ('int', 'float')],
        }
        return headers, data_rows, metadata


class HRDataGenerator(FakeDataGenerator):
    """Generate HR/employee data."""

    def generate(self, rows: int, cols: int) -> Tuple[List[str], List[List[Any]], Dict[str, Any]]:
        lang = self.language
        possible_columns = [
            ('Employee', 'name'), ('Department', 'department'), ('Position', 'position'),
            ('Salary', 'float'), ('Years', 'int'), ('Location', 'city'),
        ]
        selected = self.rng.sample(possible_columns, min(cols, len(possible_columns)))
        en_headers = [col[0] for col in selected]
        headers = [translate_header(h, "hr", lang) for h in en_headers]
        col_types = [col[1] for col in selected]

        departments = get_list("departments", lang)
        positions = get_list("positions", lang)
        cities = get_list("cities", lang)
        fallback_names = FALLBACK_NAMES.get(lang, FALLBACK_NAMES["en"])

        data_rows = []
        for _ in range(rows):
            row = []
            for col_type in col_types:
                if col_type == 'name':
                    if names:
                        row.append(names.get_full_name())
                    else:
                        row.append(self.rng.choice(fallback_names))
                elif col_type == 'department':
                    row.append(self.rng.choice(departments))
                elif col_type == 'position':
                    row.append(self.rng.choice(positions))
                elif col_type == 'city':
                    row.append(self.rng.choice(cities))
                elif col_type == 'int':
                    row.append(str(self.rng.randint(0, 20)))
                elif col_type == 'float':
                    row.append(f"{self.rng.uniform(40000, 200000):.2f}")
            data_rows.append(row)

        metadata = {
            'data_type': 'hr', 'headers': headers, 'col_types': col_types,
            'numeric_columns': [i for i, t in enumerate(col_types) if t in ('int', 'float')],
            'text_columns': [i for i, t in enumerate(col_types) if t not in ('int', 'float')],
        }
        return headers, data_rows, metadata


class GradesDataGenerator(FakeDataGenerator):
    """Generate student grades data."""

    def generate(self, rows: int, cols: int) -> Tuple[List[str], List[List[Any]], Dict[str, Any]]:
        lang = self.language
        possible_columns = [
            ('Student', 'name'), ('Math', 'grade'), ('Science', 'grade'),
            ('English', 'grade'), ('History', 'grade'), ('Art', 'grade'), ('Grade', 'year'),
        ]
        selected = self.rng.sample(possible_columns, min(cols, len(possible_columns)))
        en_headers = [col[0] for col in selected]
        headers = [translate_header(h, "grades", lang) for h in en_headers]
        col_types = [col[1] for col in selected]

        years = get_list("grade_years", lang)
        fallback_names = FALLBACK_NAMES.get(lang, FALLBACK_NAMES["en"])

        data_rows = []
        for _ in range(rows):
            row = []
            for col_type in col_types:
                if col_type == 'name':
                    if names:
                        row.append(names.get_full_name())
                    else:
                        row.append(self.rng.choice(fallback_names))
                elif col_type == 'grade':
                    row.append(str(self.rng.randint(60, 100)))
                elif col_type == 'year':
                    row.append(self.rng.choice(years))
            data_rows.append(row)

        metadata = {
            'data_type': 'grades', 'headers': headers, 'col_types': col_types,
            'numeric_columns': [i for i, t in enumerate(col_types) if t == 'grade'],
            'text_columns': [i for i, t in enumerate(col_types) if t not in ('grade',)],
        }
        return headers, data_rows, metadata


class InventoryDataGenerator(FakeDataGenerator):
    """Generate inventory/stock data."""

    def generate(self, rows: int, cols: int) -> Tuple[List[str], List[List[Any]], Dict[str, Any]]:
        lang = self.language
        possible_columns = [
            ('Item', 'item'), ('SKU', 'sku'), ('Quantity', 'int'),
            ('Price', 'float'), ('Supplier', 'supplier'), ('Category', 'category'),
        ]
        selected = self.rng.sample(possible_columns, min(cols, len(possible_columns)))
        en_headers = [col[0] for col in selected]
        headers = [translate_header(h, "inventory", lang) for h in en_headers]
        col_types = [col[1] for col in selected]

        items = get_list("items", lang)
        suppliers = get_list("suppliers", lang)
        categories = get_list("categories", lang)

        data_rows = []
        for _ in range(rows):
            row = []
            for col_type in col_types:
                if col_type == 'item':
                    row.append(self.rng.choice(items))
                elif col_type == 'sku':
                    row.append(f"SKU-{self.rng.randint(1000, 9999)}")
                elif col_type == 'supplier':
                    row.append(self.rng.choice(suppliers))
                elif col_type == 'category':
                    row.append(self.rng.choice(categories))
                elif col_type == 'int':
                    row.append(str(self.rng.randint(0, 500)))
                elif col_type == 'float':
                    row.append(f"{self.rng.uniform(5, 500):.2f}")
            data_rows.append(row)

        metadata = {
            'data_type': 'inventory', 'headers': headers, 'col_types': col_types,
            'numeric_columns': [i for i, t in enumerate(col_types) if t in ('int', 'float')],
            'text_columns': [i for i, t in enumerate(col_types) if t not in ('int', 'float')],
        }
        return headers, data_rows, metadata


class QuestionFactory:
    """Generate questions and answers based on table data."""

    def __init__(self, seed: Optional[int] = None, language: str = "en"):
        self.rng = random.Random(seed)
        self.language = language

    def generate_question(
        self,
        question_type: str,
        headers: List[str],
        rows: List[List[Any]],
        metadata: Dict[str, Any]
    ) -> Tuple[str, Any]:
        """
        Generate a question and its answer.
        
        Returns:
            Tuple of (question, answer)
        """
        if question_type == 'cell_lookup':
            return self._cell_lookup(headers, rows, metadata)
        elif question_type == 'row_sum':
            return self._row_sum(headers, rows, metadata)
        elif question_type == 'column_count':
            return self._column_count(headers, rows, metadata)
        elif question_type == 'filter_count':
            return self._filter_count(headers, rows, metadata)
        elif question_type == 'max_min':
            return self._max_min(headers, rows, metadata)
        else:
            raise ValueError(f"Unknown question type: {question_type}")
    
    def _cell_lookup(
        self, headers: List[str], rows: List[List[Any]], metadata: Dict[str, Any]
    ) -> Tuple[str, Any]:
        """What is X's Y?"""
        if len(rows) == 0 or len(headers) < 2:
            return get_question_template("cell_lookup", self.language, "fallback_cell") or "What is the value?", "N/A"

        row = self.rng.choice(rows)
        id_col = self.rng.randint(0, len(headers) - 1)
        value_col = self.rng.choice([i for i in range(len(headers)) if i != id_col])

        identifier = row[id_col]
        answer = row[value_col]

        tmpl = get_question_template("cell_lookup", self.language)
        question = tmpl.format(identifier=identifier, column=headers[value_col])
        return question, answer
    
    def _row_sum(
        self, headers: List[str], rows: List[List[Any]], metadata: Dict[str, Any]
    ) -> Tuple[str, Any]:
        """What is the total of X?"""
        numeric_cols = metadata.get('numeric_columns', [])
        if not numeric_cols or len(rows) == 0:
            return get_question_template("row_sum", self.language, "fallback_sum") or "What is the total?", "0"

        col_idx = self.rng.choice(numeric_cols)
        total = sum(float(row[col_idx]) for row in rows)

        tmpl = get_question_template("row_sum", self.language)
        question = tmpl.format(column=headers[col_idx])
        return question, f"{total:.2f}"
    
    def _column_count(
        self, headers: List[str], rows: List[List[Any]], metadata: Dict[str, Any]
    ) -> Tuple[str, Any]:
        """How many X are there?"""
        if len(rows) == 0:
            return get_question_template("column_count", self.language, "fallback_count") or "How many entries are there?", "0"

        col_idx = self.rng.randint(0, len(headers) - 1)
        values = [row[col_idx] for row in rows]
        value_to_count = self.rng.choice(values)
        count = values.count(value_to_count)

        tmpl = get_question_template("column_count", self.language)
        question = tmpl.format(column=headers[col_idx], value=value_to_count)
        return question, str(count)
    
    def _filter_count(
        self, headers: List[str], rows: List[List[Any]], metadata: Dict[str, Any]
    ) -> Tuple[str, Any]:
        """How many X have Y > Z?"""
        numeric_cols = metadata.get('numeric_columns', [])
        if not numeric_cols or len(rows) < 2:
            return get_question_template("filter_count", self.language, "fallback_count") or "How many entries?", str(len(rows))

        col_idx = self.rng.choice(numeric_cols)
        values = [float(row[col_idx]) for row in rows]
        threshold = self.rng.choice(values)
        count = sum(1 for v in values if v > threshold)

        tmpl = get_question_template("filter_count", self.language)
        question = tmpl.format(column=headers[col_idx], threshold=threshold)
        return question, str(count)
    
    def _max_min(
        self, headers: List[str], rows: List[List[Any]], metadata: Dict[str, Any]
    ) -> Tuple[str, Any]:
        """Who has the highest/lowest X?"""
        numeric_cols = metadata.get('numeric_columns', [])
        text_cols = metadata.get('text_columns', [])

        if not numeric_cols or not text_cols or len(rows) == 0:
            return get_question_template("max_min", self.language, "fallback_max") or "Who has the maximum?", "Unknown"

        value_col = self.rng.choice(numeric_cols)
        id_col = self.rng.choice(text_cols)

        max_val = max(float(row[value_col]) for row in rows)
        max_row = next(row for row in rows if float(row[value_col]) == max_val)
        answer = max_row[id_col]

        tmpl = get_question_template("max_min", self.language)
        question = tmpl.format(id_col=headers[id_col], value_col=headers[value_col])
        return question, answer


class GridTasksTestCaseGenerator(TestCaseGenerator):
    """Generate test cases for grid tasks."""

    def __init__(self):
        pass  # base class helpers handle PromptEngine

    def get_default_config(self) -> Dict[str, Any]:
        return {
            'min_rows': 2,
            'max_rows': 20,
            'min_cols': 2,
            'max_cols': 10,
            'data_types': ['sales', 'hr', 'grades', 'inventory'],
            'question_types': ['cell_lookup', 'row_sum', 'column_count', 'max_min'],
            'table_style': 'unicode',
            'cases_per_config': 10,
        }

    def get_config_schema(self) -> List[ConfigField]:
        return [
            ConfigField(name='cases_per_config', label='Cases per config', field_type='number',
                        default=10, min_value=1, max_value=200),
            ConfigField(name='min_rows', label='Min rows', field_type='number',
                        default=2, min_value=2, max_value=20),
            ConfigField(name='max_rows', label='Max rows', field_type='number',
                        default=20, min_value=2, max_value=50),
            ConfigField(name='min_cols', label='Min columns', field_type='number',
                        default=2, min_value=2, max_value=10),
            ConfigField(name='max_cols', label='Max columns', field_type='number',
                        default=10, min_value=2, max_value=20),
            ConfigField(name='data_types', label='Data types', field_type='multi-select',
                        default=['sales', 'hr', 'grades', 'inventory'],
                        options=['sales', 'hr', 'grades', 'inventory']),
            ConfigField(name='question_types', label='Question types', field_type='multi-select',
                        default=['cell_lookup', 'row_sum', 'column_count', 'max_min'],
                        options=['cell_lookup', 'row_sum', 'column_count', 'filter_count', 'max_min']),
            ConfigField(name='table_style', label='Table style', field_type='select',
                        default='unicode', group='advanced',
                        options=['unicode', 'mysql', 'gfm', 'reddit', 'plain', 'html']),
        ]

    def generate_batch(
        self,
        config: Dict[str, Any],
        prompt_config: Dict[str, str],
        count: int,
        seed: Optional[int] = None
    ) -> List[TestCase]:
        """Generate a batch of test cases."""
        rng = random.Random(seed)
        
        # Extract config
        min_rows = config.get('min_rows', 2)
        max_rows = config.get('max_rows', 20)
        min_cols = config.get('min_cols', 2)
        max_cols = config.get('max_cols', 10)
        data_types = config.get('data_types', ['sales'])
        question_types = config.get('question_types', ['cell_lookup'])
        table_style = config.get('table_style', 'unicode')
        
        language_str = prompt_config.get('language', 'en')

        # Data generators
        generators = {
            'sales': SalesDataGenerator,
            'hr': HRDataGenerator,
            'grades': GradesDataGenerator,
            'inventory': InventoryDataGenerator,
        }

        test_cases = []
        question_factory = QuestionFactory(seed, language=language_str)
        
        for i in range(count):
            # Randomize table size
            num_rows = rng.randint(min_rows, max_rows)
            num_cols = rng.randint(min_cols, max_cols)
            
            # Select data type and question type
            data_type = rng.choice(data_types)
            question_type = rng.choice(question_types)
            
            # Generate data
            generator_class = generators[data_type]
            generator = generator_class(seed=seed + i if seed else None, language=language_str)
            headers, rows, metadata = generator.generate(num_rows, num_cols)
            
            # Generate question
            question, answer = question_factory.generate_question(
                question_type, headers, rows, metadata
            )
            
            # Format table
            table_data = [headers] + rows
            table_str = create_table(
                table_data,
                style=table_style,
                has_headers=True,
                trim_cells=True
            )
            
            # Create prompt
            user_style_str = prompt_config.get('user_style', 'casual')
            system_style_str = prompt_config.get('system_style', 'analytical')
            language_str = prompt_config.get('language', 'en')
            user_prompt = compose_user_prompt(
                "grid_tasks", language_str, user_style_str,
                table_str=table_str, question=question,
            )
            system_prompt = self._get_system_prompt(system_style_str, language_str)
            
            # Create test case
            test_case = TestCase(
                test_id=f"grid_tasks_{i:04d}",
                task_type="grid_tasks",
                config_name=prompt_config.get('name', 'default'),
                prompts={
                    'system': system_prompt,
                    'user': user_prompt,
                    'full': f"{system_prompt}\n\n{user_prompt}"
                },
                task_params={
                    'data_type': data_type,
                    'question_type': question_type,
                    'num_rows': num_rows,
                    'num_cols': num_cols,
                    'table_style': table_style,
                    'expected_answer': answer,
                    'question': question,
                },
                prompt_metadata={
                    'user_style': prompt_config.get('user_style', 'casual'),
                    'system_style': prompt_config.get('system_style', 'analytical'),
                    'language': prompt_config.get('language', 'en'),
                },
                generation_metadata={
                    'seed': seed,
                    'timestamp': datetime.now().isoformat(),
                    'version': '1.0.0',
                    'generator': 'GridTasksTestCaseGenerator',
                }
            )
            
            test_cases.append(test_case)
        
        return test_cases
