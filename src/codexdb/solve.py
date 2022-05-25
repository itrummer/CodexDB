'''
Created on Jan 3, 2022

@author: immanueltrummer
'''
import argparse
import codexdb.catalog
import codexdb.code
import codexdb.engine
import contextlib
import json
import os
import openai
import pandas as pd
import time

def extract_samples(catalog, path_to_results):
    """ Extracts completion examples from prior results file.
    
    Args:
        catalog: database catalog with schema information
        path_to_results: path to prior results file
    
    Returns:
        list of extracted examples
    """
    with open(path_to_results) as file:
        prior_results = json.load(file)
    
    examples = []
    for cur_results in prior_results.values():
        for r in cur_results:
            if r['similarity'] == 1.0:
                examples.append(r)
    
    for e in examples:
        if 'schema' not in e:
            db_id = e['db_id']
            e['schema'] = catalog.schema(db_id)
            e['files'] = catalog.files(db_id)
            
    return examples
    
def result_cmp(ref_output, cmp_output, reorder):
    """ Compares query result output against reference.
    
    Args:
        ref_output: reference query result
        cmp_output: compare this against reference
        reorder: whether to consider reordering
    
    Returns:
        Comparable flag, number of differences, similarity
    """
    print(f'-- CodexDB output:\n{cmp_output}\n--\n')
    print(f'CodexDB Index: {cmp_output.index}')
    print(f'CodexDB info: {cmp_output.info()}')
    print(f'-- Reference output:\n{ref_output}\n--\n')
    print(f'Reference Index: {ref_output.index}')
    print(f'Reference info: {ref_output.info()}')
    
    ref_output.columns = range(ref_output.shape[1])
    cmp_output.columns = range(cmp_output.shape[1])
    try:
        print('Casting all columns to string type ...')
        ref_output = ref_output.astype(str)
        cmp_output = cmp_output.astype(str)
        
        print('Normalizing representation of integers ...')
        def to_int(float_str):
            """ Transforms rounded float values into integers. """
            if float_str.endswith('.0'):
                return float_str[:-2]
            else:
                return float_str
        ref_output = ref_output.applymap(to_int)
        cmp_output = cmp_output.applymap(to_int)
        
        print('Normalizing representation of lists ...')
        def unwrap(cell):
            """ Unwrap elements from singleton lists. """
            if isinstance(cell, list) and len(cell) == 1:
                return cell[0]
            else:
                return cell
        ref_output = ref_output.applymap(unwrap)
        cmp_output = cmp_output.applymap(unwrap)
        
        if reorder:
            print('Reordering Rows Before Comparison')
            nr_columns = len(ref_output.columns)
            column_idxs = list(range(nr_columns))
            ref_output.sort_values(by=column_idxs, inplace=True)
            cmp_output.sort_values(by=column_idxs, inplace=True)

        ref_output.reset_index(drop=True, inplace=True)
        cmp_output.reset_index(drop=True, inplace=True)

        print(f'--- CodexDB column types:\n{cmp_output.dtypes}')
        print(f'--- CodexDB normalized output:\n{cmp_output}\n--\n')
        print(f'--- Reference column types:\n{ref_output.dtypes}')
        print(f'--- Normalized reference output:\n{ref_output}\n--\n')
        
        nr_ref_rows = ref_output.shape[0]
        nr_cmp_rows = cmp_output.shape[0]
        if nr_ref_rows == 0 and nr_cmp_rows == 0:
            diffs = pd.DataFrame()
        else:
            diffs = ref_output.compare(cmp_output, align_axis=0)
        print(f'-- Differences:\n{diffs}\n--\n')
        nr_diffs = diffs.shape[0]
        return True, nr_diffs, 1.0/(nr_diffs+1)
    except Exception as e:
        print('(Incomparable)')
        print(f'Exception: {e}')
        return False, -1, 0

def solve(catalog, test_case, coder, engine, 
          termination, max_tries, max_temperature):
    """ Solve given test case by generating code.
    
    Args:
        catalog: database catalog
        test_case: a natural language query
        coder: code generator to use
        engine: execution engine for code
        termination: criterion to advance to next case
        max_tries: maximal number of tries
        max_temperature: maximal temperature
    
    Returns:
        list of dictionaries with generated code and statistics
    """
    db_id = test_case['db_id']
    schema = catalog.schema(db_id)
    files = catalog.files(db_id)
    question = test_case['question']
    query = test_case['query']
    reorder = False if 'order by' in query.lower() else True
    temperature_step = max_temperature / max_tries
    print(f'Treating query {query}, question {question}.')

    results = []
    for try_idx in range(max_tries):
        print("Waiting due to OpenAI's rate limit ...")
        time.sleep(3)
        print(f'Starting try number {try_idx} ...')
        gen_start_s = time.time()
        temperature = try_idx * temperature_step
        gen_stats, code = coder.generate(test_case, temperature)
        print(f'Generated code:\n-------\n{code}\n-------\n')
        print(f'Reference Query: "{query}"')
        gen_total_s = time.time() - gen_start_s
        executed, codb_result, elapsed_s = engine.execute(db_id, code, 30)
        print(f'CodexDB executed: {executed} in {elapsed_s}s')
        ref_output = pd.DataFrame(test_case['results'])
        comparable, nr_diffs, similarity = result_cmp(
            ref_output, codb_result, reorder)
        nr_tries = try_idx + 1
        results.append({
            'nr_tries':nr_tries, 'executed':executed, 'comparable':comparable, 
            'nr_diffs':nr_diffs, 'similarity':similarity, 
            'outsize':len(codb_result), 
            'question':question, 'query':query, 
            'db':db_id, 'schema':schema, 'files':files, 
            'code':code, 'gen_stats':gen_stats, 'gen_total_s':gen_total_s,
            'execution_s':elapsed_s})

        if (termination == 'executed' and executed) or \
            (termination == 'solved' and similarity >= 1.0):
            print('Termination Criterion Satisfied.')
            break

    return results

def main(
        data_dir, test_path, language, model_id, prompt_style, id_case,
        mod_start, mod_between, mod_end, sample_path, nr_samples, 
        test_start, test_step, test_end, termination, max_tries,
        max_temperature, log_path, result_path):
    """ Try solving given test cases and write results to file.
    
    Args:
        data_dir: directory containing database
        test_path: path to file with test cases
        language: generate code in this language
        model_id: OpenAI engine for code generation
        prompt_style: choose prompt template
        id_case: whether to consider letter case of identifiers
        mod_start: modification at plan start
        mod_between: modifications between steps
        mod_end: modification at plan end
        sample_path: path to example library
        nr_samples: number of examples in prompt
        test_start: index of first test case
        test_step: gap between test case indexes
        test_end: index of last test case + 1
        termination: termination criterion
        max_tries: maximal tries per test case
        max_temperature: maximal temperature
        log_path: path for logging output
        result_path: path to result .json file
    """
    catalog = codexdb.catalog.DbCatalog(data_dir)
    os.environ['KMP_DUPLICATE_LIB_OK']='True'
    
    with open(test_path) as file:
        test_cases = json.load(file)
    if language not in ['python', 'sql']:
        raise ValueError(f'Unknown implementation language: {language}!')
    examples = []
    if sample_path:
        with open(sample_path) as file:
            examples = extract_samples(catalog, sample_path)
    if prompt_style not in ['question', 'query', 'plan', 'data']:
        raise ValueError(f'Unknown prompt style: {prompt_style}!')
    if termination not in ['executed', 'solved']:
        raise ValueError(f'Unknown termination criterion: {termination}')

    with open(log_path, 'w') as log_file:
        with contextlib.redirect_stdout(log_file):
            if language == 'python':
                coder = codexdb.code.PythonGenerator(
                    catalog, examples, nr_samples, 
                    prompt_style, model_id, 
                    id_case=id_case,
                    mod_start=mod_start, 
                    mod_between=mod_between, 
                    mod_end=mod_end)
                engine = codexdb.engine.PythonEngine(
                    catalog, id_case)
            elif language == 'sql':
                coder = codexdb.code.SqlGenerator(
                    catalog, examples, nr_samples, 
                    prompt_style, model_id)
                engine = codexdb.engine.SqliteEngine(catalog)
        
            idx_to_results = {}
            for i in range(test_start, test_end, test_step):
                print(f'Starting test case nr. {i} ...')
                test_case = test_cases[i]
                cur_results = solve(
                    catalog, test_case, coder, engine, 
                    termination, max_tries, max_temperature)
                idx_to_results[i] = cur_results
                print(cur_results)
        
            with open(result_path, 'w') as results_file:
                json.dump(idx_to_results, results_file)

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('ai_key', type=str, help='Key for OpenAI access')
    parser.add_argument('data_dir', type=str, help='Data directory')
    parser.add_argument('test_path', type=str, help='Path to test case file')
    parser.add_argument('language', type=str, help='Implementation language')
    parser.add_argument('model_id', type=str, help='ID of OpenAI model')
    parser.add_argument('prompt_style', type=str, help='Style of prompt')
    parser.add_argument('mod_start', type=str, help='Instructions at start')
    parser.add_argument('mod_between', type=str, help='Execute between steps')
    parser.add_argument('mod_end', type=str, help='Instructions at end')
    parser.add_argument('sample_path', type=str, help='Path to sample file')
    parser.add_argument('nr_samples', type=int, help='Number of samples in prompt')
    parser.add_argument('nr_tests', type=int, help='Number of test cases')
    parser.add_argument('termination', type=str, help='Termination criterion')
    parser.add_argument('max_tries', type=int, help='Maximal number of tries')
    parser.add_argument('log_path', type=str, help='Redirect output here')
    parser.add_argument('result_path', type=str, help='Contains results')
    args = parser.parse_args()
    
    openai.api_key = args.ai_key
    main(
        args.data_dir, args.test_path, args.language, args.model_id, 
        args.prompt_style, args.mod_start, args.mod_between, args.mod_end, 
        args.sample_path, args.nr_samples, args.nr_tests, args.termination, 
        args.max_tries, 0.5, args.log_path, args.result_path)