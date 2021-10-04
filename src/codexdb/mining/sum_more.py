'''
Created on Sep 30, 2021

@author: immanueltrummer
'''
import argparse
import codexdb.mining.common
import openai
import pandas as pd
import re

def get_text_chunks(df):
    """ Extracts chunks of text from data frame.
    
    Args:
        df: data frame containing summary snippets
    
    Returns:
        list of text chunks
    """
    step = 100
    df_chunks = [df[i:i+step] for i in range(0, df.shape[0], step)]
    return ['\n'.join(df.iloc[:,1]) for df in df_chunks]

def polished(summary):
    """ Polish summary, e.g. by cutting and trimming it.
    
    Args:
        summary: summary text to polish
    
    Returns:
        (part of) polished summary
    """
    first_sentence = re.search('.*\.', summary)
    if first_sentence:
        return first_sentence.group().strip()
    else:
        return summary.strip()


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('key', type=str, help='Access key for OpenAI')
    parser.add_argument('in_path', type=str, help='Path to input file')
    args = parser.parse_args()
    
    openai.api_key = args.key
    df = pd.read_csv(args.in_path)
    print(df.info())
    df['summaries'] = df.apply(lambda r:polished(r['summaries']), axis=1)
    t_chunks = get_text_chunks(df)
    
    sums = []
    for t in t_chunks:
        summary = codexdb.mining.common.summarize(t)
        sums.append(summary)
        print(summary)