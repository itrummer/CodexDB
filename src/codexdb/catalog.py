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
        self.table_to_file = {}
    
    def assign_file(self, db_id, table, file_name):
        """ Assign file to given table in given database.
        
        Args:
            db_id: table is in this database
            table: assign file containing data for this table
            file_name: name of file containing data
        """
        self.table_to_file[(db_id, table)] = file_name
        
    def db_dir(self, db_id):
        """ Returns directory storing specific database.
        
        Args:
            db_id: name of database
        
        Returns:
            path of directory containing database
        """
        return f'{self.data_dir}/database/{db_id}'
    
    def db_ids(self):
        """ Returns IDs of available databases.
        
        Returns:
            list with database IDs
        """
        return self.schemata.keys()
    
    def file_name(self, db_id, table):
        """ Returns name of file storing table data.
        
        Args:
            db_id: ID of database
            table: name of table
        
        Returns:
            name of file storing data
        """
        key = (db_id, table)
        default = f'{table}.csv'
        return self.table_to_file.get(key, default)
    
    def file_path(self, db_id, table):
        """ Returns path to file containing data for table.
        
        Args:
            db_id: search table in this database
            table: name of table
        
        Returns:
            path to file containing data for table
        """
        db_dir = self.db_dir(db_id)
        file_name = self.file_name(db_id, table)
        return f'{db_dir}/{file_name}'

    def files(self, db_id):
        """ Returns names of files containing database tables.
        
        Args:
            db_id: unique database identifier
        
        Returns:
            list of files associated with database tables
        """
        tables = self.schema(db_id)['table_names_original']
        return [self.file_name(db_id, t) for t in tables]
    
    def schema(self, db_id):
        """ Returns description of database schema.
        
        Args:
            db_id: unique name of database
        
        Returns:
            JSON object describing database schema
        """
        return self.schemata[db_id]