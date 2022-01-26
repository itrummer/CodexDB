'''
Created on Jan 3, 2022

@author: immanueltrummer
'''
import argparse
import codexdb.catalog
import codexdb.code
import codexdb.engine
import json
import os
import openai
import pandas as pd
import sys
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
    print(f'-- Reference output:\n{ref_output}\n--\n')
    ref_output.reindex()
    cmp_output.reindex()
    ref_output.columns = [0] * ref_output.shape[1]
    cmp_output.columns = [0] * cmp_output.shape[1]
    try:
        if reorder:
            print('Reordering Rows Before Comparison')
            nr_columns = len(ref_output.columns)
            column_idxs = list(range(nr_columns))
            ref_output.sort_values(by=column_idxs)
            cmp_output.sort_values(by=column_idxs)

        diffs = ref_output.compare(cmp_output, align_axis=0)
        print(f'-- Differences:\n{diffs}\n--\n')
        nr_diffs = diffs.shape[0]
        return True, nr_diffs, 1.0/(nr_diffs+1)
    except:
        print('(Incomparable)')
        return False, -1, 0

def solve(test_case, coder, engine, termination, max_tries):
    """ Solve given test case by generating code.
    
    Args:
        test_case: a natural language query
        coder: code generator to use
        engine: execution engine for code
        termination: criterion to advance to next case
        max_tries: maximal number of tries
    
    Returns:
        list of dictionaries with generated code and statistics
    """
    db_id = test_case['db_id']
    schema = catalog.schema(db_id)
    files = catalog.files(db_id)
    question = test_case['question']
    query = test_case['query']
    reorder = False if 'order by' in query.lower() else True
    temperature_step = 0.5 / max_tries
    print(f'Treating query {query}, question {question}.')

    results = []
    for try_idx in range(max_tries):
        print("Waiting due to OpenAI's rate limit ...")
        time.sleep(3)
        print(f'Starting try number {try_idx} ...')
        gen_start_s = time.time()
        temperature = try_idx * temperature_step
        code = coder.generate(test_case, temperature)
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
            'code':code, 'generation_s':gen_total_s, 'execution_s':elapsed_s})

        if (termination == 'executed' and executed) or \
            (termination == 'solved' and similarity >= 1.0):
            print('Termination Criterion Satisfied.')
            break

    return results


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('ai_key', type=str, help='Key for OpenAI access')
    parser.add_argument('data_dir', type=str, help='Data directory')
    parser.add_argument('test_path', type=str, help='Path to test case file')
    parser.add_argument('language', type=str, help='Implementation language')
    parser.add_argument('model_id', type=str, help='ID of OpenAI model')
    parser.add_argument('prompt_style', type=str, help='Style of prompt')
    parser.add_argument('sample_path', type=str, help='Path to sample file')
    parser.add_argument('nr_samples', type=int, help='Number of samples in prompt')
    parser.add_argument('nr_tests', type=int, help='Number of test cases')
    parser.add_argument('termination', type=str, help='Termination criterion')
    parser.add_argument('max_tries', type=int, help='Maximal number of tries')
    args = parser.parse_args()
    
    catalog = codexdb.catalog.DbCatalog(args.data_dir)
    os.environ['KMP_DUPLICATE_LIB_OK']='True'
    openai.api_key = args.ai_key
    with open(args.test_path) as file:
        test_cases = json.load(file)
    if args.language not in ['python', 'sql']:
        print(f'Unknown implementation language: {args.language}!')
        sys.exit(1)
    with open(args.sample_path) as file:
        examples = extract_samples(catalog, args.sample_path)
    if args.prompt_style not in ['train', 'test', 'data']:
        print(f'Unknown prompt style: {args.prompt_style}!')
        sys.exit(1)
    if args.termination not in ['executed', 'solved']:
        print(f'Unknown termination criterion: {args.termination}')
        sys.exit(1)

    if args.language == 'python':
        coder = codexdb.code.PythonGenerator(
            catalog, examples, args.nr_samples, 
            args.prompt_style, args.model_id)
        engine = codexdb.engine.PythonEngine(catalog)
    elif args.language == 'sql':
        coder = codexdb.code.SqlGenerator(
            catalog, examples, args.nr_samples, 
            args.prompt_style, args.model_id)
        engine = codexdb.engine.SqliteEngine(catalog)

    idx_to_results = {}
    for i in range(args.nr_tests):
        print(f'Starting test case nr. {i} ...')
        test_case = test_cases[i]
        cur_results = solve(
            test_case, coder, engine, 
            args.termination, args.max_tries)
        idx_to_results[i] = cur_results
        print(cur_results)

    with open('results.json', 'w') as results_file:
        json.dump(idx_to_results, results_file)