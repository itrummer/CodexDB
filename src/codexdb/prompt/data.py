'''
Created on Sep 20, 2021

@author: immanueltrummer
'''
import json
import pandas as pd

class DbPrompt():
    """ Generates partial prompt describing the database. """
    
    def __init__(self, spider_dir):
        """ Initialize from given benchmark directory. 
        
        Args:
            spider_dir: path to benchmark directory
        """
        self.schemata = self._get_schemata(spider_dir)
        self.p_style = 0
    
    def generate(self, db_id):
        """ Generates prompt following specific style. 
        
        Args:
            db_id: generate prompt describing this database
        
        Returns:
            partial prompt text
        """
        if self.p_style == 0:
            return self._comment_prompt(db_id)
        else:
            raise ValueError(f'Unknown style: {self.p_style}')
    
    def _comment_prompt(self, db_id):
        """ Describes given database as code comment. 
        
        Args:
            db_id: database identifier
        
        Returns:
            comment describing database
        """
        db_json = self.schemata[db_id]
        tables = db_json['table_names']
        columns = db_json['column_names']
        
        col_names = [name for _, name in columns]
        col_tbls = [tbl for tbl, _ in columns]
        col_groups = pd.DataFrame(col_names).groupby(col_tbls)
        
        rows = []        
        for tbl_idx, cols in col_groups:
            table = tables[tbl_idx]
            col_list = ', '.join(cols)
            rows.append(f'  {table} with fields {col_list}')
        
        return '\n'.join(rows)


    def _get_schemata(self, spider_dir):
        """ Read information on DB schemata from disk. 
        
        Args:
            spider_dir: spider benchmark directory path
        
        Returns:
            dictionary mapping DB IDs to schema information
        """
        result = {}
        t_path = f'{spider_dir}/tables.json'
        with open(t_path) as file:
            t_json = json.load(file)
            for db_info in t_json:
                db_id = db_info['db_id']
                result[db_id] = db_info
        
        return result