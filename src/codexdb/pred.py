'''
Created on Sep 20, 2021

@author: immanueltrummer
'''
import argparse
import json
import openai
import pandas as pd




if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('key', type=str, help='OpenAI API access key')
    parser.add_argument('spider', type=str, help='SPIDER benchmark directory')
    args = parser.parse_args()
    
    openai.api_key = args.key
    id_to_schema = get_schemata(args.spider)
    q_path = f'{args.spider}/all_results.csv'
    queries = pd.read_csv(q_path, sep='\t')
    
    for row_idx, row in queries.iterrows():
        db_id = row['db_id']
        db_info = id_to_schema[db_id]
        print(row['question'])
        print(db_info)
        break