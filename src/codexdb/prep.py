'''
Created on Sep 19, 2021

@author: immanueltrummer
'''
import argparse
import collections
import json
import pandas as pd
import sqlite3

def get_db_path(spider_dir, db_id):
    """ Return path to SQLite database file. 
    
    Args:
        spider_dir: path to SPIDER benchmark
        db_id: database identifier
    
    Returns:
        path to SQLite database file
    """
    return f'{spider_dir}/database/{db_id}/{db_id}.sqlite'


def extract(spider_dir, db_json):
    """ Extract data from database into .csv files. 
    
    Args:
        spider_dir: path to SPIDER main directory
        db_json: JSON description of database
    """
    db_id = db_json['db_id']
    db_dir = f'{spider_dir}/database/{db_id}'
    db_path = f'{db_dir}/{db_id}.sqlite'
    print(f'Path to DB: {db_path}')
    with sqlite3.connect(db_path) as con:
        #con.text_factory = bytes
        con.text_factory = lambda b: b.decode(errors = 'ignore')
        for tbl in db_json['table_names_original']:
            query = f'select * from {tbl}'
            df = pd.read_sql_query(query, con)
            out_path = f'{db_dir}/{tbl}.csv'
            df.to_csv(out_path, index=False)


def get_result(spider_dir, query_json):
    """ Execute query and return result.
    
    Args:
        spider_dir: path to SPIDER benchmark
        query_json: describes query by JSON
    
    Returns:
        query result
    """
    db_id = query_json['db_id']
    db_path = get_db_path(spider_dir, db_id)
    sql = query_json['query']
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(sql)
        result = cur.fetchall()
    
    print(f'Query: {sql}; Result: {result}')
    return result


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('key', type=str, help='OpenAI Key')
    parser.add_argument('spider', type=str, help='Path to SPIDER benchmark')
    args = parser.parse_args()
        
    tables_path = f'{args.spider}/tables.json'
    db_to_s = {}
    with open(tables_path) as file:
        tables = json.load(file)
        nr_dbs = len(tables)
        for db_idx, db in enumerate(tables):
            db_id = db['db_id']
            db_to_s[db_id] = db
            print(f'Extracting {db_id} ({db_idx+1}/{nr_dbs})')
            extract(args.spider, db)
    db_path = f'{args.spider}/schemata.json'
    with open(db_path, 'w') as file:
        json.dump(db_to_s, file)
    
    for in_file in ['train_spider', 'dev']:
        db_to_q = collections.defaultdict(lambda:[])
        all_results = []
        train_path = f'{args.spider}/{in_file}.json'
        with open(train_path) as file:
            queries = json.load(file)
            nr_queries = len(queries)
            nr_valid = 0
            
            for q_idx, q_json in enumerate(queries):
                query = q_json['query']
                question = q_json['question']
                db_id = q_json['db_id']
                print(f'"{query}" on "{db_id}" ({q_idx+1}/{nr_queries})')
                
                db_to_q[db_id].append(q_json)
                try:
                    result = get_result(args.spider, q_json)
                    row = {
                        'db_id':db_id, 'question':question,
                        'query':query, 'results':result}
                    all_results.append(row)
                    nr_valid += 1
                except:
                    print(f'Invalid Query: {query} on {db_id}')
        
            print(f'Processed {nr_valid}/{nr_queries} queries')
            results_path = f'{args.spider}/results_{in_file}.json'
            with open(results_path, 'w') as file:
                json.dump(all_results, file)
        
        q_path = f'{args.spider}/{in_file}_queries.json'
        with open(q_path, 'w') as file:
            json.dump(db_to_q, file)