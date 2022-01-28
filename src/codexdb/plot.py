'''
Created on Jan 28, 2022

@author: immanueltrummer
'''
import argparse
import json

def count_solved(results):
    """ Count the number of solved test cases. 
    
    Args:
        results: results from one run
    
    Returns:
        number of solved test cases
    """
    count = 0
    for results in results.values():
        for r in results:
            if r['similarity'] == 1.0:
                count += 1
    return count

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('run_dir', type=str, help='Path to directory with runs')
    args = parser.parse_args()
    
    plots = []
    for model_id in ['cushman-codex', 'davinci-codex']:
        plot = []
        for prompt_style in ['question', 'query', 'plan']:
            line = []
            for nr_samples in [0, 2, 4]:
                run_id = f'{model_id}_{prompt_style}_{nr_samples}'
                result_path = f'{args.run_dir}/results_{run_id}.json'
                with open(result_path) as file:
                    data = json.load(file)
                    count = count_solved(data)
                    point = f'({nr_samples}, {count})'
                    line += [point]
            plot += ['\add plot coordinates {' +  ' '.join(line) + '};']
        plots += ['\n'.join(plot)]
    
    for plot in plots:
        print('---')
        print(plot)