'''
Created on Oct 3, 2021

@author: immanueltrummer
'''
import codexdb.code
import codexdb.engine
import gym.spaces
import math
import numpy as np

def result_cmp(ref_output, cmp_output):
    """ Compares query result output against reference.
    
    Args:
        ref_output: reference query result
        cmp_output: compare this against reference
    
    Returns:
        Number between 0 and 1 (1 is most similar)
    """
    ref_len = len(ref_output)
    cmp_len = len(cmp_output)
    return min(ref_len, cmp_len)/(1+max(ref_len, cmp_len))
    # ref_lines =ref_output.split('\n')
    # cmp_lines = cmp_output.split('\n')
        

class PromptEnv(gym.Env):
    """ Learn to generate optimal prompts for data processing. """
    
    def __init__(
            self, catalog, db_id, prompts, from_lang, 
            ref_lang, queries, reload_every):
        """ Initialize for given search space.
        
        Args:
            catalog: stores schema and location for databases
            db_id: ID of current database
            prompts: configuration for prompting
            from_lang: queries are written in this language
            ref_lang: reference results use this target language
            queries: list of queries to optimize
            reload_every: reload data after so many steps
        """
        self.catalog = catalog
        self.db_id = db_id
        self.prompts = prompts
        self.stages = ['transform', 'index', 'query']
        self.nr_stages = len(self.stages)
        self.from_lang = from_lang
        self.ref_lang = ref_lang
        self.queries = queries
        self.nr_queries = len(queries)
        self.reload_every = reload_every
        self.coder = codexdb.code.CodeGenerator(prompts)
        self.engine = codexdb.engine.ExecuteCode(catalog)
        self.to_langs = self.engine.supported_langs()
        self.nr_to_langs = len(self.to_langs)
        
        self.action_dims = self._action_dims()
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
        p_type = self.stages[self.cur_stage]
        schema = self.catalog.schema(self.db_id)
        files = self.catalog.files(self.db_id)
        task = self.queries[self.cur_query]
        tactics = self.prompts[p_type]['tactics']
        strategies = self.prompts[p_type]['strategies']
        
        to_lang_idx = math.floor(self.nr_to_langs * action[0])
        to_lang = self.to_langs[to_lang_idx]
        use_examples = True if action[1] > 0.5 else False
        
        tactics_p = []
        nr_tactics = len(tactics)
        for tac_idx in range(nr_tactics):
            tac_priority = action[2+tac_idx]
            if tac_priority < 0.2:
                tac_priority = 0
            tactics_p.append(tac_priority)
        
        nr_strategies = len(strategies)
        strat_idx = math.floor(nr_strategies * action[-1])
        strategy = strategies[strat_idx]
        
        # TODO: consider examples once available for all stages
        code = self.coder.generate(
            p_type, schema, files, self.from_lang, to_lang, 
            task, False, tactics_p, strategy)
        print(f'Generated code:\n---\n{code}\n---\n')
        approval = input('Do you approve executing this code? [y for yes]')
        if approval == 'y':
            success, output, elapsed_s = self.engine.execute(
                self.db_id, to_lang, code)
        else:
            success, output, elapsed_s = False, '', 1
        
        if not success:
            reward = 0
            done = True
        else:
            reward = 1
            done = False        
            if self.cur_stage == 2:
                # Query processing stage - compare to reference
                ref_code = self.coder.generate(
                    p_type, schema, files, self.from_lang, 
                    self.ref_lang, task, use_examples, 
                    tactics_p, strategy)
                ref_output = self.engine.execute(
                    self.db_id, self.ref_lang, ref_code)
                reward = result_cmp(ref_output, output)
                reward /= elapsed_s
            else:
                self.context.append(code)
        
        self.cur_stage = min(self.nr_stages-1, self.cur_stage+1)
        self.cur_query = self.cur_query+1 % self.nr_queries        
        self.cur_step += 1
        if self.cur_step >= self.reload_every:
            done = True
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
    
    def _observe(self):
        """ Generates an observation.
        
        Returns:
            Array containing stage and query number
        """
        return np.array([self.cur_stage, self.cur_query])