'''
Created on Sep 23, 2021

@author: immanueltrummer
'''
from abc import ABC, abstractmethod
import json
import pandas as pd

class Generator(ABC):
    """ Super class of all code generators. """
    
    def __init__(self, spider_dir):
        """ Initializes code generator.
        
        Args:
            spider_dir: Spider benchmark directory
        """
        self.spider_dir = spider_dir
        self.schemata = self._get_schemata(spider_dir)
        self.for_prompt = True
        self.col_names = 0
        self.col_types = 0
        self.p_keys = 0
        self.f_keys = 0
        self.data_struct = 0
        self.operators = 0
        self.examples = 0
        self.tbl_p_step = 50
    
    @abstractmethod
    def execute(self, db_id, question, generated):
        """ Execute generated code and return output.
        
        Args:
            db_id: database identifier
            question: generated code answers this question
            generated: code generated by Codex
        
        Returns:
            output when executing generated code
        """
        pass
    
    def generate(self, db_id, question):
        """ Generate code according to specified style.
        
        Args:
            db_id: database identifier
            question: generated prompt targets this question
        
        Returns:
            generated code (used as prompt or for execution)
        """
        snippets = []
        snippets += self._add_context()
        snippets += self._add_data(db_id)
        snippets += self._add_examples(db_id, question)
        snippets += self._add_task(db_id, question, 100000)
        ordered = [s[1] for s in sorted(snippets, key=lambda s:s[0])]
        return '\n'.join(ordered) + '\n'
     
    @abstractmethod   
    def _add_context(self):
        """ Add code creating context (e.g., required libraries). 
        
        Returns:
            prioritized snippets (priority, snippet)
        """
        pass
    
    def _add_data(self, db_id):
        """ Add code loading and describing data.
        
        Args:
            db_id: database identifier
        
        Returns:
            snippets with associated priority
        """
        db_json = self.schemata[db_id]
        tables = db_json['table_names_original']
        
        snippets = []
        for tbl_idx, _ in enumerate(tables):
            snippets += self._add_data_samples(db_json, tbl_idx)
            snippets += self._add_data_load(db_json, tbl_idx)
            snippets += self._add_data_schema(db_json, tbl_idx)
            snippets += self._add_data_types(db_json, tbl_idx)
        
        snippets += self._add_data_constraints(db_json)
        return snippets
    
    @abstractmethod
    def _add_data_constraints(self, db_json):
        """ Add code illustrating foreign key constraints.
        
        Args:
            db_json: json description of database
        
        Returns:
            list of snippets with associated priority
        """
        pass
    
    @abstractmethod
    def _add_data_load(self, db_json, tbl_idx):
        """ Add code for loading a specific table. 
        
        Args:
            db_json: description of database schema
            tbl_idx: index of table to load
        
        Returns:
            snippets with associated priority
        """
        pass
    
    @abstractmethod
    def _add_data_samples(self, db_json, tbl_idx):
        """ Adds samples from table rows (e.g., via comments).
        
        Args:
            db_json: JSON description of database schema
            tbl_idx: index of current table
        
        Returns:
            list of snippets with priority
        """
        pass
    
    @abstractmethod
    def _add_data_schema(self, db_json, tbl_idx):
        """ Add code describing table columns.
        
        Args:
            db_json: description of database schema
            tbl_idx: describe schema of this table
        
        Returns:
            list of tuples (priority and snippet)
        """
        pass
    
    @abstractmethod
    def _add_data_types(self, db_json, tbl_idx):
        """ Add description of data types. 
        
        Args:
            db_json: JSON description of database
            tbl_idx: add column types for this table
        
        Returns:
            list of tuples (priority and snippet)
        """
        pass
    
    @abstractmethod
    def _add_examples(self, db_json, question):
        """ Add examples for task to solve.
        
        Args:
            db_json: JSON description of database schema
            question: we ultimately want to answer this query
        
        Returns:
            list of snippets with associated priority
        """
        pass
    
    @abstractmethod    
    def _add_task(self, db_json, question, start_priority):
        """ Add code describing task to solve.
        
        Args:
            db_json: JSON description of database schema
            question: ultimately we want to answer this question
            start_priority: priority of first produced line
        
        Returns:
            list of snippets with associated priority
        """
        pass
    
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