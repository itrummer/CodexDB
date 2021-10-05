'''
Created on Oct 3, 2021

@author: immanueltrummer
'''
import os

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
            output generated when executing code
        """
        if code_lang == 'bash':
            return self._exec_bash(db_id, code)
        elif code_lang == 'cpp':
            return self._exec_cpp(db_id, code)
        elif code_lang == 'python':
            return self._exec_python(db_id, code)
        else:
            raise ValueError(f'Unsupported language: {code_lang}')
    
    def _exec_bash(self, db_id, code):
        """ Execute bash code.
        
        Args:
            db_id: database identifier
            code: execute this code
        
        Returns:
            Output of executed code
        """
        filename = 'execute.sh'
        self._write_file(db_id, filename, code)
        db_dir = self.catalog.db_dir(db_id)
        os.system(f'chmod {db_dir}/execute.sh +x')
        os.system(f'{db_dir}/execute.sh &> bout.txt')
        with open(f'{db_dir}/bout.txt') as file:
            return file.read()
    
    def _exec_cpp(self, db_id, code):
        """ Execute C++ code.
        
        Args:
            db_id: database identifier
            code: C++ code to execute
        
        Returns:
            output of executed code
        """
        filename = 'execute.cpp'
        self._write_file(db_id, filename, code)
        db_dir = self.catalog.db_dir(db_id)
        exefile = 'execute.out'
        os.system(f'gpp {db_dir}/{filename} -o {db_dir}/{exefile}')
        os.system(f'{db_dir}/{exefile} &> output.txt')
        with open(f'{db_dir}/output.txt') as file:
            return file.read()
    
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
        for file in self.catalog.files(db_id):
            full_path = f'{db_dir}/{file}'
            code = code.replace(file, full_path)
        self._write_file(db_id, filename, code)
        python_path = f'PYTHONPATH={db_dir}'
        python_exe = '/opt/homebrew/anaconda3/envs/literate/bin/python'
        exe_file = f'{db_dir}/{filename}'
        out_file = f'{db_dir}/pout.txt'
        os.system(f'{python_path} {python_exe} {exe_file} &> {out_file}')
        with open(f'{out_file}') as file:
            return file.read()
    
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