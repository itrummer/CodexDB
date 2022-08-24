'''
Created on Aug 23, 2022

@author: immanueltrummer
'''
import argparse
import os
import pathlib
import streamlit as st
import sys

cur_file_dir = os.path.dirname(__file__)
src_dir = pathlib.Path(cur_file_dir).parent
root_dir = src_dir.parent
sys.path.append(str(src_dir))
sys.path.append(str(root_dir))
print(f'sys.path: {sys.path}')

import codexdb.catalog

parser = argparse.ArgumentParser()
parser.add_argument('ai_key', type=str, help='Access key for OpenAI platform')
parser.add_argument('data_dir', type=str, help='Path to data directory')
args = parser.parse_args()

catalog = codexdb.catalog.DbCatalog(args.data_dir)
os.environ['KMP_DUPLICATE_LIB_OK']='True'

st.set_page_config(page_title='CodexDB')
st.markdown('''
# CodexDB
CodexDB generates customizable code for SQL processing via GPT-3 Codex.
''')

with st.expander('Prompt Configuration'):
    model_ids = ['code-cushman-001', 'code-davinci-002']
    model_id = st.selectbox(
        'Select GPT-3 Codex Model:', 
        options=model_ids, index=1)
    
    prompt_styles = ['query', 'plan']
    prompt_style = st.selectbox(
        'Select prompt style:', 
        options=prompt_styles, index=1)
    
    nr_samples = int(st.slider(
        'Number of samples in prompt:', 
        min_value=0, max_value=6))
    
    nr_tries = int(st.slider(
        'Number of generation tries:',
        min_value=1, max_value=10))

with st.expander('Code Customization'):
    mod_start = st.text_input('General instructions (natural language):')
    mod_between = st.text_input('Per-step instructions (natural language):')
    mod_end = ''

db_ids = catalog.db_ids()
db_id = st.selectbox('Select source database:', options=db_ids)

id_case = 0
query = st.text_input('Write SQL query:')

if st.button('Generate Code'):
    examples = []
    coder = codexdb.code.PythonGenerator(
        catalog, examples, nr_samples, 
        prompt_style, model_id, 
        id_case=id_case,
        mod_start=mod_start, 
        mod_between=mod_between, 
        mod_end=mod_end)
    engine = codexdb.engine.PythonEngine(
        catalog, id_case)