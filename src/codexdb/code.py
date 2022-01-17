'''
Created on Jan 17, 2022

@author: immanueltrummer
'''
import abc
import numpy as np
import openai
import pandas as pd
import sqlglot

class CodeGenerator(abc.ABC):
    """ Generates code in different languages using OpenAI. """
    
    def __init__(self, examples, nr_samples, prompt_style, model_id):
        """ Initializes with examples for few-shot learning.
        
        Args:
            examples: list of examples for few-shot learning.
            nr_samples: maximal number of examples to use.
            prompt_style: style of prompt to generate
            model_id: OpenAI model to use for generation
        """
        self.examples = examples
        self.nr_samples = nr_samples
        self.prompt_style = prompt_style
        self.model_id = model_id
    
    @abc.abstractmethod
    def generate(self, catalog, test_case, temperature):
        """ Generate code to solve given test case.
        
        Args:
            catalog: catalog with information on database content
            test_case: generate code solving this test case
            temperature: degree of randomness during generation
        
        Returns:
            generated code
        """
        raise NotImplementedError()


class PythonGenerator(CodeGenerator):
    """ Generates Python code to solve database queries. """
    
    @abc.abstractmethod
    def generate(self, catalog, test_case, temperature):
        """ Generate Python code to solve test case. """
        pass
    
    def _complete(self, prompt, temperature):
        """ Generate code by completing given prompt. 
        
        Args:
            prompt: initiate generation with this prompt
            temperature: degree of randomness in generation
        
        Returns:
            generated code, following prompt
        """
        try:
            print(f'\nPrompt:\n*******\n{prompt}\n*******')
            response = openai.Completion.create(
                engine=self.model_id, prompt=prompt, 
                temperature=temperature, max_tokens=600,
                stop='"""')
            return response['choices'][0]['text']
        except Exception as e:
            print(f'Error querying OpenAI (model: {self.model_id}): {e}')
            return ''
    
    def _db_info(self, schema, db_dir, files):
        """ Generate description of database.
        
        Args:
            schema: description of database schema
            db_dir: directory containing data
            files: names to files storing tables
            prompt_style: style of generated prompt
        
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
                for col_name, col_type in zip(df.columns, df.dtypes):
                    #header = f'{col_name}:{col_type.name}'
                    header = f'"{col_name}"'
                    headers.append(header)
                lines.append(','.join(headers))
                        
                nr_rows = df.shape[0]
                nr_cols = df.shape[1]
                for row_idx in range(min(5, nr_rows)):
                    row_parts = []
                    for col_idx in range(nr_cols):
                        value = str(df.iloc[row_idx, col_idx])
                        col_type = df.dtypes[col_idx].type
                        if not np.issubdtype(col_type, np.number):
                            value = '"' + value + '"'
                        row_parts.append(value)
                    lines.append(','.join(row_parts))
                
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
    
    def _get_plan(self, sql):
        """ Generate natural language query plan. 
        
        Args:
            sql: the SQL query to process
        
        Returns:
            list of plan steps (in order)
        """
        tokenizer = sqlglot.tokens.Tokenizer()
        parser = sqlglot.parser.Parser()
        tokens = tokenizer.tokenize(sql)
        ast = parser.parse(tokens)[0]
        
        tables = []
        for table_expr in ast.find_all(sqlglot.expressions.Table):
            table_name = table_expr.args['this'].args['this']
            tables.append(table_name)
        
        out_parts = []
        out_parts.append('Import pandas library.')
        out_parts.append(f'Load data for table {tables[0]}.')
        for table in tables[2:]:
            out_parts.append(f'Join with table {table}.')
        
        where = ast.args['where'] if 'where' in ast.args else None
        if where is not None:
            out_parts.append(f'Filter using {where.sql()}.')
        
        group_by = ast.args['group'] if 'group' in ast.args else None
        if group_by is not None:
            out_parts.append(f'Group data via {group_by.sql()}.')
        
        order_by = ast.args['order'] if 'order' in ast.args else None
        if order_by is not None:
            out_parts.append(f'Sort according to {order_by.sql()}.')
        
        selects = ast.args['expressions'] if 'expressions' in ast.args else None
        if selects is not None:
            selects_sql = ', '.join([s.sql() for s in selects])
            out_parts.append(f'Calculate {selects_sql}.')
        
        out_parts.append("Write query result to 'result.csv'.")
        out_parts = [f'{idx}. {out}' for idx, out in enumerate(out_parts, 1)]
        return out_parts
    
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
        prompt_parts += self._db_info(schema, db_dir, files, self.prompt_style)
        prompt_parts.append(f'Query: "{question}".')
        if self.prompt_style == 'train':
            prompt_parts.append(f'SQL query: {query}')
            prompt_parts += self._get_plan(query)
        else:
            prompt_parts.append('1. Import pandas library.')
            prompt_parts.append('2. Calculate query answer.')
            prompt_parts.append("3. Store result in 'result.csv'.")
        prompt_parts.append('"""')
        return '\n'.join(prompt_parts)