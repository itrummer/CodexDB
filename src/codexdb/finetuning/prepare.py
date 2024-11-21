'''
Created on Nov 21, 2024

@author: immanueltrummer
'''
import argparse
import json
import jsonlines

from codexdb.catalog import DbCatalog
from codexdb.code import PythonGenerator


def get_sample(final_try):
    """ Generate sample from solved test case.
    
    Args:
        final_try: try that solved the test case.
    
    Returns:
        Sample in OpenAI format for fine-tuning.
    """
    schema = final_try['schema']
    db = final_try['db']
    files = final_try['files']
    question = final_try['question']
    query = final_try['query']

    prompt = coder.get_prompt(schema, db, files, question, query)
    user_message = {'role':'user', 'content':prompt}
    
    code = final_try['code']
    assistant_message = {'role':'assistant', 'content':code}
    
    sample = {'messages':[user_message, assistant_message]}
    return sample


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('data_dir', type=str, help='Data directory')
    parser.add_argument('in_path', type=str, help='Path to input')
    parser.add_argument('mod_start', type=str, help='Modification at plan start')
    parser.add_argument('mod_between', type=str, help='Modification between steps')
    parser.add_argument('mod_end', type=str, help='Modification at plan end')
    parser.add_argument('out_path', type=str, help='Path to output')
    args = parser.parse_args()
        
    catalog = DbCatalog(args.data_dir)
    coder = PythonGenerator(
        catalog, [], 0, 'plan', '',
        id_case=True, mod_start=args.mod_start, 
        mod_between=args.mod_between, 
        mod_end=args.mod_end)
    
    with open(args.in_path) as file:
        data = json.load(file)
    
    samples = []
    for test_case in data.values():
        final_try = test_case[-1]
        solved = (final_try['similarity'] == 1.0)
        if solved:
            sample = get_sample(final_try)
            samples.append(sample)
    
    with jsonlines.open(args.out_path, 'w') as file:
        for sample in samples:
            file.write(sample)