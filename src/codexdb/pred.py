'''
Created on Sep 20, 2021

@author: immanueltrummer
'''
import argparse
import codexdb.check
import codexdb.engine
import codexdb.prompt.all
import json
import openai

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('key', type=str, help='OpenAI API access key')
    parser.add_argument('spider', type=str, help='SPIDER benchmark directory')
    args = parser.parse_args()
    
    openai.api_key = args.key
    p_gen = codexdb.prompt.all.AllPrompt(args.spider)
    q_path = f'{args.spider}/all_results.json'
    with open(q_path) as file:
        queries = json.load(file)
    p_exec = codexdb.engine.PythonExec(args.spider)
    
    nr_correct = 0
    nr_wrong = 0
    
    with open('codex_log2.txt', 'w') as log_file:
        ctr = 0
        for query in queries:
            ctr += 1
            print(f'Iteration counter: {ctr}')
            # if ctr > 10:
                # break
            
            db_id = query['db_id']
            question = query['question']
            print(f'Database ID: {db_id}')
            prompt = p_gen.data_frame(db_id, question)
            print(prompt)
            
            response = openai.Completion.create(
                engine='davinci-codex', prompt=prompt, 
                temperature=0, max_tokens=100)
            print(response)
            generated = response['choices'][0]['text']
            print('Executing generated code: ')
            answer = p_exec.get_answer(db_id, prompt, generated)
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
        
        log_file.write(f'OK: {nr_correct}; False: {nr_wrong}\n')