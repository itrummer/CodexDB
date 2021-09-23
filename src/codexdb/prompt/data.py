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
    
    def load_data(self, db_id):
        """ Generates code for data loading. 
        
        Args:
            db_id: database identifier
        
        Returns:
            code for loading data
        """
        tbl_to_cols = self._get_tbls_to_cols(db_id)
        rows = []
        for tbl, cols in tbl_to_cols.items():
            # df_name = tbl.replace(' ', '_')
            # quoted_cols = [f"'{c}'" for c in cols]
            # col_list = ', '.join(quoted_cols)
            # row = f"{df_name} = pd.read_csv('{tbl}.csv', names=[{col_list}])"
            # rows.append(row)
            df_name = tbl.replace(' ', '_')
            row = f"{df_name} = pd.read_csv('{tbl}.csv')"
            rows.append(row)
            quoted_cols = [f"'{c}'" for c in cols]
            col_list = ', '.join(quoted_cols)
            row = f"{df_name}.columns = [{col_list}]"
            rows.append(row)
        return '\n'.join(rows)
    
    def schema_comment(self, db_id):
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
        for tbl_idx, cols_df in col_groups:
            if tbl_idx >= 0:
                table = tables[tbl_idx]
                cols = list(cols_df.loc[:,0])
                quoted_cols = [f"'{col}'" for col in cols]
                col_list = ', '.join(quoted_cols)
                rows.append(f'     {table}: data frame with fields {col_list}')
        
        return '\n  Args:\n' + '\n'.join(rows)
    
    def table_signature(self, db_id):
        """ Create function signature with table names. 
        
        Args:
            db_id: database identifier
        
        Returns:
            text of function signature
        """
        db_json = self.schemata[db_id]
        tables = [t.replace(' ', '_') for t in db_json['table_names']]
        return f'def calculate({", ".join(tables)}):'

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
    
    def _get_tbls_to_cols(self, db_id):
        """ Generate mapping from tables to column lists.
        
        Args:
            db_id: database identifier
        
        Returns:
            dictionary mapping tables to columns
        """
        db_json = self.schemata[db_id]
        tables = db_json['table_names_original']
        columns = db_json['column_names']
        
        col_names = [name for _, name in columns]
        col_tbls = [tbl for tbl, _ in columns]
        col_groups = pd.DataFrame(col_names).groupby(col_tbls)
        
        result = {}
        for tbl_idx, cols_df in col_groups:
            if tbl_idx >= 0:
                table = tables[tbl_idx]
                cols = list(cols_df.loc[:,0])
                result[table] = cols
        
        return result