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
    if must_contain:
        required = zip(must_contain.split(':'), multiplicity.split(':'))
    else:
        required = []
    
    nr_solved = 0
    for results in results.values():
        for r in results:
            if r['similarity'] == 1.0:
                valid = True
                for required_string, required_number in required:
                    code = r['code']
                    if code.count(required_string) < int(required_number):
                        valid = False
                
                if valid:
                    nr_solved += 1
    return nr_solved

def generate_plot(run_dir, y_fct):
    """ Generates commands for PGF group plot. 
    
    Args:
        run_dir: source data for plot
        y_fct: how to calculate
    
    Returns:
        list of plot groups
    """
    plots = []
    for model_id in ['cushman-codex', 'davinci-codex']:
        plot = []
        for prompt_style in ['question', 'query', 'plan']:
            line = []
            for nr_samples in [0, 2, 4]:
                run_id = f'{model_id}_{prompt_style}_{nr_samples}'
                result_path = f'{run_dir}/results_{run_id}.json'
                with open(result_path) as file:
                    data = json.load(file)
                    y_coordinate = y_fct(data)
                    point = f'({nr_samples}, {y_coordinate})'
                    line += [point]
            plot += ['\\addplot coordinates {' +  ' '.join(line) + '};']
        plots += ['\n'.join(plot)]
    return plots

def print_group(plots):
    """ Print out a group of plots.
    
    Args:
        plots: list of plots
    """
    for plot in plots:
        print('---')
        print(plot)


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('run_dir', type=str, help='Path to directory with runs')
    parser.add_argument('must_contain', type=str, help='Code must contain this')
    parser.add_argument('multiplicity', type=str, help='Minimal #occurrences')
    args = parser.parse_args()
    
    print('Counting number of solved test cases:')
    count_fct = lambda d:count_solved(d, args.must_contain, args.multiplicity)
    count_plots = generate_plot(args.run_dir, count_fct)
    print_group(count_plots)