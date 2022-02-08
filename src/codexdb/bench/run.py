'''
Created on Oct 3, 2021

@author: immanueltrummer
'''
import argparse
import codexdb.solve
import openai
import os
import time


def train(data_dir, train_path, log_path, mod_start,
          mod_between, mod_end, result_path):
    """ Generate training samples for few-shot learning.
    
    Args:
        data_dir: path to database directory
        train_path: path to test cases for training
        log_path: path to file for logging output
        mod_start: modification at plan start
        mod_between: modification between plan steps
        mod_end: modification at plan end
        result_path: path to file for result output
    """
    codexdb.solve.main(
        data_dir, train_path, 'python', 'davinci-codex', 'plan', 
        mod_start, mod_between, mod_end, '', 0, 50, 'solved', 10, 
        log_path, result_path)

def test(data_dir, test_path, sample_path, mod_start, 
         mod_between, mod_end, out_dir):
    """ Solve test cases using previously generated samples.
    
    Args:
        data_dir: directory of database
        test_path: path to file with test cases
        sample_path: path to file with samples
        mod_start: modification at plan start
        mod_between: modification between plan steps
        mod_end: modification at plan end
        out_dir: generate output in this directory
    """
    for model_id in ['cushman-codex', 'davinci-codex']:
        for prompt_style in ['plan', 'query', 'question']:
            for nr_samples in [0, 2, 4]:
                run_id = f'{model_id}_{prompt_style}_{nr_samples}'
                log_path = f'{out_dir}/log_{run_id}'
                result_path = f'{out_dir}/results_{run_id}.json'
                codexdb.solve.main(
                    data_dir, test_path, 'python', model_id, 
                    prompt_style, mod_start, mod_between, mod_end, 
                    sample_path, nr_samples, 100, 'executed', 1, 
                    log_path, result_path)


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('ai_key', type=str, help='Key for OpenAI access')
    parser.add_argument('data_dir', type=str, help='Data directory')
    parser.add_argument('train_path', type=str, help='Path to train case file')
    parser.add_argument('test_path', type=str, help='Path to test case file')
    parser.add_argument('mod_start', type=str, help='Modifying plan start')
    parser.add_argument('mod_between', type=str, help='Modifications in between')
    parser.add_argument('mod_end', type=str, help='Modifying plan end')
    parser.add_argument('out_dir', type=str, help='Output directory')
    args = parser.parse_args()
    if os.listdir(args.out_dir):
        raise ValueError('Output directory must be empty!')
    
    openai.api_key = args.ai_key
    
    # Train and test generating code without modifications
    log_path = f'{args.out_dir}/train_log_plain'
    sample_path = f'{args.out_dir}/train_plain.json'
    
    start_s = time.time()
    train(args.data_dir, args.train_path, log_path, args.mod_start, 
          args.mod_between, args.mod_end, sample_path)
    total_s = time.time() - start_s
    print(f'Training took {total_s} seconds')
    
    start_s = time.time()
    test(args.data_dir, args.test_path, sample_path, args.mod_start, 
         args.mod_between, args.mod_end, args.out_dir)
    total_s = time.time() - start_s
    print(f'Testing took {total_s} seconds')