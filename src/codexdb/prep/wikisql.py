'''
Created on Jan 15, 2022

@author: immanueltrummer
'''
import argparse
import json
import jsonlines
import lib.dbengine
import lib.query
import os
import pandas as pd
import sqlite3

def extract_data(source_dir, split, target_dir):
    """ Extract data from given split and store on hard disk.
    
    Args:
        source_dir: source data directory
        split: treat this split of data
        target_dir: write into this directory
    """
    tbl_path = f'{source_dir}/{split}.tables.jsonl'
    db_path = f'{source_dir}/{split}.db'
    
    with jsonlines.open(tbl_path) as file:
        tables = list(file)
    
    with sqlite3.connect(db_path) as connection:
        for table in tables:
            table_id = table['id']
            table_name = 'table_' + table_id.replace('-','_')
            columns = table['header']
            query = f'select * from {table_name}'
            df = pd.read_sql_query(query, connection)
            df.columns = columns
            out_dir = f'{target_dir}/database/{table_id}'
            os.makedirs(out_dir, exist_ok=True)
            out_path = f'{out_dir}/Data.csv'
            df.to_csv(out_path, index=False)


def extract_schemata(source_dir, split):
    """ Extract table schemata from given file.
    
    Args:
        source_dir: source directory for WikiSQL benchmark
        split: treat this split of data
    
    Returns:
        schemata of all tables in database
    """
    tbl_path = f'{source_dir}/{split}.tables.jsonl'
    with jsonlines.open(tbl_path) as file:
        tables = list(file)
    
    schemata = {}
    for table in tables:
        columns = table['header']
        idx_cols = [(0, c) for c in columns]
        schema = {}
        schema['table_names_original'] = ['Data']
        schema['column_names_original'] = idx_cols
        db_id = table['id']
        schema['db_id'] = db_id
        schemata[db_id] = schema
    
    return schemata


def extract_tests(engine, source_dir, split):
    """ Extract test cases from file.
    
    Args:
        engine: database engine for processing queries
        source_dir: source directory of WikiSQL
        split: extract queries from this split
    
    Returns:
        list of extracted test cases
    """
    in_path = f'{source_dir}/{split}.jsonl'
    with jsonlines.open(in_path) as file:
        out_cases = []
        for in_case in file:
            out_case = {}
            table_id = in_case['table_id']
            out_case['db_id'] = table_id
            out_case['question'] = in_case['question']
            query = lib.query.Query.from_dict(in_case['sql'], True)
            out_case['query'] = str(query)
            raw_result = engine.execute_query(table_id, query, lower=True)
            result = [[r] for r in raw_result if r is not None]
            out_case['results'] = result
            out_cases.append(out_case)

    return out_cases

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('source_dir', type=str, help='Path of WikiSQL directory')
    parser.add_argument('target_dir', type=str, help='Write test cases here')
    args = parser.parse_args()
    
    schemata = {}
    test_cases = []
    
    for split in ['train', 'dev', 'test']:
        print(f'Processing {split} split ...')
        
        extract_data(args.source_dir, split, args.target_dir)
        split_schemata = extract_schemata(args.source_dir, split)
        schemata = {**schemata, **split_schemata}
        
        db_file = f'{args.source_dir}/{split}.db'
        engine = lib.dbengine.DBEngine(db_file)
        tests = extract_tests(engine, args.source_dir, split)
        test_out = f'{args.source_dir}/results_{split}.json'
        with open(test_out, 'w') as file:
            json.dump(tests, file)
    
    schema_out = f'{args.target_dir}/schemata.json'
    with open(schema_out, 'w') as file:
        json.dump(schemata, file)