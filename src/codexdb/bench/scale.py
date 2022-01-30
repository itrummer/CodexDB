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
import pandas as pd
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
        code referencing scaled data files, byte sizes, #rows
    """
    scaled_code = code
    schema = catalog.schema(db_id)
    tables = schema['table_names_original']
    table_byte_sizes = []
    table_nr_rows = []
    for table in tables:
        original_file = catalog.file_name(db_id, table)
        original_path = catalog.file_path(db_id, table)
        scaled_file = f'xxl_{original_file}'
        catalog.assign_file(db_id, table, scaled_file)
        scaled_path = catalog.file_path(db_id, table)
        scale_data(original_path, factor, scaled_path)
        scaled_code = scaled_code.replace(original_file, scaled_file)
        byte_size = os.path.getsize(scaled_path)
        nr_rows = (1 for l in open(scaled_path))
        table_byte_sizes += [byte_size]
        table_nr_rows += [nr_rows]
    return scaled_code, table_byte_sizes, table_nr_rows

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
        performance and size statistics
    """
    print('Starting data scaling ...')
    scaled_code, byte_sizes, row_sizes = scale_tables(
        catalog, db_id, factor, code)
    print('Scaling finished - starting measurements ...')
    start_s = time.time()
    engine.execute(db_id, scaled_code, timeout_s)
    total_s = time.time() - start_s
    print('Execution finished - unscaling tables ...')
    unscale_tables(catalog, db_id)
    return {'total_s':total_s, 'byte_sizes':byte_sizes, 'row_sizes':row_sizes}


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('data_dir', type=str, help='Data directory')
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
    factors = [10, 1000, 100000]
    nr_factors = len(factors)
    
    times_path = 'times.csv'
    results_path = 'stats.json'
    if os.path.exists(times_path):
        raise ValueError(f'Error - {times_path} exists!')
    if os.path.exists(results_path):
        raise ValueError(f'Error - {results_path} exists!')
    
    results = []
    for test_case_id in range(nr_tests):
        test_case_key = str(test_case_id)
        tries = test_cases[test_case_key]
        test_case = tries[-1]
        for factor in factors:
            print(f'Treating test case {test_case_id}, factor {factor}')
            if test_case['similarity'] == 1.0:
                db_id = test_case['schema']['db_id']
                code = get_code(args.language, test_case)
                stats = test_performance(
                    engine, db_id, factor, 
                    code, args.timeout_s)
                stats['scaling_factor'] = factor
                results += [stats]
            else:
                results += [{'total_s':-1, 'scaling_factor':factor}]
    
    by_factors = []
    for idx, factor in enumerate(factors):
        factor_times = [r['total_s'] for r in results[idx::nr_factors]]
        by_factors.append(factor_times)
    times_df = pd.DataFrame(by_factors)
    times_df.columns = factors
    times_df.to_csv(times_path, index=False)
    print(times_df)

    with open(results_path, 'w') as file:
        json.dump(results, file)