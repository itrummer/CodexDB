'''
Created on Jan 28, 2022

@author: immanueltrummer
'''
import argparse

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('run_dir', type=str, help='Directory with results')
    args = parser.parse_args()
    
    