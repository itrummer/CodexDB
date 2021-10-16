'''
Created on Oct 3, 2021

@author: immanueltrummer
'''
import os
import time

class ExecuteCode():
    """ Executes code in different languages. """
    
    def __init__(self, catalog):
        """ Initialize with database catalog.
        
        Args:
            catalog: informs on database schema and file locations
        """
        self.catalog = catalog
    
    def execute(self, db_id, code_lang, code):
        """ Execute code written in specified language.
        
        Args:
            db_id: code references data in this database
            code_lang: code is written in this language
            code: execute this code
        
        Returns:
            Boolean success flag, output, elapsed time in seconds
        """
        start_s = time.time()
        if code_lang == 'bash':
            success, output = self._exec_bash(db_id, code)
        elif code_lang == 'cpp':
            success, output = self._exec_cpp(db_id, code)
        elif code_lang == 'python':
            success, output = self._exec_python(db_id, code)
        elif code_lang == 'dummy':
            success, output = True, ''
        else:
            raise ValueError(f'Unsupported language: {code_lang}')
        total_s = time.time() - start_s
        return success, output, total_s
    
    def supported_langs(self):
        """ Returns supported languages as string list. """
        return ['bash', 'cpp', 'python', 'dummy']
    
    def _exec_bash(self, db_id, code):
        """ Execute bash code.
        
        Args:
            db_id: database identifier
            code: execute this code
        
        Returns:
            Output of executed code
        """
        filename = 'execute.sh'
        code = self._expand_paths(db_id, code)
        self._write_file(db_id, filename, code)
        db_dir = self.catalog.db_dir(db_id)
        os.system(f'chmod +x {db_dir}/execute.sh')
        if os.system(f'{db_dir}/execute.sh &> {db_dir}/bout.txt') > 0:
            return False, ''
        with open(f'{db_dir}/bout.txt') as file:
            return True, file.read()
    
    def _exec_cpp(self, db_id, code):
        """ Execute C++ code.
        
        Args:
            db_id: database identifier
            code: C++ code to execute
        
        Returns:
            output of executed code
        """
        filename = 'execute.cpp'
        code = self._expand_paths(db_id, code)
        self._write_file(db_id, filename, code)
        db_dir = self.catalog.db_dir(db_id)
        exefile = 'execute.out'
        if os.system(f'g++ {db_dir}/{filename} -o {db_dir}/{exefile}') > 0 or \
            os.system(f'{db_dir}/{exefile} &> {db_dir}/cout.txt') > 0:
            return False, ''
        with open(f'{db_dir}/cout.txt') as file:
            return True, file.read()
    
    def _exec_python(self, db_id, code):
        """ Execute Python code and return generated output.
        
        Args:
            db_id: database identifier
            code: Python code to execute
        
        Returns:
            output generated when executing code
        """
        filename = 'execute.py'
        db_dir = self.catalog.db_dir(db_id)
        code = self._expand_paths(db_id, code)
        self._write_file(db_id, filename, code)
        python_path = f'PYTHONPATH={db_dir}'
        python_exe = '/opt/homebrew/anaconda3/envs/literate/bin/python'
        exe_file = f'{db_dir}/{filename}'
        out_file = f'{db_dir}/pout.txt'
        if os.system(
            f'{python_path} {python_exe} {exe_file} &> {out_file}') > 0:
            return False, ''
        with open(f'{out_file}') as file:
            return file.read()
    
    def _expand_paths(self, db_id, code):
        """ Expand relative paths to data files in code.
        
        Args:
            db_id: database identifier
            code: generated code
        
        Returns:
            code after expanding paths
        """
        db_dir = self.catalog.db_dir(db_id)
        for file in self.catalog.files(db_id):
            full_path = f'{db_dir}/{file}'
            code = code.replace(file, full_path)
        return code
    
    def _write_file(self, db_id, filename, code):
        """ Write code into file in database directory. 
        
        Args:
            db_id: database ID
            filename: name of code file
            code: write code into this file
            
        """
        file_path = f'{self.catalog.db_dir(db_id)}/{filename}'
        with open(file_path, 'w') as file:
            file.write(code)