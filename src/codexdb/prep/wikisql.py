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


def sql_name(raw_name):
    """ Cleaned column name.
    
    Args:
        raw_name: raw column name
    
    Returns:
        cleaned name suitable for SQL column
    """
    sql_name = raw_name
    for to_replace in [' ', '\\', '/', '(', ')', '.']:
        sql_name = sql_name.replace(to_replace, '_')
    return sql_name.strip()


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
            query = f'select * from {table_name}'
            df = pd.read_sql_query(query, connection)
            raw_columns = table['header']
            df.columns = [sql_name(c) for c in raw_columns]
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
        columns = [sql_name(h) for h in table['header']]
        idx_cols = [(0, c) for c in columns]
        schema = {}
        schema['table_names_original'] = ['Data']
        schema['column_names_original'] = idx_cols
        db_id = table['id']
        schema['db_id'] = db_id
        schemata[db_id] = schema
    
    return schemata


def extract_tests(source_dir, split, target_dir):
    """ Extract test cases from file.
    
    Args:
        source_dir: source directory of WikiSQL
        split: extract queries from this split
        target_dir: target directory for data
    
    Returns:
        list of extracted test cases
    """
    in_path = f'{source_dir}/{split}.jsonl'
    with jsonlines.open(in_path) as file:
        out_cases = []
        for in_case in file:
            out_case = {}
            db_id = in_case['table_id']
            out_case['db_id'] = db_id
            csv_path = f'{target_dir}/database/{db_id}/Data.csv'
            db_path = '/tmp/tmp.db'
            df = pd.read_csv(csv_path)
            with sqlite3.connect(db_path) as connection:
                cursor = connection.cursor()
                cursor.execute('drop table if exists Data')
                connection.commit()
                df.to_sql('Data', connection, index=False)
                # for row in cursor.execute('select * from Data'):
                    # print(row)
                # for row in cursor.execute('select sql, tbl_name from sqlite_master'):
                    # print(row)

            engine = lib.dbengine.DBEngine(db_path)
            query_template = lib.query.Query.from_dict(in_case['sql'], True)
            query, raw_result = engine.execute_query(
                'Data', query_template, lower=True)
            # print(f'Query: {query}')
            out_case['question'] = in_case['question']
            out_case['query'] = str(query)
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
    
    for split in ['dev', 'test', 'train']:
        print(f'Processing {split} split ...')
        
        extract_data(args.source_dir, split, args.target_dir)
        split_schemata = extract_schemata(args.source_dir, split)
        schemata = {**schemata, **split_schemata}
        
        tests = extract_tests(args.source_dir, split, args.target_dir)
        test_out = f'{args.source_dir}/results_{split}.json'
        with open(test_out, 'w') as file:
            json.dump(tests, file)
    
    schema_out = f'{args.target_dir}/schemata.json'
    with open(schema_out, 'w') as file:
        json.dump(schemata, file)