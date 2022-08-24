'''
Created on Aug 23, 2022

@author: immanueltrummer
'''
import argparse
import openai
import os
import pandas as pd
import pathlib
import streamlit as st
import sqlite3
import sys

cur_file_dir = os.path.dirname(__file__)
src_dir = pathlib.Path(cur_file_dir).parent
root_dir = src_dir.parent
sys.path.append(str(src_dir))
sys.path.append(str(root_dir))
print(f'sys.path: {sys.path}')

import codexdb.catalog
import codexdb.code
import codexdb.engine
import codexdb.solve

parser = argparse.ArgumentParser()
parser.add_argument('ai_key', type=str, help='Access key for OpenAI platform')
parser.add_argument('data_dir', type=str, help='Path to data directory')
args = parser.parse_args()

openai.api_key = args.ai_key
catalog = codexdb.catalog.DbCatalog(args.data_dir)
os.environ['KMP_DUPLICATE_LIB_OK']='True'

st.set_page_config(page_title='CodexDB')
st.markdown('''
# CodexDB
CodexDB generates customizable code for SQL processing via GPT-3 Codex.
''')


with st.expander('Data Source'):
    db_ids = catalog.db_ids()
    db_id = st.selectbox('Select source database:', options=db_ids)
    
    schema = catalog.schema(db_id)
    all_tables = schema['table_names_original']
    all_columns = schema['column_names_original']
    for table_idx, table in enumerate(all_tables): 
        columns = [c[1] for c in all_columns if c[0] == table_idx]
        st.write(f'{table}({", ".join(columns)})')


with st.expander('Model Configuration'):
    
    model_ids = ['code-cushman-001', 'code-davinci-002']
    model_id = st.selectbox(
        'Select GPT-3 Codex Model:', 
        options=model_ids, index=1)
    
    start_temp = float(st.slider(
        'Start temperature:', 
        min_value=0.0, max_value=1.0))
    final_temp = float(st.slider(
        'Final temperature:',
        min_value=0.0, max_value=1.0))


with st.expander('Prompt Configuration'):
       
    prompt_styles = ['query', 'plan']
    prompt_style = st.selectbox(
        'Select prompt style:', 
        options=prompt_styles, index=1)
    
    nr_samples = int(st.slider(
        'Number of samples in prompt:', 
        min_value=0, max_value=6))


with st.expander('Code Customization'):
    mod_start = st.text_input('General instructions (natural language):')
    mod_between = st.text_input('Per-step instructions (natural language):')
    mod_end = ''


id_case = 0
query = st.text_input('Write SQL query:')

max_tries = int(st.slider(
    'Number of generation tries:',
    min_value=1, max_value=10))

examples = []
temp_delta = final_temp - start_temp
temp_step = 0 if max_tries == 1 else temp_delta / (max_tries - 1.0)
test_case = {'question':'', 'query':query, 'db_id':db_id}
reorder = False if 'order by' in query.lower() else True

coder = codexdb.code.PythonGenerator(
    catalog, examples, nr_samples, 
    prompt_style, model_id, 
    id_case=id_case,
    mod_start=mod_start, 
    mod_between=mod_between, 
    mod_end=mod_end)
engine = codexdb.engine.PythonEngine(
    catalog, id_case)


if st.button('Generate Code'):
    
    sqlite_path = f'{args.data_dir}/database/{db_id}/{db_id}.sqlite'
    with sqlite3.connect(sqlite_path) as con:
        ref_result = pd.read_sql_query(query, con)
    
    for try_idx in range(max_tries):
        temperature = start_temp + temp_step * try_idx
        gen_stats, code = coder.generate(test_case, temperature)
        st.code(code, language='python')
        
        executed, codb_result, elapsed_s = engine.execute(db_id, code, 30)
        comparable, nr_diffs, similarity = codexdb.solve.result_cmp(
            ref_result, codb_result, reorder)
        st.write(f'Result similarity: {similarity}')