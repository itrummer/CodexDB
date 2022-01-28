'''
Created on Oct 3, 2021

@author: immanueltrummer
'''
import argparse
import codexdb.solve
import openai


def train(data_dir, train_path, log_path, result_path, 
          mod_start='Import pandas library', 
          mod_between='', mod_end=''):
    """ Generate training samples for few-shot learning.
    
    Args:
        data_dir: path to database directory
        train_path: path to test cases for training
        log_path: path to file for logging output
        result_path: path to file for result output
    """
    codexdb.solve.main(
        data_dir, train_path, 'python', 'davinci-codex', 'plan', 
        mod_start, mod_between, mod_end, '', 0, 50, 'solved', 10, 
        log_path, result_path)

def test_plain(data_dir, test_path, sample_path, out_dir):
    """ Solve test cases without any user-defined modifications.
    
    Args:
        data_dir: directory of database
        test_path: path to file with test cases
        sample_path: path to file with samples
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
                    prompt_style, mod_start='Import pandas library', '', '', 
                    sample_path, nr_samples, 100, 'executed', 1, 
                    log_path, result_path)


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('ai_key', type=str, help='Key for OpenAI access')
    parser.add_argument('data_dir', type=str, help='Data directory')
    parser.add_argument('train_path', type=str, help='Path to train case file')
    parser.add_argument('test_path', type=str, help='Path to test case file')
    parser.add_argument('out_dir', type=str, help='Output directory')
    args = parser.parse_args()
    
    openai.api_key = args.ai_key
    
    # Train and test generating code without modifications
    log_path = f'{args.out_dir}/train_log_plain'
    sample_path = f'{args.out_dir}/train_plain.json'
    train(args.data_dir, args.train_path, log_path, sample_path)
    test_plain(args.data_dir, args.test_path, sample_path, args.out_dir)