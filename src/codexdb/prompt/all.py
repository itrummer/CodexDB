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
    
    def generate(self, db_id, question):
        """ Generates prompt describing database and question.
        
        Args:
            db_id: database ID
            question: translate into code
        
        Returns:
            prompt initiating code generation
        """
        