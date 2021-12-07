'''
Created on Oct 3, 2021

@author: immanueltrummer
'''
import codexdb.code
import codexdb.engine
import gym.spaces
import math
import numpy as np
import pandas as pd

class PromptEnv(gym.Env):
    """ Learn to generate optimal prompts for data processing. """
    
    def __init__(
            self, catalog, prompts, from_lang, ref_lang, 
            test_cases, reload_every=float('inf')):
        """ Initialize for given search space.
        
        Args:
            catalog: stores schema and location for databases
            prompts: configuration for prompting
            from_lang: queries are written in this language
            ref_lang: reference results use this target language
            test_cases: questions, optionally with associated results
            reload_every: reload data after so many steps
        """
        self.catalog = catalog
        self.prompts = prompts
        self.stages = ['query']
        self.nr_stages = len(self.stages)
        self.from_lang = from_lang
        self.ref_lang = ref_lang
        self.test_cases = test_cases
        self.nr_queries = len(test_cases)
        self.reload_every = reload_every
        self.coder = codexdb.code.CodeGenerator(prompts)
        self.engine = codexdb.engine.ExecuteCode(catalog)
        self.to_langs = self.engine.supported_langs()
        self.nr_to_langs = len(self.to_langs)
        
        self.nr_action_dims = self._action_dims()
        action_shape = (self.nr_action_dims,)
        self.observation_space = gym.spaces.Box(shape=(2,), low=0, high=1)
        self.action_space = gym.spaces.Box(shape=action_shape, low=0, high=1)
        self.reset()
    
    def step(self, action):
        """ Execute given action and return reward. 
        
        Args:
            action: Selects prompt for next step
        
        Returns:
            Observation, reward, done flag, meta-data
        """
        cur_test = self.test_cases[self.cur_query]
        db_id = cur_test['db_id']
        p_type = self.stages[self.cur_stage]
        schema = self.catalog.schema(db_id)
        files = self.catalog.files(db_id)
        task = cur_test['question']
        tactics = self.prompts[p_type]['tactics']
        strategies = self.prompts[p_type]['strategies']
        
        to_lang_idx = math.floor(self.nr_to_langs * action[0])
        to_lang_idx = min(to_lang_idx, self.nr_to_langs - 1)
        to_lang = self.to_langs[to_lang_idx]
        use_examples = True if action[1] > 0.5 else False
        
        to_lang = 'python'
        use_examples = False
        
        tactics_p = []
        nr_tactics = len(tactics)
        for tac_idx in range(nr_tactics):
            tac_priority = action[2+tac_idx]
            if tac_priority < 0.2:
                tac_priority = 0
            tactics_p.append(tac_priority)
        
        nr_strategies = len(strategies)
        strat_idx = math.floor(nr_strategies * action[-1])
        strat_idx = min(strat_idx, nr_strategies - 1)
        strategy = strategies[strat_idx]
        
        code = self.coder.generate(
            self.context, p_type, schema, files, self.from_lang, 
            to_lang, task, use_examples, tactics_p, strategy)
        print(f'Generated code:\n-------\n{code}\n-------\n')
        success, output, elapsed_s = self.engine.execute(
            db_id, to_lang, code)
        print(f'CodexDB successful: {success} in {elapsed_s}s')
        
        stage_name = self.stages[self.cur_stage]
        if success and not (stage_name == 'query'):
            self.context.append(code)
        reward = self._calculate_reward(
            success, elapsed_s, output, 
            schema, files, task)
        
        self.cur_stage = min(self.nr_stages-1, self.cur_stage+1)
        self.cur_query = self.cur_query+1 % self.nr_queries        
        self.cur_step += 1
        if self.cur_step >= self.reload_every:
            done = True
        else:
            done = False
        observation = self._observe()
        return observation, reward, done, {}
    
    def reset(self):
        """ Reset stage, query, and step. """
        self.cur_stage = 0
        self.cur_query = 0
        self.cur_step = 0
        self.context = []
        return self._observe()
    
    def _action_dims(self):
        """ Calculate number of action dimensions required. 
        
        Returns:
            Number of required action dimensions.
        """
        max_dims = 0
        for stage in self.stages:
            tactics = self.prompts[stage]['tactics']
            strats = self.prompts[stage]['strategies']
            # Language, examples, tactics, strategy
            dims = 2 + len(tactics) + len(strats)
            max_dims = max(dims, max_dims)
        return max_dims
    
    def _calculate_reward(
            self, success, elapsed_s, output, 
            schema, files, task):
        """ Calculate reward for generated code.
        
        Args:
            success: if generated code is executable
            elapsed_s: execution time in seconds
            output: output of generated code
            schema: schema of current database
            files: files containing table data
            task: query description
        
        Returns:
            reward value
        """
        if not success:
            reward = 0
        else:
            reward = 1
            cur_test = self.test_cases[self.cur_query]
            if 'results' in cur_test:
                ref_output = pd.DataFrame(cur_test['results'])
            else:
                db_id = cur_test['db_id']
                ref_code = self.coder.generate(
                    [], 'query', schema, files, self.from_lang, 
                    self.ref_lang, task, False)
                ref_success, ref_output, ref_s = self.engine.execute(
                    db_id, self.ref_lang, ref_code)
                print(f'Reference successful: {ref_success} in {ref_s}s')
            reward = self._result_cmp(ref_output, output)
            reward /= elapsed_s
        return reward
    
    def _observe(self):
        """ Generates an observation.
        
        Returns:
            Array containing stage and query number
        """
        return np.array([self.cur_stage, self.cur_query])
    
    def _result_cmp(self, ref_output, cmp_output):
        """ Compares query result output against reference.
        
        Args:
            ref_output: reference query result
            cmp_output: compare this against reference
        
        Returns:
            Number between 0 and 1 (1 is most similar)
        """
        print(f'-- CodexDB output:\n{cmp_output}\n--\n')
        print(f'-- Reference output:\n{ref_output}\n--\n')
        ref_output.reindex()
        cmp_output.reindex()
        try:
            diffs = ref_output.compare(cmp_output, align_axis=0)
            print(f'-- Differences:\n{diffs}\n--\n')
            return 1.0/diffs.shape[0]
        except:
            print('(Incomparable)')
            return 0
        #
        # ref_len = ref_output.shape[0]
        # cmp_len = cmp_output.shape[0]
        # print(f'ref_len: {ref_len}; cmp_len: {cmp_len}')
        # if ref_len == cmp_len:
            # ref_output.reindex()
            # cmp_output.reindex()
            # diffs = ref_output.compare(cmp_output, align_axis=0)
            # print(f'-- Differences:\n{diffs}\n--\n')
            # return 1.0/diffs.shape[0]
        # else:
            # return 0