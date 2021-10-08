'''
Created on Oct 3, 2021

@author: immanueltrummer
'''
import argparse
import json
import openai
import sys
from codexdb.catalog import DbCatalog
from codexdb.code import CodeGenerator
from codexdb.engine import ExecuteCode
from codexdb.learn import PromptEnv
import os
from stable_baselines3 import DQN
from stable_baselines3 import A2C
from stable_baselines3.common.evaluation import evaluate_policy


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('key', type=str, help='Key for OpenAI Codex access')
    parser.add_argument('data_dir', type=str, help='Data directory')
    parser.add_argument('db', type=str, help='Name of database')
    parser.add_argument('from_lang', type=str, help='Source language (NL vs SQL)')
    parser.add_argument('to_lang', type=str, help='Admissible target language(s)')
    parser.add_argument('config', type=str, help='Path to configuration file')
    args = parser.parse_args()
    
    os.environ['KMP_DUPLICATE_LIB_OK']='True'
    openai.api_key = args.key
    from_lang = args.from_lang.lower()
    if from_lang not in ['nl', 'pg_sql']:
        sys.exit(f'Unknown source language: {from_lang}')
    
    with open(args.config) as file:
        prompts = json.load(file)
    code_gen = CodeGenerator(prompts)
    catalog = DbCatalog(args.data_dir)
    engine = ExecuteCode(catalog)
    
    cmd = ''
    print('CodexDB ready - enter your queries:')
    while not (cmd == 'quit'):
        cmd = input()
        print(f'Processing command "{cmd}" ...')
        if not (cmd == 'quit'):
            schema = catalog.schema(args.db)
            files = catalog.files(args.db)
            env = PromptEnv(
                catalog, args.db, prompts, 
                from_lang, 'pg_sql', [cmd], 10)
            model = A2C('MlpPolicy', env, verbose=1)
            model.learn(total_timesteps=int(50))
            #
            # tactics_p = [0, 0, 0, 0, 1, 0, 1]
            # code = code_gen.generate(
                # 'query', schema, files, args.from_lang, 
                # args.to_lang, cmd, tactics_p)
            # print(code)
            # result = engine.execute(
                # args.db, args.to_lang, code)
            # print(result)