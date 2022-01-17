'''
Created on Dec 5, 2021

@author: immanueltrummer
'''
import argparse
import codexdb.catalog
import codexdb.deprecated.code_gen
import codexdb.engine
import codexdb.learn
import json
import openai
import os
import sys

from stable_baselines3 import DQN
from stable_baselines3 import A2C
from stable_baselines3.common.evaluation import evaluate_policy

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('key', type=str, help='Key for OpenAI Codex access')
    parser.add_argument('data_dir', type=str, help='Data directory')
    parser.add_argument('test_path', type=str, help='Path to test case file')
    parser.add_argument('from_lang', type=str, help='Source language (NL vs SQL)')
    parser.add_argument('config', type=str, help='Path to configuration file')
    parser.add_argument('nr_steps', type=int, help='The number of learning steps')
    parser.add_argument('model_in', type=str, help='Path to input model')
    parser.add_argument('log_path', type=str, help='Path to logging file if any')
    parser.add_argument('model_out', type=str, help='Path to output model')
    args = parser.parse_args()
    
    os.environ['KMP_DUPLICATE_LIB_OK']='True'
    openai.api_key = args.key
    from_lang = args.from_lang.lower()
    if from_lang not in ['nl', 'pg_sql']:
        sys.exit(f'Unknown source language: {from_lang}')
    log_path = None
    if args.log_path:
        log_path = args.log_path
    
    with open(args.config) as file:
        prompts = json.load(file)
    code_gen = codexdb.deprecated.code_gen.CodeGenerator(prompts)
    catalog = codexdb.catalog.DbCatalog(args.data_dir)
    engine = codexdb.engine.ExecuteCode(catalog)
    
    with open(args.test_path) as file:
        test_cases = json.load(file)
        env = codexdb.learn.PromptEnv(
            catalog, prompts, from_lang, 
            'pg_sql', test_cases, 
            log_path=log_path)
        
        if args.model_in:
            print(f'Loading model from {args.model_in} ...')
            model = A2C.load(args.model_in, env, verbose=1)
        else:
            print('Initializing new model ...')
            model = A2C('MlpPolicy', env, verbose=1)
        
        model.learn(total_timesteps=args.nr_steps)
        if args.model_out:
            model.save(args.model_out)