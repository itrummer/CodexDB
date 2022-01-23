'''
Created on Jan 21, 2022

@author: immanueltrummer
'''

class NlPlan():
    """ Represents a plan described in natural language. 
    
    Attributes:
        next_id: next integer ID to use for steps
    """
    next_id = 0
    
    def __init__(self, prefix):
        """ Initializes plan steps. 
        
        Args:
            prefix: use this string as line prefix for output
        """
        self.prefix = prefix
        # List of Tuple(Step ID, List of parts)
        self.id_steps = []
    
    def __repr__(self):
        """ Generates string representation of plan for prompt. 
        
        Returns:
            plan represented as string
        """
        nl_steps = []
        for idx, (_, step) in enumerate(self.id_steps):
            nl_step = self._step_to_nl(idx, step)
            nl_steps.append(nl_step)
        parts = [f'{self.prefix} {(idx+1)}. {s}' for s in nl_steps]
        return '\n'.join(parts)

    def add_plan(self, plan):
        """ Add steps of another plan. 
        
        Args:
            plan: add steps of this plan (after current steps).
        """
        self.id_steps += plan.id_steps
        
    def add_step(self, step):
        """ Adds one step to plan. 
        
        Args:
            step: a list mixing strings and expressions
        
        Returns:
            integer ID of newly created step
        """
        step_id = self._step_ID()
        self.id_steps.append((step_id, step))
        return step_id

    def last_step_id(self):
        """ Returns ID of last step or None. """
        if self.id_steps:
            return self.id_steps[-1][0]
        else:
            return None

    def _index_of(self, search):
        """ Finds step by its index.
        
        Args:
            search: search for step with this ID
        
        Returns:
            index of corresponding step or None
        """
        for idx, (step_id, _) in enumerate(self.id_steps):
            if step_id == search:
                return idx
        return None
    
    def _step_ID(self):
        """ Returns next unused step ID and advances counter. """
        NlPlan.next_id += 1
        return NlPlan.next_id - 1
        
    def _step_to_nl(self, idx, step):
        """ Transforms plan step into natural language.
        
        Args:
            idx: index of plan step in plan (zero-based)
            step: list of strings or expressions
        
        Returns:
            string describing the step in natural language
        """
        out_parts = []
        for in_part in step:
            if isinstance(in_part, str):
                out_parts.append(in_part)
            elif isinstance(in_part, int):
                in_idx = self._index_of(in_part, idx)
                out_parts.append(f'results of step {in_idx}')
        return ' '.join(out_parts)


class NlPlanner():
    """ Generates natural language query plan for query. """
    
    def __init__(self, line_prefix):
        """ Initializes with given line prefix. 
        
        Args:
            line_prefix: every line is prefixed by this string
        """
        self.line_prefix = line_prefix
    
    def nl(self, expression, key=None):
        """ Returns a natural language plan for given expression. 
        
        Args:
            expression: an SQL expression
            key: transform this attribute
        
        Returns:
            a label list to refer to expression in text, preparatory steps
        """
        if not expression:
            return ['']
        
        if isinstance(expression, str):
            return [expression]
        
        if key:
            return self.nl(expression.args.get(key))
        
        handler_name = f'_{expression.key}_nl'
        if hasattr(self, handler_name):
            return getattr(self, handler_name)(expression)
        
        raise ValueError(f'Error - cannot process expression {expression}!')
    
    def _select_nl(self, expression):
        """ Generates natural language plan for select query. """
        from_labels, plan = self.nl(expression, 'from')
        last_labels = from_labels
        
        for join_expr in expression.args.get("joins", []):
            join_labels, join_prep = self.nl(join_expr)
            plan.add_plan(join_prep)
            join_step = ['Join '] + last_labels + [' and '] + join_labels + ['.']
            last_labels = [plan.add_step(join_step)]
        
        if self.args.get('where'):
            where_expr = expression.args['where'].args['this']
            where_labels, where_prep = self.nl(where_expr)
            plan.add_plan(where_prep)
            where_step = \
                ['Filter '] + from_labels + [' if '] + \
                where_labels + [' is true.']
            last_labels = [plan.add_step(where_step)]
        
        if self.args.get('group'):
            group_expr = expression.args['group'].args['this']
            group_labels, group_prep = self._expressions(group_expr)
            plan.add_plan(group_prep)
            group_step = \
                ['Group rows from '] + last_labels + \
                [' using '] + group_labels + ['.']
            last_labels = [plan.add_step(group_step)]
        
        if self.args.get('having'):
            having_expr = expression.args['having'].args['this']
            having_labels, having_prep = self.nl(having_expr)
            plan.add_plan(having_prep)
            having_step = \
                ['Filter groups from '] + last_labels + \
                [' using '] + having_labels + ['.']
            last_labels = [plan.add_step(having_step)]
        
        if self.args.get('order'):
            order_expr = expression.args['order']
            order_labels, order_prep = self._expressions(order_expr)
            plan.add_plan(order_prep)
            order_step = \
                ['Order rows from '] + last_labels + \
                [' using '] + order_labels + ['.']
            last_labels = [plan.add_step(order_step)]
        
        if self.args.get('limit'):
            limit_expr = expression.args['limit'].args['this']
            limit_labels, limit_prep = self.nl(limit_expr)
            plan.add_plan(limit_prep)
            limit_step = \
                ['Keep only '] + limit_labels + \
                [' rows from '] + last_labels + ['.']
            last_labels = [plan.add_step(limit_step)]
        
        select_labels, select_prep = self._expressions(expression)
        plan.add_plan(select_prep)
        select_step = ['Select '] + select_labels + ['.']
        last_labels = [plan.add_step(select_step)]
        
        if expression.args.get('distinct'):
            distinct_step = \
                ['Only keep unique values in the rows from '] + \
                last_labels + ['.']
            last_labels = [plan.add_step(distinct_step)]
        
        return last_labels, plan
    
    def _binary(self, expression):
        """ Pre-processes a generic binary expression. 
        
        Args:
            expression: a generic binary expression
        
        Returns:
            tuple: left labels, right labels, combined preparation
        """
        left_labels, plan = self.nl(expression, 'this')
        right_labels, right_prep = self.nl(expression, 'expression')
        plan.add_plan(right_prep)
        return left_labels, right_labels, plan
    
    def _cmp(self, expression, comparator):
        """ Processes a binary comparison.
        
        Args:
            expression: a binary comparison expression
            comparator: natural language comparator
        
        Returns:
            labels representing comparison result, corresponding plan
        """
        left, right, plan = self._binary(expression)
        step = ['Check if '] + left + [comparator] + right + ['.']
        last_labels = plan.add_step(step)
        return last_labels, plan

    def _column_nl(self, expression):
        """ Express a column reference in natural language. """
        column = expression.args["this"]
        labels = [f'Column {column}']
        table = expression.args.get('table')
        if table:
            labels += [f' in table {table}']
        database = expression.args.get('database')
        if database:
            labels += [f' in database {database}']
        return labels, NlPlan()

    def _expressions(self, expression):
        """ Translates associated expressions into natural language. """
        plan = NlPlan()
        labels = []
        for expr in expression.args.get('expressions'):
            label, prep = self.nl(expr)
            plan.add_plan(prep)
            labels += [label]
        if len(labels) > 1:
            labels = [i for l in labels for i in [l, ', ']][:-1]
            labels = labels[0:-1] + ['and '] + labels[-1:]
        return labels, plan
    
    def _literal_nl(self, expression):
        """ Translates a literal into natural language. """
        text = expression.args.get('this') or ''
        is_string = expression.args.get('is_string')
        if is_string:
            return f"'{text}'"
        else:
            return text

    def _null_nl(self, _):
        """ Express SQL NULL value in natural language. """
        return 'unknown'
    
    def _ordered_nl(self, expression):
        """ Translates item in ORDER BY clause into natural language. """
        last_labels, plan = self.nl(expression, 'this')
        is_desc = True if expression.args.get('desc') else False
        direction = ' (descending) ' if is_desc else ' (ascending) '
        return last_labels + [direction], plan
    
    def _eq_nl(self, expression):
        """ Translate equality condition into natural language. """
        return self._cmp(expression, ' equals ')

    def _gt_nl(self, expression):
        """ Translate greater than condition into natural language. """
        return self._cmp(expression, ' is greater than ')

    def _gte_nl(self, expression):
        """ Translate greater or equal into natural language. """
        return self._cmp(expression, ' is greater or equal to ')

    def _is_nl(self, expression):
        """ Translate SQL IS comparison into natural language. """
        return self._cmp(expression, ' is ')

    def _like_nl(self, expression):
        """ Translate SQL LIKE into natural language. """
        return self._cmp(expression, ' matches ')

    def _lt_nl(self, expression):
        """ Translate less than comparison into natural language. """
        return self._cmp(expression, ' is less than ')

    def _lte_nl(self, expression):
        """ Translates less or equal than comparison into natural language. """
        return self._cmp(expression, ' is less than or equal to ')
    
    def _neq_nl(self, expression):
        """ Translates inequality into natural language. """
        return self._cmp(expression, ' is not equal to ')

    def _or_nl(self, expression):
        """ Translate logical or into natural language. """
        return self._cmp(expression, ' or ')

    def _and_nl(self, expression):
        """ Translate logical and into natural language. """
        return self._cmp(expression, ' and ')
    
    def _from_nl(self, expression):
        """ Translates from clause into natural language description. """
        last_label = None
        for expr in expression.args['expressions']:
            from_label, from_prep = self.nl(expr)
            if last_label is None:
                last_label = from_label
                plan = from_prep
            else:
                step = ['Join ', last_label, ' with ', from_label, '.']
                last_label = plan.add_step(step)
        return last_label, plan