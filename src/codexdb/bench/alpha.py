'''
Created on Nov 23, 2024

@author: immanueltrummer
'''
import argparse
import json
import pandas

from pathlib import Path


def get_inputs(db_dir, db_id):
    """ Extracts all .csv files in directory. 
    
    Args:
        db_dir: directory containing databases.
        db_id: name of sub-directory.
    
    Returns:
        Dictionary mapping file names to data frames.
    """
    name2df = {}
    db_path = Path(db_dir) / Path(db_id)
    for csv_path in db_path.glob('*.csv'):
        file_name = csv_path.name
        csv_file = pandas.read_csv(csv_path)
        name2df[file_name] = csv_file
    
    return name2df


def table_to_JSON(table_name, table_df):
    """ Transforms a named data frame into a JSON representation.
    
    Args:
        table_name: name of the table.
        table_df: data frame.
    
    Returns:
        JSON dictionary with table details.
    """
    return {
        'name':table_name,
        'headers':table_df.columns.values.tolist(),
        'rows':table_df.values.tolist()
    }


def make_alpha_test(test_name, db_description, query, results, modification):
    """ Create test case for AlphaCodium.
    
    Args:
        test_name: name of the test case.
        db_description: list of JSON dictionaries describing tables.
        query: the query to process.
        results: results from reference SQL engine.
        modification: instructions on code customization.
    
    Returns:
        JSON object suitable as input for AlphaChromium.
    """
    task_parts = []
    task_parts += [f'Write Python code implementing the SQL query "{query}".']
    task_parts += ['The input is a database, represented as a list of Python dictionaries.']
    task_parts += ['Each dictionary describes one table with fields "name", "headers", and "rows".']
    task_parts += ['The "headers" field contains a list of column names.']
    task_parts += ['The "rows" field contains a list of rows where each row is a list of values.']
    task_parts += ['The output is the query result: a list of rows where each row is a list of values.']
    task_parts += ['Tables:']
    for table_info in db_description:
        table_name = table_info['name']
        table_headers = table_info['headers']
        task_parts += [f'{table_name} columns: {table_headers}']
    task = '\n'.join(task_parts)
    alpha_test = {
        'name':test_name,
        'description':task,
        'public_tests':{
            'input':[str(db_description)],
            'output':[str(results)]
            }
        }
    return alpha_test


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('db_dir', type=str, help='Path to databases')
    parser.add_argument('test_path', type=str, help='Path to test cases')
    parser.add_argument('modification', type=str, help='Code modification')
    args = parser.parse_args()
    
    with open(args.test_path) as file:
        test_cases = json.load(file)

    for i in range(0, 200, 2):
        test_case = test_cases[i]

        db_id = test_case['db_id']
        inputs = get_inputs(args.db_dir, db_id)
        db_description = []
        for table_name, table_df in inputs.items():
            db_description += [table_to_JSON(table_name, table_df)]
        
        query = test_case['query']
        question = test_case['question']
        results = test_case['results']
        test_name = f'CodingTest{i}'
        alpha_test = make_alpha_test(
            test_name, db_description, query, 
            results, args.modification)
        
        with open(f'{test_name}.json', 'w') as file:
            json.dump(alpha_test, file)