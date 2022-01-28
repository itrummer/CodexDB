'''
Created on Jan 28, 2022

@author: immanueltrummer
'''
import argparse
import json

def count_solved(results, must_contain, multiplicity):
    """ Count the number of solved test cases. 
    
    Args:
        results: results from one run
        must_contain: strings that must appear in code, separated by colon
        multiplicity: minimal number of occurrences for each required string
    
    Returns:
        number of solved test cases
    """
    required = zip(must_contain.split(':'), multiplicity.split(':'))
    nr_solved = 0
    for results in results.values():
        for r in results:
            if r['similarity'] == 1.0:
                valid = True
                for required_string, required_number in required:
                    code = r['code']
                    if code.count(required_string) < required_number:
                        valid = False
                
                if valid:
                    nr_solved += 1
    return nr_solved

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('run_dir', type=str, help='Path to directory with runs')
    parser.add_argument('must_contain', type=str, help='Code must contain this')
    parser.add_argument('multiplicity', type=str, help='Minimal #occurrences')
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
                    count = count_solved(
                        data, args.must_contain, 
                        args.multiplicity)
                    point = f'({nr_samples}, {count})'
                    line += [point]
            plot += ['\\addplot coordinates {' +  ' '.join(line) + '};']
        plots += ['\n'.join(plot)]
    
    for plot in plots:
        print('---')
        print(plot)