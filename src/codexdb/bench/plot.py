'''
Created on Jan 28, 2022

@author: immanueltrummer
'''
import argparse
import collections
import json
import re
import statistics


model_ids = ['gpt-3.5-turbo', 'gpt-4o']


def get_run_id(model_id, prompt_style, nr_samples):
    """ Generate string ID characterizing run settings.
    
    Args:
        model_id: ID of the LLM used.
        prompt_style: style of prompt.
        nr_samples: how many samples for few-shot learning.
    
    Returns:
        string ID of run (used in result file names).
    """
    return f'{model_id}_{prompt_style}_{nr_samples}'


def agg_all(run_dir, solved, map_fct, agg_fct):
    """ Calculate aggregates over all runs.
    
    Args:
        run_dir: directory containing benchmark results
        solved: whether to consider only successful tries
        map_fct: maps tries to values for aggregation
        agg_fct: function used to aggregate values
    
    Returns:
        aggregated value over all tries
    """
    values = []
    #for model_id in ['cushman-codex', 'davinci-codex']:
    #for model_id in ['code-cushman-001', 'code-davinci-002']:
    for model_id in model_ids:
        # for prompt_style in ['question', 'query', 'plan']:
        for prompt_style in ['plan']:
            for nr_samples in [0, 2, 4]:
                run_id = get_run_id(model_id, prompt_style, nr_samples)
                result_path = f'{run_dir}/results_{run_id}.json'
                try:
                    with open(result_path) as file:
                        data = json.load(file)
                        for tries in data.values():
                            for one_try in tries:
                                if not solved or one_try['similarity']==1.0:
                                    value = map_fct(one_try)
                                    if value is not None:
                                        values.append(value)
                except Exception as e:
                    pass
                    #print(e)
    
    return agg_fct(values)


def analyze_code(run_dir):
    """ Analyze generated code. 
    
    Args:
        run_dir: directory containing benchmark results
    """
    print('Analyzing generated code ...')
    model_id = model_ids[-1]
    prompt_style = 'plan'
    nr_samples = 2
    run_id = get_run_id(model_id, prompt_style, nr_samples)
    result_path = f'{run_dir}/results_{run_id}.json'
    with open(result_path) as file:
        data = json.load(file)
    
    lib_count = collections.defaultdict(lambda:0)
    tries_by_case = data.values()
    libraries = [
        'csv', 'pandas', 'vaex', 'datatable']
    for tries in tries_by_case:
        code = tries[-1]['code']
        for library in libraries:
            if f'import {library}' in code:
                lib_count[library] += 1
    
    reg_count = collections.defaultdict(lambda:0)
    reg_exps = [
        'print\(\'Done\.\'\)', 'print\(\'Done\'\)',
        'print\("Done"\)', 'print\("Done."\)',
        'print\("done"\)', 'print\("done."\)',
        'print\(\'done\'\)', 'print\(\'done.\'\)',
        'print\(([a-zA-Z_\(\)\.])+\)',
        'print\(["|\'].+["|\']\)', 'print']
    for tries in tries_by_case:
        code = tries[-1]['code']
        for reg_exp in reg_exps:
            if re.search(reg_exp, code):
                reg_count[reg_exp] += 1
    
    print(lib_count)
    print(reg_count)


def analyze_training(run_dir):
    """ Analyze training process. """
    print('Analyzing training process ...')
    result_path = f'{run_dir}/train_plain.json'
    with open(result_path) as file:
        data = json.load(file)

    tries_by_case = data.values()
    nr_solved = 0
    for tries in tries_by_case:
        if [t for t in tries if t['similarity']==1.0]:
            nr_solved += 1
    print(f'Cases solved: {nr_solved}')
    
    solved_by = []
    for max_nr_tries in range(11):
        count = 0
        for tries in tries_by_case:
            nr_tries = len(tries)
            last_idx = min(max_nr_tries, nr_tries)
            count += len([t for t in tries[:last_idx] if t['similarity']==1.0])
        solved_by += [count]
    solved_by = list(enumerate(solved_by))
    solved_by = ' '.join([str(s) for s in solved_by])
    print(f'Nr. solved by try: {solved_by}')

    total_s = 0
    for tries in tries_by_case:
        for one_try in tries:
            generation_s = one_try['gen_total_s']
            execution_s = one_try['execution_s']['total_s']
            total_s += generation_s
            total_s += execution_s
    print(f'Total training time: {total_s} s')
    
    nr_tries_by_case = [len(tries) for tries in tries_by_case]
    print('Analyzing number of tries')
    for fct in [min, statistics.mean, statistics.median, max]:
        agg = fct(nr_tries_by_case)
        print(f'Nr. tries {fct}: {agg}')
            

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
        required = list(zip(must_contain.split(':'), multiplicity.split(':')))
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
    for model_id in model_ids:
        plot = []
        for prompt_style in ['question', 'query', 'plan']:
        # for prompt_style in ['plan']:
            line = []
            for nr_samples in [0, 2, 4]:
                run_id = get_run_id(model_id, prompt_style, nr_samples)
                result_path = f'{run_dir}/results_{run_id}.json'
                try:
                    with open(result_path) as file:
                        data = json.load(file)
                        y_coordinate = y_fct(data)
                        point = f'({nr_samples}, {y_coordinate})'
                        line += [point]
                except Exception as e:
                    #print(f'Exception for {result_path}: {e}')
                    line += ['(-1, -1)']
            plot += ['\\addplot coordinates {' +  ' '.join(line) + '};']
        plots += ['\n'.join(plot)]
    return plots


def median(results, extractor, solved):
    """ Calculate median of numerical field over all tries.
    
    Args:
        results: dictionary mapping test case IDs to lists of tries
        extractor: function for extracting value of interest
        solved: whether to consider solved test cases only
    
    Returns:
        average of field over all relevant tries
    """
    values = []
    for tries in results.values():
        for one_try in tries:
            if not solved or one_try['similarity'] == 1.0:
                value = extractor(one_try)
                if value is not None:
                    values += [value]
    return statistics.median(values) if values else -1


def print_aggs(run_dir, solved, map_fct):
    """ Print out aggregates for tries in directory.
    
    Args:
        run_dir: directory containing benchmark results
        solved: whether to only consider successful tries
        map_fct: maps tries to numbers for aggregation
    """
    print(f'Printint aggregates for {run_dir} (solved: {solved}):')
    for agg_fct in [min, statistics.median, max]:
        agg_val = agg_all(run_dir, solved, map_fct, agg_fct)
        print(f'{agg_fct}:{agg_val}')
    print('\n' * 3)


def print_group(plots):
    """ Print out a group of plots.
    
    Args:
        plots: list of plots
    """
    for plot in plots:
        print('---')
        print(plot)
    print()
    print('###')


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
        
    print('CODE LENGTH')
    map_fct = lambda x:len(x['code'])
    y_fct = lambda d:median(d, map_fct, True)
    print_group(generate_plot(args.run_dir, y_fct))
    print_aggs(args.run_dir, True, map_fct)
    
    print('QUERY LENGTH')
    map_fct = lambda x:len(x['query'])
    y_fct = lambda d:median(d, map_fct, False)
    print_group(generate_plot(args.run_dir, y_fct))
    print_aggs(args.run_dir, False, map_fct)
    
    print('GENERATION TIMES')
    map_fct = lambda x:x['gen_stats']['last_request_s'] if 'gen_stats' in x and 'last_request_s' in x['gen_stats'] else None
    y_fct = lambda d:median(d, map_fct, False)
    print_group(generate_plot(args.run_dir, y_fct))
    print_aggs(args.run_dir, False, map_fct)
    
    print('EXECUTION TIMES')
    map_fct = lambda x:x['execution_s']['total_s']
    y_fct = lambda d:median(d, map_fct, True)
    print_group(generate_plot(args.run_dir, y_fct))
    print_aggs(args.run_dir, True, map_fct)
    
    print('PROMPT TOKENS')
    map_fct = lambda x:x['gen_stats']['prompt_tokens']
    y_fct = lambda d:median(d, map_fct, False)
    print_group(generate_plot(args.run_dir, y_fct))
    print_aggs(args.run_dir, False, map_fct)
    
    print('COMPLETION TOKENS')
    map_fct = lambda x:x['gen_stats']['completion_tokens']
    y_fct = lambda d:median(d, map_fct, False)
    print_group(generate_plot(args.run_dir, y_fct))
    print_aggs(args.run_dir, False, map_fct)
    
    print('ANALYZING CODE')
    analyze_code(args.run_dir)
    print('\n\n\n')
    
    print('ANALYZING TRAINING')
    analyze_training(args.run_dir)