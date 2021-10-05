'''
Created on Sep 30, 2021

@author: immanueltrummer
'''
import argparse
import codexdb.mining.common
import openai
import pandas as pd
import pdfplumber
import time

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('key', type=str, help='Key for OpenAI API')
    parser.add_argument('in_file', type=str, help='Path of file to summarize')
    parser.add_argument('out_file', type=str, help='Path to output file')
    args = parser.parse_args()
    
    sum_by_page = []
    start_s = time.time()
    openai.api_key = args.key
    with pdfplumber.open(args.in_file) as pdf:
        for p_idx, p in enumerate(pdf.pages):
            text = p.extract_text()
            summary = codexdb.mining.common.summarize(text)
            sum_by_page.append(summary)
            print(f'{p_idx}: {summary}')
            total_s = time.time() - start_s
            print(f'Time elapsed: {total_s} seconds')
    
    df = pd.DataFrame(sum_by_page)
    df.columns = ['summaries']
    df.index.name = 'page_idx'
    df.to_csv(args.out_file)