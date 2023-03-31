'''
Created on Sep 23, 2021

@author: immanueltrummer
'''
import codexdb.deprecated.code_gen.generic
from contextlib import redirect_stdout
from io import StringIO
import pandas as pd
import sys


class PythonGenerator(codexdb.deprecated.code_gen.generic.Generator):
    """ Generates Python code. """
    
    def execute(self, db_id, question, generated):
        self.for_prompt = False
        code_prefix = self.generate(db_id, question)
        self.for_prompt = True
        
        pruned = self._prune_code(generated)
        all_code = code_prefix + pruned        
        print(f'Executing \n{all_code}\n---')
        
        try:
            f = StringIO()
            with redirect_stdout(f):
                exec(all_code)
            return f.getvalue()
        except Exception as e:
            sys.stderr.write(f'Exception: {e}\n')
            return ''
    
    def _add_context(self):
        snippets = []
        snippets += [(0, 'import pandas as pd')]
        snippets += [(1, 'import numpy as np')]
        if not self.for_prompt:
            snippets += [(2, 'pd.set_option("max_columns", None)')]
            snippets += [(3, 'pd.set_option("max_colwidth", None)')]
            snippets += [(4, 'pd.set_option("max_rows", None)')]
        return snippets
    
    def _add_data_constraints(self, db_json):
        snippets = []
        if self.for_prompt:
            tables = db_json['table_names_original']
            columns = db_json['column_names_original']
            f_keys = db_json['foreign_keys']
            for f_idx, f_key in enumerate(f_keys):
                col_1_idx, col_2_idx = f_key
                tbl_1_idx, col_1 = columns[col_1_idx]
                tbl_2_idx, col_2 = columns[col_2_idx]
                tbl_1 = tables[tbl_1_idx]
                tbl_2 = tables[tbl_2_idx]
                question = f'What are the entries from {tbl_1} and {tbl_2}?'
                snippets += self._add_task(db_json, question, 5000 + f_idx * 100)
                code = f"print({tbl_1}.merge({tbl_2}, left_on='{col_1}', right_on='{col_2}'))"
                snippets += [(5010 + f_idx * 100, code)]
        return snippets
    
    def _add_data_load(self, db_json, tbl_idx):
        db_id = db_json['db_id']
        tables = db_json['table_names_original']
        table = tables[tbl_idx]
        path_prefix = '' if self.for_prompt else f'{self.spider_dir}/database/{db_id}/' 
        code = f"{table} = pd.read_csv('{path_prefix}{table}.csv')"
        priority = 1000 + tbl_idx * self.tbl_p_step
        return [(priority, code)]
    
    def _add_data_samples(self, db_json, tbl_idx):
        db_id = db_json['db_id']
        tables = db_json['table_names_original']
        table = tables[tbl_idx]
        df = pd.read_csv(f'{self.spider_dir}/database/{db_id}/{table}.csv')
        
        snippets = []
        start_priority = 990 + tbl_idx * self.tbl_p_step
        snippets += [(start_priority, f'# Sample data from {table}.csv:')]
        
        for row_ctr, row in df.iloc[0:2,:].reset_index().iterrows():
            priority = start_priority + row_ctr + 1
            code = f'# {list(row)}'
            snippets += [(priority, code)]
        
        return snippets
    
    def _add_data_schema(self, db_json, tbl_idx):
        tables = db_json['table_names_original']
        tbl_name = tables[tbl_idx]
        all_columns = db_json['column_names_original']
        tbl_columns = [c[1] for c in all_columns if c[0] == tbl_idx]
        quoted_cols = [f"'{c}'" for c in tbl_columns]
        col_list = ', '.join(quoted_cols)
        code = f"{tbl_name}.columns = [{col_list}]"
        priority = 1001 + tbl_idx * self.tbl_p_step
        return [(priority, code)]

    def _add_data_types(self, db_json, tbl_idx):
        tables = db_json['table_names_original']
        tbl_name = tables[tbl_idx]
        col_info = db_json['column_names_original']
        col_types = db_json['column_types']
        t_items = []
        for col_idx, col_info in enumerate(col_info):
            col_tbl, col_name = col_info
            if col_tbl == tbl_idx:
                sql_type = col_types[col_idx]
                d_type = self._sql_to_dtype(sql_type)
                t_item = f"'{col_name}':{d_type}"
                t_items.append(t_item)
        
        priority = 1002 + tbl_idx * self.tbl_p_step
        # snippet = f'{tbl_name} = {tbl_name}.astype({{{", ".join(t_items)}}})'
        snippet = f'# Column types in {tbl_name}: {", ".join(t_items)}'
        # return [(priority, snippet)]
        return []
    
    def _add_examples(self, db_json, question):
        return []
    
    def _add_task(self, db_json, question, first_priority):
        q_requoted = question.replace("'", '"')
        snippets = [(first_priority, f"# {q_requoted} Print answer.")]
        snippets += [(first_priority+1, f"print('{q_requoted}')")]
        return snippets
    
    def _cmd_load(self, table, data_path):
        return f"{table} = pd.read_csv('{data_path}')"
    
    def _prune_code(self, generated):
        """ Prune generated code. 
        
        Args:
            generated: code generated by Codex
        
        Returns:
            code parts that likely answer query
        """
        gen_lines = generated.split('\n')
        gen_lines = [g for g in gen_lines if g]
        if len(gen_lines) > 1:
            gen_lines.pop()
        
        if gen_lines:
            first_line = gen_lines[0]
            if not first_line.startswith('print('):
                gen_lines[0] = 'print(' + first_line + ')'
        
        pruned = []
        for line in gen_lines:
            if not line.startswith('print('):
                break
            else:
                pruned.append(line)
        
        return '\n'.join(pruned)
    
    def _sql_to_dtype(self, sql_type):
        """ Translates SQL type into dtype for pandas data frame. 
        
        Args:
            sql_type: SQL column type
        
        Returns:
            dtype of Pandas data frame 
        """
        sql_type = sql_type.lower()
        if sql_type == 'text':
            return 'object'
        elif sql_type == 'number':
            return 'np.float64'
        else:
            return 'object'