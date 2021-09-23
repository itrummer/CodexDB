'''
Created on Sep 20, 2021

@author: immanueltrummer
'''
import codexdb.prompt.data

class AllPrompt():
    """ Generates prompt describing query and data. """
    
    def __init__(self, spider_dir):
        """ Initializes for given benchmark repository.
        
        Args:
            spider_dir: path of benchmark directory
        """
        self.db_prompt = codexdb.prompt.data.DbPrompt(spider_dir)
    
    def data_frame(self, db_id, question):
        """ Generates prompt loading data frames and describing query.
        
        Args:
            db_id: database ID
            question: translate into code
        
        Returns:
            prompt initiating code generation
        """
        p_parts = []
        p_parts.append('import pandas as pd\n')
        p_parts.append(self.db_prompt.load_data(db_id))
        q_requoted = question.replace("'", '"')
        p_parts.append(f"\n# {q_requoted}")
        p_parts.append(f"\nprint('{q_requoted}')")
        p_parts.append('\n')
        return ''.join(p_parts)
    
    def function_prompt(self, db_id, question):
        """ Generates a function to complete to answer the query.
        
        Args:
            db_id: database identifier
            question: question to answer
        
        Returns:
            start of function answering query
        """
        p_parts = []
        p_parts.append(self.db_prompt.table_signature(db_id))
        p_parts.append(f'\n  """ {question}\n')
        p_parts.append(self.db_prompt.schema_comment(db_id))
        p_parts.append(f'\n\n  Returns:\n    {question}')
        p_parts.append('\n  """')
        return ''.join(p_parts)