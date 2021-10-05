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
            to_lang, task, tactics_p=None, strategy=None):
        """ Generate a piece of code solving specified task.
        
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
        if from_lang == to_lang:
            return task
        
        tactics = self.spaces[p_type]['tactics']
        precedence = self.spaces[p_type]['precedence']
        snippets = self.spaces[p_type][from_lang][to_lang]
        
        nr_tactics = len(tactics)
        if tactics_p is None:
            tactics_p = [1] * nr_tactics
        if strategy is None:
            strategy = ''
        
        line_pre = snippets['linepre']
        ordered_ts = self._plan(tactics, precedence, tactics_p)
        plan = '\n'.join([line_pre + t for t in ordered_ts])
        plan = plan.replace('<strategy>', strategy)
        
        db_lines = self._db_info(schema, files)
        db_info = '\n'.join([line_pre + l for l in db_lines])
        
        prompt = snippets['template']
        prompt = prompt.replace('<plan>', plan)
        prompt = prompt.replace('<task>', task)
        prompt = prompt.replace('<database>', db_info)
        
        completion = self._complete(prompt)
        marker = snippets['marker']
        return completion.replace(marker, '')
    
    def _complete(self, prompt):
        """ Complete prompt using Codex. 
        
        Args:
            prompt: initiate generation with this prompt
        
        Returns:
            generated code, following prompt
        """
        try:
            response = openai.Completion.create(
                engine='davinci-codex', prompt=prompt, 
                temperature=0, max_tokens=150)
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
                usable.remove(c['S'])
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
        used = {}
        while (self._eligible_tactics(tactics, precedence, used)):
            usable = self._eligible_tactics(tactics, precedence, used)
            use = max(usable, key=lambda t_id:tactics_p[t_id])
            used.add(use)
            ordered_ts.append(tactics[use])
        return ordered_ts


if __name__ == '__main__':
    generator = CodeGenerator('config/spaces.json')
    print(generator.space)
    print(generator.space['from_nl'])
    print(generator.space['tactics'])