'''
Created on Sep 20, 2021

@author: immanueltrummer
'''
import argparse
import codexdb.engine
import codexdb.prompt.all
import openai
import pandas as pd


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('key', type=str, help='OpenAI API access key')
    parser.add_argument('spider', type=str, help='SPIDER benchmark directory')
    args = parser.parse_args()
    
    openai.api_key = args.key
    p_gen = codexdb.prompt.all.AllPrompt(args.spider)
    q_path = f'{args.spider}/all_results.csv'
    queries = pd.read_csv(q_path, sep='\t')
    p_exec = codexdb.engine.PythonExec(args.spider)
    
    ctr = 0
    for row_idx, row in queries.iterrows():
        ctr += 1
        if ctr > 10:
            break
        
        db_id = row['db_id']
        question = row['question']
        print(f'Database ID: {db_id}')
        prompt = p_gen.data_frame(db_id, question)
        print(prompt)
        
        response = openai.Completion.create(
            engine='davinci-codex', prompt=prompt, 
            temperature=0, max_tokens=50)
        print(response)
        generated = response['choices'][0]['text']
        print('Executing generated code: ')
        answer = p_exec.get_answer(db_id, prompt, generated)
        print(f'Generated answer: {answer}')
        print(f'Actual response: {row["results"]}')
            
            # '''
            # import pandas as pd
            #
            # department = pd.read_csv("department.csv")
            # department.columns = ["department id", "name", "creation", "ranking", "budget in billions", "num employees"]
            # head = pd.read_csv("head.csv")
            # head.columns = ["head id", "name", "born state", "age"]
            # management = pd.read_csv("management.csv")
            # management.columns = ["department id". "head id", "temporary acting"]
            #
            # # How many departments have a budget higher than 10 billion?
            # print('How many departments have a budget higher than 10 billion:')
            # print(department.query('"budget in billions" > 10').count())
            #
            # # How many heads of the departments are older than 56 ?
            # print('How many heads of the departments are older than 56:')
            # '''