'''
Created on Oct 3, 2021

@author: immanueltrummer
'''
import json
import openai


class CodeGenerator():
    """ Generates code using Codex. """
    
    def __init__(self, space_path):
        """ Initializes search space.
        
        Args:
            space_path: path to file describing search space
        """
        with open(space_path) as file:
            self.space = json.load(file)
    
    def generate(
            self, p_type, schema, files, from_lang,
            to_lang, task, use_examples=True, 
            tactics_p=None, strategy=None):
        """ Generate a piece of code solving specified task.
        
        Args:
            p_type: task type ('query' vs. 'transform')
            schema: JSON description of database schema
            files: names of files storing tables
            from_lang: query language
            to_lang: query processing language
            use_examples: whether to use example queries
            task: task description in source language
            tactics_p: assigns each tactics to priority
            strategy: high-level processing strategy
        """
        if from_lang == to_lang:
            return task
        from_lang = 'from_' + from_lang
        to_lang = 'to_' + to_lang        
        
        sample_parts = []
        if use_examples:
            sample_dbs = self.space['sample_databases']
            from_content = self.space[p_type][from_lang]
            sample_tasks = from_content['sample_tasks']
            sample_solutions = from_content[to_lang]['sample_solutions']
            
            for sample_task, solution in zip(sample_tasks, sample_solutions):
                sample_text = sample_task['task']
                sample_db_id = sample_task['db_id']
                sample_db = sample_dbs[sample_db_id]
                sample_prompt = self._prompt(
                    p_type, sample_db, files, from_lang, 
                    to_lang, sample_text, tactics_p, strategy)
                sample_parts.append(sample_prompt)
                sample_parts.append(solution)
        
        last_prompt = self._prompt(
            p_type, schema, files, from_lang, 
            to_lang, task, tactics_p, strategy)
        prompt = '\n'.join(sample_parts) + '\n' + last_prompt
        
        snippets = self.space[p_type][from_lang][to_lang]        
        marker = snippets['marker']
        completion = self._complete(prompt, marker)
        return completion.replace(marker, '')
    
    def _complete(self, prompt, marker):
        """ Complete prompt using Codex. 
        
        Args:
            prompt: initiate generation with this prompt
            marker: generation stops at marker text
        
        Returns:
            generated code, following prompt
        """
        try:
            response = openai.Completion.create(
                engine='davinci-codex', prompt=prompt, 
                temperature=0, max_tokens=500,
                stop=marker)
            return response['choices'][0]['text']
        except Exception as e:
            print(f'Error querying Codex: {e}')
            return ''
    
    def _db_info(self, schema, files):
        """ Generate description of database.
        
        Args:
            schema: description of database schema
            files: names to files storing tables
        
        Returns:
            list of description lines
        """
        lines = []
        tables = schema['table_names_original']
        all_columns = schema['column_names_original']
        nr_tables = len(tables)
        for tbl_idx in range(nr_tables):
            filename = files[tbl_idx]
            tbl_name = tables[tbl_idx]
            tbl_columns = [c[1] for c in all_columns if c[0] == tbl_idx]
            col_list = ', '.join(tbl_columns)
            line = f'Table {tbl_name} with columns {col_list}, ' \
                f'stored in {filename}.'
            lines.append(line)
        return lines
        
    def _eligible_tactics(self, tactics, precedence, used):
        """ Determine eligible next tactics.
        
        Args:
            tactics: available tactics
            precedence: precedence constraints
            used: tactics already used
        
        Returns:
            list of usable tactics IDs
        """
        nr_tactics = len(tactics)
        usable = set(range(nr_tactics))
        usable = usable.difference(used)
        for c in precedence:
            if c['F'] not in used:
                usable.discard(c['S'])
        return usable        
        
    def _plan(self, tactics, precedence, tactics_p):
        """ Generate list of ordered tactics.
        
        Args:
            tactics: list of available tactics
            precedence: ordering constraints
            tactics_p: priorities for tactics
        
        Returns:
            ordered list of tactics
        """
        ordered_ts = []
        used = set()
        while (self._eligible_tactics(tactics, precedence, used)):
            usable = self._eligible_tactics(tactics, precedence, used)
            use = max(usable, key=lambda t_id:tactics_p[t_id])
            used.add(use)
            if tactics_p[use] > 0:
                ordered_ts.append(tactics[use])
        return ordered_ts
    
    def _prompt(
            self, p_type, schema, files, from_lang,
            to_lang, task, tactics_p=None, strategy=None):
        """ Generate a prompt initiating code generation.
        
        Args:
            p_type: task type ('query' vs. 'transform')
            schema: JSON description of database schema
            files: names of files storing tables
            from_lang: query language
            to_lang: query processing language
            task: task description in source language
            tactics_p: assigns each tactics to priority
            strategy: high-level processing strategy
        """
        tactics = self.space[p_type]['tactics']
        precedence = self.space[p_type]['precedence']
        snippets = self.space[p_type][from_lang][to_lang]
        
        nr_tactics = len(tactics)
        if tactics_p is None:
            tactics_p = [1] * nr_tactics
        if strategy is None:
            strategy = ''
        
        line_pre = snippets['linepre']
        ordered_ts = self._plan(tactics, precedence, tactics_p)
        plan_lines = [f'{l_id+1}. {l}' for l_id, l in enumerate(ordered_ts)]
        plan = '\n'.join([line_pre + t for t in plan_lines])
        plan = plan.replace('<strategy>', strategy)
        
        db_lines = self._db_info(schema, files)
        db_info = '\n'.join([line_pre + l for l in db_lines])
        
        prompt = snippets['template']
        prompt = prompt.replace('<plan>', plan)
        prompt = prompt.replace('<task>', task)
        prompt = prompt.replace('<database>', db_info)
        return prompt

if __name__ == '__main__':
    generator = CodeGenerator('config/spaces.json')
    print(generator.space)
    print(generator.space['query']['from_nl']['to_cpp']['sample_solutions'])