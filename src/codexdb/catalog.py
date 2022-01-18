'''
Created on Oct 5, 2021

@author: immanueltrummer
'''
import json

class DbCatalog():
    """ Information over all databases in database directory. """
    
    def __init__(self, data_dir):
        """ Initialize for given database directory. 
        
        Args:
            data_dir: contains databases and schemata
        """
        self.data_dir = data_dir
        self.schema_path = f'{data_dir}/schemata.json'
        with open(self.schema_path) as file:
            self.schemata = json.load(file)
        
    def db_dir(self, db_id):
        """ Returns directory storing specific database.
        
        Args:
            db_id: name of database
        
        Returns:
            path of directory containing database
        """
        return f'{self.data_dir}/database/{db_id}'
    
    def file(self, table):
        """ Returns name of file storing table data.
        
        Args:
            table: name of table
        
        Returns:
            name of file storing data
        """
        return f'{table}.csv'
    
    def files(self, db_id):
        """ Returns names of files containing database tables.
        
        Args:
            db_id: unique database identifier
        
        Returns:
            list of files associated with database tables
        """
        tables = self.schema(db_id)['table_names_original']
        return [self.file(t) for t in tables]
    
    def schema(self, db_id):
        """ Returns description of database schema.
        
        Args:
            db_id: unique name of database
        
        Returns:
            JSON object describing database schema
        """
        return self.schemata[db_id]