'''
Created on Oct 3, 2021

@author: immanueltrummer
'''
import abc
import os
import pandas as pd
import subprocess
import sys
import sqlite3
import time

class ExecutionEngine(abc.ABC):
    """ Executes code in different languages. """
    
    def __init__(self, catalog):
        """ Initialize with database catalog and variables.
        
        Args:
            catalog: informs on database schema and file locations
        """
        self.catalog = catalog
        self.tmp_dir = os.environ['CODEXDB_TMP']
        self.result_path = f'{self.tmp_dir}/result.csv'
    
    @abc.abstractmethod
    def execute(self, db_id, code, timeout_s):
        """ Execute code written in specified language.
        
        Args:
            db_id: code references data in this database
            code: execute this code
            timeout_s: execution timeout in seconds
        
        Returns:
            Boolean success flag, output, execution statistics
        """
        raise NotImplementedError()
    
    def _clean(self):
        """ Cleans up working directory before execution. 
        
        The result file may have been generated either as
        file or as directory. This handles multiple cases.
        """
        subprocess.run(['rm', f'{self.tmp_dir}/result.csv/*'])
        subprocess.run(['rm', '-d', f'{self.tmp_dir}/result.csv'])
        subprocess.run(['rm', f'{self.tmp_dir}/result.csv'])
    
    def _copy_db(self, db_id):
        """ Copies data to a temporary directory.
        
        Args:
            db_id: database ID
        """
        src_dir = self.catalog.db_dir(db_id)
        for tbl_file in self.catalog.files(db_id):
            cmd = f'sudo cp -r {src_dir}/{tbl_file} {self.tmp_dir}'
            os.system(cmd)
    
    def _expand_paths(self, db_id, code):
        """ Expand relative paths to data files in code.
        
        Args:
            db_id: database identifier
            code: generated code
        
        Returns:
            code after expanding paths
        """
        for file in self.catalog.files(db_id):
            for quote in ['"', "'"]:
                file_path = f'{quote}{file}{quote}'
                full_path = f'{quote}{self.tmp_dir}/{file}{quote}'
                code = code.replace(file_path, full_path)
        
        prefix = f"import os\nos.chdir('{self.tmp_dir}')\n"
        return prefix + code
    
    def _write_file(self, filename, code):
        """ Write code into file in temporary directory. 
        
        Args:
            db_id: database ID
            filename: name of code file
            code: write code into this file
            
        """
        file_path = f'{self.tmp_dir}/{filename}'
        with open(file_path, 'w') as file:
            file.write(code)


class PythonEngine(ExecutionEngine):
    """ Executes Python code. """
    
    def __init__(self, catalog):
        """ Initialize with database catalog and paths.
        
        Args:
            catalog: informs on database schema and file locations
        """
        super().__init__(catalog)
        self.python_path = os.environ['CODEXDB_PYTHON']
    
    def execute(self, db_id, code, timeout_s):
        """ Execute code written in specified language.
        
        Args:
            db_id: code references data in this database
            code: execute this code
            timeout_s: execution timeout in seconds
        
        Returns:
            Boolean success flag, output, execution statistics
        """
        self._clean()
        self._copy_db(db_id)
        start_s = time.time()
        success, output, stats = self._exec_python(db_id, code, timeout_s)
        total_s = time.time() - start_s
        stats['total_s'] = total_s
        return success, output, stats
    
    def _exec_python(self, db_id, code, timeout_s):
        """ Execute Python code and return generated output.
        
        Args:
            db_id: database identifier
            code: Python code to execute
            timeout_s: execution timeout in seconds
        
        Returns:
            Success flag, output, and execution statistics
        """
        filename = 'execute.py'
        code = self._expand_paths(db_id, code)
        self._write_file(filename, code)
        exe_path = f'{self.tmp_dir}/{filename}'
        cmd_parts = ['timeout', str(timeout_s), self.python_path, exe_path]
        sub_comp = subprocess.run(cmd_parts)
        success = False if sub_comp.returncode > 0 else True
        if not success:
            print(f'Python stdout: {sub_comp.stdout}')
            print(f'Python stderr: {sub_comp.stderr}')
            output = pd.DataFrame([[]])
        else:
            try:
                output = pd.read_csv(self.result_path)
            except:
                e = sys.exc_info()[0]
                print(f'Exception while reading result file: {e}')
                output = pd.DataFrame([[]])
        return success, output, {}


class SqliteEngine(ExecutionEngine):
    """ SQL execution engine using SQLite. """
    
    def __init__(self, catalog):
        """ Initialize with given catalog. 
        
        Args:
            catalog: information about database schemata
        """
        super().__init__(catalog)
    
    def execute(self, db_id, sql, timeout_s):
        """ Execute given SQL query. 
        
        Args:
            db_id: ID of database (in catalog)
            sql: SQL query to execute on database
            timeout_s: execution timeout in seconds
        
        Returns:
            Success flag, output, and execution statistics
        """
        self._prepare_db(db_id)
        return self._execute(db_id, sql, timeout_s)
    
    def _execute(self, db_id, sql, timeout_s):
        """ Execute given SQL query on specified database. 
        
        Args:
            db_id: ID of database in catalog
            sql: execute this SQL query
            timeout_s: execution timeout in seconds
        
        Returns:
            success flag, result, and execution statistics
        """
        db_dir = self.catalog.db_dir(db_id)
        db_path = f'{db_dir}/db.db'
        try:
            with sqlite3.connect(db_path) as connection:
                result = pd.read_sql(sql, connection)
                print(f'Query Result Info: {result.info()}')
                result.to_csv(self.result_path)
            return True, result, {}
        except Exception as e:
            print(f'Exception: {e}')
            return False, pd.DataFrame(), {}
    
    def _prepare_db(self, db_id):
        """ Prepare database for querying. 
        
        Args:
            db_id: database ID in catalog
        """
        db_dir = self.catalog.db_dir(db_id)
        db_path = f'{db_dir}/db.db'
        if os.path.exists(db_path):
            subprocess.run(['rm', db_path])
        with sqlite3.connect(db_path) as connection:
            schema = self.catalog.schema(db_id)
            tables = schema['table_names_original']
            for table in tables:
                file_name = self.catalog.file_name(table)
                table_path = f'{db_dir}/{file_name}'
                df = pd.read_csv(table_path)
                df.columns = df.columns.str.replace(' ', '_')
                df.to_sql(table, connection)