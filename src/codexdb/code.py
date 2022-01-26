'''
Created on Jan 17, 2022

@author: immanueltrummer
'''
import abc
import codexdb.plan
import numpy as np
import openai
import pandas as pd
import random

class CodeGenerator(abc.ABC):
    """ Generates code in different languages using OpenAI. """
    
    def __init__(self, catalog, examples, nr_samples, prompt_style, model_id):
        """ Initializes with examples for few-shot learning.
        
        Args:
            catalog: database catalog
            examples: list of examples for few-shot learning.
            nr_samples: maximal number of examples to use.
            prompt_style: style of prompt to generate
            model_id: OpenAI model to use for generation
        """
        self.catalog = catalog
        self.examples = examples
        self.nr_samples = nr_samples
        self.prompt_style = prompt_style
        self.ai_kwargs = {'engine':model_id}
        self.code_prefix = ''
        self.code_suffix = ''
    
    def generate(self, test_case, temperature):
        """ Generate code to solve given test case.
        
        Args:
            test_case: generate code solving this test case
            temperature: degree of randomness during generation
        
        Returns:
            generated code
        """
        prefix = self._sample_prompts()
        db_id = test_case['db_id']
        schema = self.catalog.schema(db_id)
        files = self.catalog.files(db_id)
        db_dir = self.catalog.db_dir(db_id)
        question = test_case['question']
        query = test_case['query']
        suffix = self._get_prompt(schema, db_dir, files, question, query)
        prompt = prefix + '\n' + suffix
        gen_code = self._complete(prompt, temperature)
        return self.code_prefix + gen_code + self.code_suffix

    def _complete(self, prompt, temperature):
        """ Generate code by completing given prompt. 
        
        Args:
            prompt: initiate generation with this prompt
            temperature: degree of randomness
        
        Returns:
            generated code, following prompt
        """
        try:
            print(f'\nPrompt:\n*******\n{prompt}\n*******')
            response = openai.Completion.create(
                prompt=prompt, temperature=temperature,
                **self.ai_kwargs)
            return response['choices'][0]['text']
        except Exception as e:
            print(f'Error querying OpenAI: {e}')
            return ''
    
    def _db_sample(self, db_dir, file_name, max_rows):
        """ Returns data sample from specified file. 
        
        Args:
            db_dir: directory containing database data
            file_name: name of file within directory
            max_rows: maximal number of sample rows
        
        Returns:
            list of string representing sample rows
        """
        lines = []
        df = pd.read_csv(f'{db_dir}/{file_name}')
        nr_rows = df.shape[0]
        nr_cols = df.shape[1]
        for row_idx in range(min(max_rows, nr_rows)):
            row_parts = []
            for col_idx in range(nr_cols):
                value = str(df.iloc[row_idx, col_idx])
                col_type = df.dtypes[col_idx].type
                if not np.issubdtype(col_type, np.number):
                    value = '"' + value + '"'
                row_parts.append(value)
            lines.append(','.join(row_parts))
        return lines
    
    @abc.abstractmethod
    def _get_prompt(self, schema, db_dir, files, question, query):
        """ Generate prompt for processing specific query. 
        
        Args:
            schema: description of database schema
            db_dir: directory storing data files
            files: location of data files for tables
            question: natural language query
            query: SQL translation of query
        
        Returns:
            Prompt for generating code for executing query
        """
        raise NotImplementedError()
    
    @abc.abstractmethod
    def _sample_prompts(self):
        """ Generate sample prompts for few-shot learning. 
        
        Returns:
            Prompt prefix with completion examples
        """
        raise NotImplementedError()


class PythonGenerator(CodeGenerator):
    """ Generates Python code to solve database queries. """
    
    def __init__(self, *kwargs):
        """ Initializes for Python code generation.
        
        Args:
            kwargs: arguments of super class constructor
        """
        super().__init__(*kwargs)
        self.ai_kwargs['max_tokens'] = 600
        self.ai_kwargs['stop'] = '"""'
        self.planner = codexdb.plan.NlPlanner()
        suffix_parts = [
            "\nimport pandas as pd",
            "if isinstance(final_result, (pd.DataFrame, pd.Series, list, dict)):",
            "\tfinal_result = pd.DataFrame(final_result)",
            "\tfinal_result.to_csv('result.csv', index=False)",
            "else:",
            "\twith open('result.csv', 'w') as file:",
            "\t\tfile.write('result\\n')",
            "\t\tfile.write(str(final_result))"
            ]
        self.code_suffix = '\n'.join(suffix_parts)
    
    def _db_info(self, schema, db_dir, files, max_rows):
        """ Generate description of database.
        
        Args:
            schema: description of database schema
            db_dir: directory containing data
            files: names to files storing tables
            max_rows: maximal number of rows in data sample
        
        Returns:
            list of description lines
        """
        lines = []
        tables = schema['table_names_original']
        all_columns = schema['column_names_original']
        nr_tables = len(tables)
        for tbl_idx in range(nr_tables):
            filename = files[tbl_idx]
            tbl_name = tables[tbl_idx]
            
            if self.prompt_style == 'data':
                
                lines.append(f'Sample from table {tbl_name}, stored in "{filename}":')
                df = pd.read_csv(f'{db_dir}/{filename}')
                headers = []
                for col_name in df.columns:
                    header = f'"{col_name}"'
                    headers.append(header)
                lines.append(','.join(headers))
                
                file_name = files[tbl_idx]
                lines += self._db_sample(db_dir, file_name, max_rows)
                
                type_items = []
                for col_name, col_type in zip(df.columns, df.dtypes):
                    if np.issubdtype(col_type, np.number):
                        print_type = 'numeric' 
                    else:
                        print_type = 'text'
                    type_item = f'"{col_name}": {print_type}'
                    type_items.append(type_item)
                lines.append('Column types: ' + ', '.join(type_items))
                    
            else:
                tbl_columns = ["'" + c[1] + "'" for c in all_columns if c[0] == tbl_idx]
                col_list = ','.join(tbl_columns)
                line = f'Table {tbl_name} with columns {col_list}, ' \
                    f'stored in \'{filename}\'.'
                lines.append(line)
                
        return lines
    
    def _get_prompt(self, schema, db_dir, files, question, query):
        """ Generate prompt for processing specific query. 
        
        Args:
            schema: description of database schema
            db_dir: directory storing data files
            files: location of data files for tables
            question: natural language query
            query: SQL translation of query
        
        Returns:
            Prompt for generating code for executing query
        """
        prompt_parts = []
        prompt_parts.append('"""')
        prompt_parts += self._db_info(schema, db_dir, files, 5)
        if self.prompt_style == 'train':
            #prompt_parts.append(f'SQL query: {query}')
            prompt_parts.append('Processing steps:')
            plan = self.planner.plan(query)
            plan.add_step(['Import pandas library'], False)
            # plan.add_step(["Store result data frame in 'result.csv' (without index)"])
            prompt_parts += plan.steps()
        else:
            prompt_parts.append(f'Query: "{question}".')
            prompt_parts.append('1. Import pandas library.')
            prompt_parts.append('2. Calculate query answer.')
            prompt_parts.append("3. Store result in 'result.csv'.")
        prompt_parts.append('"""')
        return '\n'.join(prompt_parts)
    
    def _sample_prompts(self):
        """ Generate prompts from examples for few-shot learning.
        
        Returns:
            a prefix of the full prompt to generate
        """
        parts = []
        if self.examples:
            selected = random.sample(self.examples, k=self.nr_samples)
            for example in selected:
                db_id = example['schema']['db_id']
                db_dir = self.catalog.db_dir(db_id)
                prompt = self._get_prompt(
                    example['schema'], db_dir, example['files'], 
                    example['question'], example['query'])
                parts.append(prompt)
                parts.append(example['code'])
                parts.append('')
                parts.append('')
        return '\n'.join(parts)


class SqlGenerator(CodeGenerator):
    """ Translates natural language questions into SQL queries. """
    
    def __init__(self, *kwargs):
        """ Initializes for SQL query generation.
        
        Args:
            kwargs: arguments for super class constructor
        """
        super().__init__(*kwargs)
        self.ai_kwargs['max_tokens'] = 150
        self.ai_kwargs['stop'] = ['#', ';']
        self.code_prefix = 'SELECT '
    
    def _get_prompt(self, schema, db_dir, files, question, query):
        """ Returns prompt for given question. """
        lines = []
        lines.append('### Postgres SQL tables, with their properties:')
        lines.append('#')
        
        tables = schema['table_names_original']
        all_columns = schema['column_names_original']
        for idx, table in enumerate(tables):
            cols = [c[1].replace(' ', '_') for c in all_columns if c[0] == idx]
            lines.append(f'# {table}({",".join(cols)})')
            if self.prompt_style == 'data':
                #lines.append(f'Sample rows from {table}:')
                file_name = files[idx]
                sample = self._db_sample(db_dir, file_name, 5)
                lines += ['# ' + s for s in sample]

        lines.append('#')
        lines.append(f'### Query: "{question}"')
        lines.append('SELECT')
        return '\n'.join(lines)
    
    def _sample_prompts(self):
        """ Returns prefix with samples for few-shot learning. """
        parts = []
        selected = random.sample(self.examples, k=self.nr_samples)
        for example in selected:
            db_id = example['schema']['db_id']
            db_dir = self.catalog.db_dir(db_id)
            prompt = self._get_prompt(
                example['schema'], db_dir, example['files'], 
                example['question'], example['query'])
            parts.append(prompt + example['query'][6:])
            parts.append('')
            parts.append('')
        return '\n'.join(parts)