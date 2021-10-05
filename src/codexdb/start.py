'''
Created on Oct 3, 2021

@author: immanueltrummer
'''
import argparse
import sys

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('key', type=str, help='Key for OpenAI Codex access')
    parser.add_argument('data_dir', type=str, help='Data directory')
    parser.add_argument('src_lang', type=str, help='Source language (NL vs SQL)')
    args = parser.parse_args()
    
    src_lang = args.src_lang.lower()
    if src_lang not in ['nl', 'sql']:
        sys.exit(f'Unknown source language: {src_lang}')
    
    cmd = ''
    while not (cmd == 'quit'):
        cmd = input()
        print(f'Processing command "{cmd}" ...')