'''
Created on Jan 3, 2022

@author: immanueltrummer
'''
import argparse
import codexdb.catalog
import codexdb.engine
import json
import os
import openai
import pandas as pd
import sqlglot
import sys
import time


def db_info(schema, files):
    """ Generate description of database.
    
    Args:
        schema: description of database schema
        files: names to files storing tables
    
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
        tbl_columns = [c[1] for c in all_columns if c[0] == tbl_idx]
        col_list = ', '.join(tbl_columns)
        line = f'Table {tbl_name} with columns {col_list}, ' \
            f'stored in {filename}.'
        lines.append(line)
    return lines


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
            temperature=temperature, max_tokens=400)
        # ,
            # stop='--- End of Python program ---')
        return response['choices'][0]['text']
    except Exception as e:
        print(f'Error querying OpenAI (model: {model_id}): {e}')
        return ''


def get_prompt(schema, files, question, query, prompt_style):
    """ Generate prompt for processing specific query. 
    
    Args:
        schema: description of database schema
        files: location of data files for tables
        question: natural language query
        query: SQL translation of query
        prompt_style: describes style of generated prompt
    
    Returns:
        Prompt generating code for executing query
    """
    prompt_parts = []
    prompt_parts.append(
        f'"""\nThis Python program answers the query "{question}" ' +\
        f'on the following tables:')
    prompt_parts += db_info(schema, files)
    # prompt_parts.append('The first line in each file is the header column.')
    if prompt_style == 'train':
        prompt_parts.append(f'SQL query: {query}')
        prompt_parts += get_plan(query)
    else:
        prompt_parts.append('1. Import pandas library.')
        prompt_parts.append('2. Calculate query result.')
        prompt_parts.append("3. Write result to 'result.csv'.")
    prompt_parts.append('"""')
    # prompt_parts.append('')
    # prompt_parts.append('--- Start of Python program ---')
    return '\n'.join(prompt_parts)


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


def result_cmp(ref_output, cmp_output):
    """ Compares query result output against reference.
    
    Args:
        ref_output: reference query result
        cmp_output: compare this against reference
    
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
        diffs = ref_output.compare(cmp_output, align_axis=0)
        print(f'-- Differences:\n{diffs}\n--\n')
        nr_diffs = diffs.shape[0]
        return True, nr_diffs, 1.0/(nr_diffs+1)
    except:
        print('(Incomparable)')
        return False, -1, 0


def solve(catalog, model_id, prompt_style, test_case, max_tries):
    """ Solve given test case by generating code.
    
    Args:
        catalog: informs on database schemata
        model_id: ID of OpenAI model
        prompt_style: style of generated prompt
        test_case: a natural language query
        max_tries: maximal number of tries
    
    Returns:
        list of dictionaries with generated code and statistics
    """
    db_id = test_case['db_id']
    schema = catalog.schema(db_id)
    files = catalog.files(db_id)
    question = test_case['question']
    query = test_case['query']
    temperature_step = 0.5 / max_tries
    print(f'Treating query {query}, question {question}.')
    
    results = []
    for try_idx in range(max_tries):
        print(f'Starting try number {try_idx} ...')
        
        gen_start_s = time.time()
        prompt = get_prompt(schema, files, question, query, prompt_style)
        temperature = try_idx * temperature_step
        code = generate_code(model_id, prompt, temperature)
        print(f'Generated code:\n-------\n{code}\n-------\n')
        gen_total_s = time.time() - gen_start_s
        
        success, output, elapsed_s = engine.execute(db_id, 'python', code, 30)
        print(f'CodexDB successful: {success} in {elapsed_s}s')                
        ref_output = pd.DataFrame(test_case['results'])
        comparable, nr_diffs, similarity = result_cmp(ref_output, output)
        
        nr_tries = try_idx + 1
        test_prompt = get_prompt(schema, files, question, query, 'test')
        results.append({
            'nr_tries':nr_tries, 'executed':success, 'comparable':comparable, 
            'nr_diffs':nr_diffs, 'similarity':similarity, 'output':output, 
            'execution_s':elapsed_s, 'db':db_id, 'question':question, 
            'query':query, 'prompt':test_prompt, 'code':code, 
            'generation_s':gen_total_s})

        if similarity >= 1.0:
            break

    return results


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('ai_key', type=str, help='Key for OpenAI access')
    parser.add_argument('data_dir', type=str, help='Data directory')
    parser.add_argument('test_path', type=str, help='Path to test case file')
    parser.add_argument('model_id', type=str, help='ID of OpenAI model')
    parser.add_argument('prompt_style', type=str, help='Style of prompt')
    parser.add_argument('nr_tests', type=int, help='Number of test cases')
    parser.add_argument('max_tries', type=int, help='Maximal number of tries')
    args = parser.parse_args()
    
    os.environ['KMP_DUPLICATE_LIB_OK']='True'
    openai.api_key = args.ai_key
    with open(args.test_path) as file:
        test_cases = json.load(file)
    if args.prompt_style not in ['train', 'test']:
        print(f'Unknown prompt style: {args.prompt_style}!')
        sys.exit(1)

    catalog = codexdb.catalog.DbCatalog(args.data_dir)
    engine = codexdb.engine.ExecuteCode(catalog)

    all_results = []
    for i in range(args.nr_tests):
        print(f'Starting test case nr. {i} ...')
        test_case = test_cases[i]
        cur_results = solve(
            catalog, args.model_id, args.prompt_style,
            test_case, args.max_tries)
        all_results.append(cur_results)
        print(cur_results)

    with open('results.json', 'w') as results_file:
        json.dump(all_results, results_file)