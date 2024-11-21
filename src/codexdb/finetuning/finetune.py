'''
Created on Nov 21, 2024

@author: immanueltrummer
'''
import argparse
import openai
import time

client = openai.OpenAI()


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('in_path', type=str, help='Path to input file')
    parser.add_argument('model', type=str, help='Base model for fine-tuning')
    args = parser.parse_args()
    
    reply = client.files.create(
        file=open(args.in_path, 'rb'), 
        purpose='fine-tune')
    file_id = reply.id
    
    reply = client.fine_tuning.jobs.create(
        training_file=file_id, model=args.model)
    job_id = reply.id
    print(f'Job ID: {job_id}')
    
    status = None
    start_s = time.time()
    
    while not (status == 'succeeded'):
        
        time.sleep(5)
        total_s = time.time() - start_s
        print(f'Fine-tuning since {total_s} seconds.')
        
        reply = client.fine_tuning.jobs.retrieve(job_id)
        status = reply.status
        print(f'Status: {status}')
        print(status)
    
    print(f'Fine-tuning is finished!')
    model_id = reply.fine_tuned_model
    print(f'Model ID: {model_id}')