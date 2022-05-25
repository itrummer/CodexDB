'''
Created on May 25, 2022

@author: immanueltrummer
'''
import argparse
import codexdb.solve
import openai
import os


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('ai_key', type=str, help='Key for OpenAI access')
    args = parser.parse_args()
    
    openai.api_key = args.ai_key
    data_dir = '/home/ubuntu/spider/spider'
    test_path = '/home/ubuntu/spider/spider/results_dev.json'
    test_start = 0
    test_step = 2
    test_end = 200
    model_id = 'code-davinci-002'
    prompt_style = 'plan'
    nr_samples = 4
    id_case = 0
    mod_end = ''
    nr_retries = 2

    for mod_start, mod_between, out_suffix in [
        ('', '', 'plain'),
        ('Use pandas library', '', 'pandas'),
        ('Use vaex library', '', 'vaex'),
        ('Use datatable library', '', 'datatable'),
        ('', 'Print "Done."', 'done'),
        ('', 'Print intermediate results', 'results'),
        ('', 'Print progress updates', 'progress')]:
        sample_path = f'/home/ubuntu/codexdb/experiments/spider3/{out_suffix}/train_plain.json'
        for max_temperature in [0.125, 0.25, 0.5, 1.0, 2.0]:
            out_dir = f'/home/ubuntu/codexdb/experiments/temperature/{out_suffix}'
            run_id = f'{model_id}_{prompt_style}_S{nr_samples}_' +\
                f'R{nr_retries}_T{max_temperature}'
            log_path = f'{out_dir}/log_{run_id}'
            result_path = f'{out_dir}/results_{run_id}.json'
            if os.path.exists(log_path) or os.path.exists(result_path):
                raise ValueError(
                    'Cannot override existing files: ' +\
                    f'{log_path}; {result_path}')
            
            codexdb.solve.main(
                data_dir, test_path, 'python', 
                model_id, prompt_style, id_case, 
                mod_start, mod_between, '', 
                sample_path, nr_samples, 
                test_start, test_step, test_end, 'executed', 
                nr_retries, max_temperature, log_path, result_path)