'''
Created on Sep 30, 2021

@author: immanueltrummer
'''
import argparse
import openai
import pdfplumber
import re
import time

def summarize(text):
    """ Summarize text using OpenAI GPT-3 Codex.
    
    Args:
        text: the text to summarize
    
    Returns:
        one sentence summary
    """
    prompt = f'{text}\n\nTL;DR: In summary,'
    response = openai.Completion.create(
        engine='davinci-codex', prompt=prompt, 
        temperature=0, max_tokens=50)
    summary = response['choices'][0]['text']
    # print(f'Summary: {summary}')
    first_sentence = re.search('.*\.', summary).group()
    return first_sentence.strip()

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('key', type=str, help='Key for OpenAI API')
    parser.add_argument('in_file', type=str, help='Path of file to summarize')
    parser.add_argument('out_file', type=str, help='Path to output file')
    args = parser.parse_args()
    
    start_s = time.time()
    openai.api_key = args.key
    with pdfplumber.open(args.in_file) as pdf:
        with open(args.out_file, 'w') as out:
            for p_idx, p in enumerate(pdf.pages):
                text = p.extract_text()
                summary = summarize(text)
                out.write(f'{summary}\n')
                print(f'{p_idx}: {summary}')
                total_s = time.time() - start_s
                print(f'Time elapsed: {total_s} seconds')