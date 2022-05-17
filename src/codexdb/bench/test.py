'''
Created on May 17, 2022

@author: immanueltrummer
'''
import argparse
import codexdb.solve
import json

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('ai_key', type=str, help='Key for OpenAI access')
    parser.add_argument('config_path', type=str, help='Configuration file path')
    args = parser.parse_args()
    
    with open(args.config_path) as file:
        config = json.load(file)
    
    data_dir = config['data_dir']
    sample_path = config['sample_path']
    test_path = config['test_path']
    nr_tests = config['nr_tests']
    model_id = config['model_id']
    prompt_style = config['prompt_style']
    nr_samples = config['nr_samples']
    id_case = config['id_case']
    mod_start = config['mod_start']
    mod_between = config['mod_between']
    mod_end = config['mod_end']
    nr_retries = config['nr_retries']
    out_dir = config['out_dir']
    
    run_id = f'{model_id}_{prompt_style}_{nr_samples}'
    log_path = f'{out_dir}/log_{run_id}'
    result_path = f'{out_dir}/results_{run_id}.json'
    codexdb.solve.main(
        data_dir, test_path, 'python', 
        model_id, prompt_style, id_case, 
        mod_start, mod_between, mod_end, 
        sample_path, nr_samples, 200, 
        'executed', 4, log_path, result_path)