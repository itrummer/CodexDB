'''
Created on Oct 3, 2021

@author: immanueltrummer
'''
import os
import time

class ExecuteCode():
    """ Executes code in different languages. """
    
    def __init__(self, catalog):
        """ Initialize with database catalog and paths.
        
        Args:
            catalog: informs on database schema and file locations
        """
        self.catalog = catalog
        self.cpp_path = os.environ['CODEXDB_CPP']
        self.psql_path = os.environ['CODEXDB_PSQL']
        self.python_path = os.environ['CODEXDB_PYTHON']
        self.tmp_dir = os.environ['CODEXDB_TMP']
    
    def execute(self, db_id, code_lang, code):
        """ Execute code written in specified language.
        
        Args:
            db_id: code references data in this database
            code_lang: code is written in this language
            code: execute this code
        
        Returns:
            Boolean success flag, output, elapsed time in seconds
        """
        self._copy_db(db_id)
        start_s = time.time()
        if code_lang == 'bash':
            success, output = self._exec_bash(db_id, code)
        elif code_lang == 'cpp':
            success, output = self._exec_cpp(db_id, code)
        elif code_lang == 'python':
            success, output = self._exec_python(db_id, code)
        elif code_lang == 'pg_sql':
            success, output = self._exec_psql(db_id, code)
        elif code_lang == 'dummy':
            success, output = True, ''
        else:
            raise ValueError(f'Unsupported language: {code_lang}')
        total_s = time.time() - start_s
        return success, output, total_s
    
    def supported_langs(self):
        """ Returns supported languages as string list. """
        return ['bash', 'cpp', 'python', 'dummy']
    
    def _copy_db(self, db_id):
        """ Copies data to a temporary directory.
        
        Args:
            db_id: database ID
        """
        src_dir = self.catalog.db_dir(db_id)
        for tbl_file in self.catalog.files(db_id):
            cmd = f'sudo cp -r {src_dir}/{tbl_file} {self.tmp_dir}'
            os.system(cmd)
    
    def _exec_bash(self, db_id, code):
        """ Execute bash code.
        
        Args:
            db_id: database identifier
            code: execute this code
        
        Returns:
            Success flag and output of executed code
        """
        filename = 'execute.sh'
        code = self._expand_paths(db_id, code)
        self._write_file(filename, code)
        sh_path = f'{self.tmp_dir}/execute.sh'
        os.system(f'chmod +x {sh_path}')
        if os.system(f'{sh_path} &> {self.tmp_dir}/bout.txt') > 0:
            return False, ''
        with open(f'{self.tmp_dir}/bout.txt') as file:
            return True, file.read()
    
    def _exec_cpp(self, db_id, code):
        """ Execute C++ code.
        
        Args:
            db_id: database identifier
            code: C++ code to execute
        
        Returns:
            Success flag and output of executed code
        """
        filename = 'execute.cpp'
        code = self._expand_paths(db_id, code)
        self._write_file(filename, code)
        src_path = f'{self.tmp_dir}/{filename}'
        exe_path = f'{self.tmp_dir}/execute.out'
        comp_cmd = f'{self.cpp_path} {src_path} -o {exe_path}'
        exe_cmd = f'{exe_path} &> {self.tmp_dir}/cout.txt'
        if os.system(comp_cmd) > 0 or os.system(exe_cmd) > 0:
            return False, ''
        with open(f'{self.tmp_dir}/cout.txt') as file:
            return True, file.read()
    
    def _exec_psql(self, db_id, code):
        """ Execute Postgres SQL query. 
        
        Args:
            db_id: database identifier
            code: SQL query to execute
        
        Returns:
            Success flag and output of generated code
        """
        self._write_file('sql.txt', code)
        sql_path = f'{self.tmp_dir}/sql.txt'
        out_path = f'{self.tmp_dir}/output.txt'
        if os.system(f'{self.psql_path} -f {sql_path} {db_id} > {out_path}'):
            return False, ''
        with open(out_path) as file:
            return True, file.read()
    
    def _exec_python(self, db_id, code):
        """ Execute Python code and return generated output.
        
        Args:
            db_id: database identifier
            code: Python code to execute
        
        Returns:
            Success flag and output generated when executing code
        """
        filename = 'execute.py'
        db_dir = self.catalog.db_dir(db_id)
        code = self._expand_paths(db_id, code)
        self._write_file(filename, code)
        pyt_cmd = f'PYTHONPATH={self.tmp_dir} {self.python_path}'
        exe_file = f'{db_dir}/{filename}'
        out_file = f'{db_dir}/pout.txt'
        if os.system(
            f'{pyt_cmd} {exe_file} &> {out_file}') > 0:
            return False, ''
        with open(f'{out_file}') as file:
            return True, file.read()
    
    def _expand_paths(self, db_id, code):
        """ Expand relative paths to data files in code.
        
        Args:
            db_id: database identifier
            code: generated code
        
        Returns:
            code after expanding paths
        """
        for file in self.catalog.files(db_id):
            full_path = f'{self.tmp_dir}/{file}'
            code = code.replace(file, full_path)
        return code
    
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