'''
Created on Oct 3, 2021

@author: immanueltrummer
'''
import openai


class CodeGenerator():
    """ Generates code using Codex. """
    
    def __init__(self, prompts):
        """ Initializes search space.
        
        Args:
            prompts: JSON object configuring prompts
        """
        self.prompts = prompts
    
    def generate(
            self, context, p_type, schema, files, 
            from_lang, to_lang, task, use_examples=True, 
            tactics_p=None, strategy=None):
        """ Generate a piece of code solving specified task.
        
        Args:
            context: text snippets for prompt prefix
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
        print(f'Generating code {p_type} from {from_lang} to {to_lang}')
        if from_lang == to_lang:
            return task
        elif to_lang == 'dummy':
            return ''
        from_lang = 'from_' + from_lang
        to_lang = 'to_' + to_lang
        
        sample_parts = []
        if use_examples:
            sample_dbs = self.prompts['sample_databases']
            if from_lang in self.prompts[p_type]:
                from_content = self.prompts[p_type][from_lang]
            else:
                from_content = self.prompts[p_type]['from_*']
            sample_tasks = from_content['sample_tasks']
            solution_links = from_content[to_lang]['sample_solution_links']
            sample_solutions = []
            for l in solution_links:
                with open(l) as file:
                    sample_solution = file.read()
                    sample_solutions.append(sample_solution)
            
            for sample_task, solution in zip(sample_tasks, sample_solutions):
                sample_text = sample_task['task']
                sample_db_id = sample_task['db_id']
                sample_db = sample_dbs[sample_db_id]
                sample_tables = sample_db['table_names_original']
                sample_files = [f'{t}.csv' for t in sample_tables]
                sample_prompt = self._prompt(
                    p_type, sample_db, sample_files, from_lang, 
                    to_lang, sample_text, tactics_p, strategy)
                sample_parts.append(sample_prompt)
                sample_parts.append(solution)
        
        # last_prompt = self._prompt(
            # p_type, schema, files, from_lang, 
            # to_lang, task, tactics_p, strategy)
        # prompt = '\n'.join(context) + \
            # '\n'.join(sample_parts[0:2]) + \
            # '\n' + last_prompt
        last_prompt = self._prompt(
            p_type, schema, files, from_lang, 
            to_lang, task, tactics_p, strategy)
        prompt = '\n'.join(context) + \
            '\n'.join(sample_parts) + \
            '\n' + last_prompt
        
        snippets = self._snippets(p_type, from_lang, to_lang)
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
            print(prompt)
            response = openai.Completion.create(
                engine='davinci-codex', prompt=prompt, 
                temperature=0, max_tokens=400,
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
        print(f'Prompt for {p_type} from {from_lang} to {to_lang}')
        if to_lang == 'to_dummy':
            return ''
        tactics = self.prompts[p_type]['tactics']
        precedence = self.prompts[p_type]['precedence']
        snippets = self._snippets(p_type, from_lang, to_lang)
        
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
    
    def _snippets(self, p_type, from_lang, to_lang):
        """ Return snippets for most specific source language.
        
        Args:
            p_type: type of prompt (i.e., processing stage)
            from_lang: translate query from this language
            to_lang: execute query using this language
        
        Returns:
            prompt snippets for specified source language or generalization
        """
        if from_lang in self.prompts[p_type]:
            return self.prompts[p_type][from_lang][to_lang]
        else:
            return self.prompts[p_type]['from_*'][to_lang]

if __name__ == '__main__':
    generator = CodeGenerator('config/spaces.json')
    print(generator.space)
    print(generator.space['query']['from_nl']['to_cpp']['sample_solutions'])