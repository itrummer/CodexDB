'''
Created on Sep 20, 2021

@author: immanueltrummer
'''
import argparse
import codexdb.code.python
import codexdb.check
import json
import openai

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('key', type=str, help='OpenAI API access key')
    parser.add_argument('spider', type=str, help='SPIDER benchmark directory')
    args = parser.parse_args()
    
    openai.api_key = args.key
    p_gen = codexdb.code.python.PythonGenerator(args.spider)
    q_path = f'{args.spider}/results_dev.json'
    with open(q_path) as file:
        queries = json.load(file)
    
    nr_correct = 0
    nr_wrong = 0
    
    with open('codex_log4.txt', 'w') as log_file:
        ctr = 0
        for query in queries:
            ctr += 1
            print(f'Iteration counter: {ctr}')
            # if ctr < 31:
                # continue
            
            db_id = query['db_id']
            question = query['question']
            print(f'Database ID: {db_id}')
            prompt = p_gen.generate(db_id, question)
            print(prompt)
            
            try:
                response = openai.Completion.create(
                    engine='davinci-codex', prompt=prompt, 
                    temperature=0, max_tokens=150)
                print(response)
                generated = response['choices'][0]['text']
                print('Executing generated code: ')
                answer = p_gen.execute(db_id, question, generated)
                print(f'Generated answer: {answer}')
                ref_res = query["results"]
                print(f'Actual response: {ref_res}')
                cmp = codexdb.check.set_compare(ref_res, answer)
                print(f'Set comparison: {cmp}')
                log_file.write(f'{ctr}: DB: {db_id}; Q: {question}; C: {cmp}\n')
                if cmp:
                    nr_correct += 1
                else:
                    nr_wrong += 1
                print(f'Number of correct results: {nr_correct}')
                print(f'Number of incorrect results: {nr_wrong}')
            except:
                print('Error while processing prompt!')
        
        log_file.write(f'OK: {nr_correct}; False: {nr_wrong}\n')