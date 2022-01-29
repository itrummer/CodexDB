'''
Created on Jan 29, 2022

@author: immanueltrummer
'''
import argparse
import codexdb.catalog
import codexdb.engine
import json
import math
import os
import time

def get_code(language, test_case):
    """ Extract code in specified language from test case.
    
    Args:
        language: extract code in this language from case
        test_case: test case containing code to execute
    
    Returns:
        code in specified language extracted from test case
    """
    if language == 'python':
        return test_case['code']
    elif language == 'sql':
        return test_case['query']
    else:
        raise ValueError(f'Unknown language: {language}')

def get_engine(language):
    """ Returns processing engine for given language.
    
    Args:
        language: create engine processing code in this language
    
    Returns:
        an engine that can process the given language
    """
    if language == 'python':
        return codexdb.engine.PythonEngine(catalog)
    elif language == 'sql':
        return codexdb.engine.SqliteEngine(catalog)
    else:
        raise ValueError(f'Unknown implementation language: {args.language}!')

def scale_data(source_path, factor, target_path):
    """ Duplicates rows in source file by given factor.
    
    Args:
        source_path: read data from this file
        factor: duplicate rows by this factor
        target_path: write scaled data here
    """
    os.system(f'cp {source_path} /tmp/scaled1')
    nr_iterations = math.ceil(math.log(factor, 2))
    for i in range(nr_iterations):
        print(f'Doubling rows - iteration {i} ...')
        # Double the number of rows (without header)
        os.system(f'cat /tmp/scaled1 > /tmp/scaled2')
        os.system(f'tail -n +2 /tmp/scaled1 >> /tmp/scaled2')
        os.system('cp /tmp/scaled2 /tmp/scaled1')
    os.system(f'cp /tmp/scaled1 {target_path}')

def scale_tables(catalog, db_id, factor, code):
    """ Scale up data size of tables in database by given factor.
    
    Args:
        catalog: contains information on database schema
        db_id: scale up tables of this database
        factor: scale up data size by approximately this factor
        code: code referencing original data files
    
    Returns:
        code referencing scaled data files
    """
    scaled_code = code
    schema = catalog.schema(db_id)
    tables = schema['table_names_original']
    for table in tables:
        original_file = catalog.file_name(db_id, table)
        original_path = catalog.file_path(db_id, table)
        scaled_file = f'xxl_{original_file}'
        catalog.assign_file(db_id, table, scaled_file)
        scaled_path = catalog.file_path(db_id, table)
        scale_data(original_path, factor, scaled_path)
        scaled_code = scaled_code.replace(original_file, scaled_file)
    return scaled_code

def unscale_tables(catalog, db_id):
    """ Replace scaled tables by the original. 
    
    Args:
        catalog: information on the database schema
        db_id: unscale all tables in this database
    """
    schema = catalog.schema(db_id)
    tables = schema['table_names_original']
    for table in tables:
        key = (db_id, table)
        del catalog.table_to_file[key]

def test_performance(engine, db_id, factor, code, timeout_s):
    """ Measure performance when processing code on given engine.
    
    Args:
        engine: use this engine for code processing
        db_id: execute code on this database
        factor: scale number of rows in tables by this factor
        code: measure performance when executing this code
        timeout_s: timeout in seconds for each execution
    
    Returns:
        performance statistics
    """
    print('Starting data scaling ...')
    scaled_code = scale_tables(catalog, db_id, factor, code)
    print('Scaling finished - starting measurements ...')
    start_s = time.time()
    engine.execute(db_id, scaled_code, timeout_s)
    total_s = time.time() - start_s
    print('Execution finished - unscaling tables ...')
    unscale_tables(catalog, db_id)
    return {'total_s':total_s}


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('data_dir', type=str, help='Data directory')
    parser.add_argument('factor', type=int, help='Scale data by this factor')
    parser.add_argument('language', type=str, help='Implementation language')
    parser.add_argument('test_path', type=str, help='Path to file with tests')
    parser.add_argument('nr_tests', type=int, help='How many test cases')
    parser.add_argument('timeout_s', type=int, help='Timeout in seconds')
    args = parser.parse_args()
    
    catalog = codexdb.catalog.DbCatalog(args.data_dir)
    with open(args.test_path) as file:
        test_cases = json.load(file)
    engine = get_engine(args.language)
    
    nr_all_tests = len(test_cases)
    nr_tests = min(args.nr_tests, nr_all_tests)
    
    results = []
    for test_case_id in range(nr_tests):
        test_case_key = str(test_case_id)
        tries = test_cases[test_case_key]
        test_case = tries[-1]
        if test_case['similarity'] == 1.0:
            db_id = test_case['schema']['db_id']
            code = get_code(args.language, test_case)
            stats = test_performance(
                engine, db_id, args.factor, 
                code, args.timeout_s)
            results += [stats]
    
    times = [str(s['total_s']) for s in results]
    print('\n'.join(times))
    
    with open('stats.json', 'w') as file:
        json.dump(results, file)