'''
Created on Sep 19, 2021

@author: immanueltrummer
'''
import argparse
import json
import openai

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('key', type=str, help='OpenAI Key')
    parser.add_argument('spider', type=str, help='Path to SPIDER benchmark')
    args = parser.parse_args()
    
    with open(args.spider) as file:
        tables = json.load(file)
        for db in tables:
            print(db['db_id'])
    
    # openai.api_key = args.key
    # response = openai.Completion.create(
        # engine='davinci-codex', 
        # prompt='Count from one to ten in Python', 
        # max_tokens=20,
        # temperature=0)
        #
    # print(response)