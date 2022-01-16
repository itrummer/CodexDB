'''
Created on Jan 3, 2022

@author: immanueltrummer
'''
import argparse
import codexdb.catalog
import codexdb.engine
import json
import numpy as np
import os
import openai
import pandas as pd
import random
import sqlglot
import sys
import time


def db_info(schema, db_dir, files, prompt_style):
    """ Generate description of database.
    
    Args:
        schema: description of database schema
        db_dir: 
        files: names to files storing tables
        prompt_style: style of generated prompt
    
    Returns:
        list of description lines
    """
    lines = []
    tables = schema['table_names_original']
    all_columns = schema['column_names_original']
    nr_tables = len(tables)
    for tbl_idx in range(nr_tables):
        filename = files[tbl_idx]
        tbl_name = tables[tbl_idx]
        
        if prompt_style == 'data':
            
            lines.append(f'Sample from table {tbl_name}, stored in "{filename}":')
            df = pd.read_csv(f'{db_dir}/{filename}')
            headers = []
            for col_name, col_type in zip(df.columns, df.dtypes):
                header = f'{col_name}:{col_type.name}'
                headers.append(header)
            lines.append(','.join(headers))
                    
            nr_rows = df.shape[0]
            nr_cols = df.shape[1]
            for row_idx in range(min(5, nr_rows)):
                row_parts = []
                for col_idx in range(nr_cols):
                    value = str(df.iloc[row_idx, col_idx])
                    col_type = df.dtypes[col_idx].type
                    if not np.issubdtype(col_type, np.number):
                        value = '"' + value + '"'
                    row_parts.append(value)
                lines.append(','.join(row_parts))
        else:
            tbl_columns = ["'" + c[1] + "'" for c in all_columns if c[0] == tbl_idx]
            col_list = ','.join(tbl_columns)
            line = f'Table {tbl_name} with columns {col_list}, ' \
                f'stored in \'{filename}\'.'
            lines.append(line)
            
    return lines


def extract_samples(path_to_results):
    """ Extracts completion examples from prior results file.
    
    Args:
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
    return examples

    
def generate_code(model_id, prompt, temperature):
    """ Generate code by completing given prompt. 
    
    Args:
        model_id: ID of OpenAI model for generation
        prompt: initiate generation with this prompt
        temperature: degree of randomization in generation
    
    Returns:
        generated code, following prompt
    """
    try:
        print(f'\nPrompt:\n*******\n{prompt}\n*******')
        response = openai.Completion.create(
            engine=model_id, prompt=prompt, 
            temperature=temperature, max_tokens=600,
            stop='"""')
        return response['choices'][0]['text']
    except Exception as e:
        print(f'Error querying OpenAI (model: {model_id}): {e}')
        return ''


def get_plan(sql):
    """ Generate natural language query plan. 
    
    Args:
        sql: the SQL query to process
    
    Returns:
        list of plan steps (in order)
    """
    tokenizer = sqlglot.tokens.Tokenizer()
    parser = sqlglot.parser.Parser()
    tokens = tokenizer.tokenize(sql)
    ast = parser.parse(tokens)[0]
    
    tables = []
    for table_expr in ast.find_all(sqlglot.expressions.Table):
        table_name = table_expr.args['this'].args['this']
        tables.append(table_name)
    
    out_parts = []
    out_parts.append('Import pandas library.')
    out_parts.append(f'Load data for table {tables[0]}.')
    for table in tables[2:]:
        out_parts.append(f'Join with table {table}.')
    
    where = ast.args['where'] if 'where' in ast.args else None
    if where is not None:
        out_parts.append(f'Filter using {where.sql()}.')
    
    group_by = ast.args['group'] if 'group' in ast.args else None
    if group_by is not None:
        out_parts.append(f'Group data via {group_by.sql()}.')
    
    order_by = ast.args['order'] if 'order' in ast.args else None
    if order_by is not None:
        out_parts.append(f'Sort according to {order_by.sql()}.')
    
    selects = ast.args['expressions'] if 'expressions' in ast.args else None
    if selects is not None:
        selects_sql = ', '.join([s.sql() for s in selects])
        out_parts.append(f'Calculate {selects_sql}.')
    
    out_parts.append("Write query result to 'result.csv'.")
    out_parts = [f'{idx}. {out}' for idx, out in enumerate(out_parts, 1)]
    return out_parts


def get_prompt(schema, db_dir, files, question, query, prompt_style):
    """ Generate prompt for processing specific query. 
    
    Args:
        schema: description of database schema
        db_dir: directory storing data files
        files: location of data files for tables
        question: natural language query
        query: SQL translation of query
        prompt_style: describes style of generated prompt
    
    Returns:
        Prompt generating code for executing query
    """
    prompt_parts = []
    prompt_parts.append('"""')
    prompt_parts += db_info(schema, db_dir, files, prompt_style)
    prompt_parts.append(f'Query: "{question}".')
    if prompt_style == 'train':
        prompt_parts.append(f'SQL query: {query}')
        prompt_parts += get_plan(query)
    else:
        prompt_parts.append('1. Import pandas library.')
        prompt_parts.append('2. Calculate query answer.')
        prompt_parts.append("3. Store result in 'result.csv'.")
    prompt_parts.append('"""')
    return '\n'.join(prompt_parts)


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


def sample_prompts(db_dir, prompt_style, examples, nr_samples):
    """ Generate prompts from examples for few-shot learning.
    
    Args:
        db_dir: directory containing database data
        prompt_style: determines template for prompts
        examples: several example prompts with completions
        nr_samples: number of examples to select
    
    Returns:
        a prefix of the full prompt to generate
    """
    parts = []
    if examples:
        selected = random.sample(examples, k=nr_samples)
        for example in selected:
            prompt = get_prompt(
                example['schema'], db_dir, example['files'], 
                example['question'], example['query'], 
                prompt_style)
            parts.append(prompt)
            parts.append(example['code'])
            parts.append('')
            parts.append('')
    return '\n'.join(parts)
    

def solve(
        catalog, model_id, prompt_style, test_case, 
        examples, nr_samples, termination, max_tries):
    """ Solve given test case by generating code.
    
    Args:
        catalog: informs on database schemata
        model_id: ID of OpenAI model
        prompt_style: style of generated prompt
        test_case: a natural language query
        examples: examples for few-shot learning
        nr_samples: number of examples in prompt
        termination: criterion to advance to next case
        max_tries: maximal number of tries
    
    Returns:
        list of dictionaries with generated code and statistics
    """
    db_id = test_case['db_id']
    schema = catalog.schema(db_id)
    files = catalog.files(db_id)
    db_dir = catalog.db_dir(db_id)
    question = test_case['question']
    query = test_case['query']
    reorder = False if 'order by' in query.lower() else True
    temperature_step = 0.5 / max_tries
    prefix = sample_prompts(db_dir, prompt_style, examples, nr_samples)
    print(f'Treating query {query}, question {question}.')
    
    results = []
    for try_idx in range(max_tries):
        print(f'Starting try number {try_idx} ...')
        
        gen_start_s = time.time()
        suffix = get_prompt(
            schema, db_dir, files, question, query, prompt_style)
        prompt = prefix + '\n' + suffix 
        temperature = try_idx * temperature_step
        code = generate_code(model_id, prompt, temperature)
        print(f'Generated code:\n-------\n{code}\n-------\n')
        gen_total_s = time.time() - gen_start_s
        
        executed, output, elapsed_s = engine.execute(db_id, 'python', code, 30)
        print(f'CodexDB executed: {executed} in {elapsed_s}s')                
        ref_output = pd.DataFrame(test_case['results'])
        comparable, nr_diffs, similarity = result_cmp(ref_output, output, reorder)
        
        nr_tries = try_idx + 1
        test_prompt = get_prompt(
            schema, db_dir, files, question, query, 'test')
        results.append({
            'nr_tries':nr_tries, 'executed':executed, 'comparable':comparable, 
            'nr_diffs':nr_diffs, 'similarity':similarity, 'outsize':len(output), 
            'question':question, 'query':query, 
            'db':db_id, 'schema':schema, 'files':files, 
            'used_prompt':prompt, 'test_prompt':test_prompt, 'code':code,
            'generation_s':gen_total_s, 'execution_s':elapsed_s})

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
    parser.add_argument('model_id', type=str, help='ID of OpenAI model')
    parser.add_argument('prompt_style', type=str, help='Style of prompt')
    parser.add_argument('sample_path', type=str, help='Path to sample file')
    parser.add_argument('nr_samples', type=int, help='Number of samples in prompt')
    parser.add_argument('nr_tests', type=int, help='Number of test cases')
    parser.add_argument('termination', type=str, help='Termination criterion')
    parser.add_argument('max_tries', type=int, help='Maximal number of tries')
    args = parser.parse_args()
    
    os.environ['KMP_DUPLICATE_LIB_OK']='True'
    openai.api_key = args.ai_key
    with open(args.test_path) as file:
        test_cases = json.load(file)
    with open(args.sample_path) as file:
        examples = extract_samples(args.sample_path)
    if args.prompt_style not in ['train', 'test', 'data']:
        print(f'Unknown prompt style: {args.prompt_style}!')
        sys.exit(1)
    if args.termination not in ['executed', 'solved']:
        print(f'Unknown termination criterion: {args.termination}')
        sys.exit(1)

    catalog = codexdb.catalog.DbCatalog(args.data_dir)
    engine = codexdb.engine.ExecuteCode(catalog)

    idx_to_results = {}
    for i in range(args.nr_tests):
        print(f'Starting test case nr. {i} ...')
        test_case = test_cases[i]
        cur_results = solve(
            catalog, args.model_id, args.prompt_style,
            test_case, examples, args.nr_samples, 
            args.termination, args.max_tries)
        idx_to_results[i] = cur_results
        print(cur_results)

    with open('results.json', 'w') as results_file:
        json.dump(idx_to_results, results_file)