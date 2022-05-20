'''
Created on Jan 21, 2022

@author: immanueltrummer
'''
import collections
import json
import sqlglot.parser
import sqlglot.tokens
import sqlglot.expressions


class NlPlan():
    """ Represents a plan described in natural language. 
    
    Attributes:
        next_id: next integer ID to use for steps
    """
    next_id = 0
    
    def __init__(self):
        """ Initializes plan steps. 
        
        Args:
            id_steps: list of tuples (step ID and step)
        """
        # List of Tuple(Step ID, List of parts)
        self.id_steps = []
    
    def add_plan(self, plan):
        """ Add steps of another plan. 
        
        Args:
            plan: add steps of this plan (after current steps).
        """
        self.id_steps += plan.id_steps
        
    def add_step(self, step, at_end=True):
        """ Adds one step to plan. 
        
        Args:
            step: a list mixing strings and expressions
            at_end: whether to add step at the end
        
        Returns:
            integer ID of newly created step
        """
        step_id = self._step_ID()
        if at_end:
            self.id_steps.append((step_id, step))
        else:
            self.id_steps.insert(0, (step_id, step))
        return step_id
    
    def id_to_step(self):
        """ Returns dictionary mapping step IDs to steps. """
        id_to_step = {}
        for step_id, step in self.id_steps:
            id_to_step[step_id] = step
        return id_to_step
    
    def intersperse_step(self, step):
        """ Add given step after each current plan step. 
        
        Args:
            step: intersperse this step
        """
        nr_steps = len(self.id_steps)
        for _ in range(nr_steps):
            self.add_step(step, False)
        
        new_id_steps = []
        for i in range(nr_steps):
            new_id_steps.append(self.id_steps[i+nr_steps])
            new_id_steps.append(self.id_steps[i])
            
        self.id_steps = new_id_steps
        
    def last_step_id(self):
        """ Returns ID of last step or None. """
        if self.id_steps:
            return self.id_steps[-1][0]
        else:
            return None

    def step_ref_counts(self):
        """ Count number of references for each step.
        
        Returns:
            dictionary mapping step IDs to number of references
        """
        step_ref_counts = collections.defaultdict(lambda:0)
        for _, step in self.id_steps:
            for part in step:
                if isinstance(part, int):
                    step_ref_counts[part] += 1
        return step_ref_counts

    def steps(self, offset=0):
        """ Generates list of natural language plan steps. 
        
        Args:
            offset: add this number to each plan step index
        
        Returns:
            list of steps (strings)
        """
        nl_steps = [self._step_to_nl(step) for _, step in self.id_steps]
        return [f'{(idx+offset)}. {s}.' for idx, s in enumerate(nl_steps, 1)]

    def _index_of(self, search):
        """ Finds step by its index.
        
        Args:
            search: search for step with this ID
        
        Returns:
            index of corresponding step or None
        """
        for idx, (step_id, _) in enumerate(self.id_steps):
            if step_id == search:
                return idx + 1
        return None
    
    def _step_ID(self):
        """ Returns next unused step ID and advances counter. """
        NlPlan.next_id += 1
        return NlPlan.next_id - 1
        
    def _step_to_nl(self, step):
        """ Transforms plan step into natural language.
        
        Args:
            step: list of strings or expressions
        
        Returns:
            string describing the step in natural language
        """
        out_parts = []
        for in_part in step:
            if isinstance(in_part, str):
                out_parts.append(in_part)
            elif isinstance(in_part, int):
                in_idx = self._index_of(in_part)
                out_parts.append(f'results of Step {in_idx}')
            else:
                raise ValueError(f'Cannot translate plan step part: {in_part}')
        return ' '.join(out_parts)


class NlPlanner():
    """ Generates natural language query plan for query. """
    
    def __init__(self, id_case, quote_ids=True):
        """ Initializes planner. 
        
        Args:
            id_case: whether to consider letter case for identifiers
            quote_ids: whether to place all identifiers in quotes
        """
        self.id_case = id_case
        self.quote_ids = quote_ids
        self.tokenizer = sqlglot.tokens.Tokenizer()
        self.parser = sqlglot.parser.Parser()
    
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
        
        if isinstance(expression, sqlglot.expressions.Func):
            print(f'Function: {expression.key}')
        
        raise ValueError(f'Error - cannot process expression {expression.key}!')
    
    def plan(self, query):
        """ Parse query and return natural language plan. 
        
        Args:
            query: SQL query to plan for
        
        Returns:
            plan for query with steps described in natural language
        """
        tokens = self.tokenizer.tokenize(query)
        ast = self.parser.parse(tokens)[0]
        labels, plan = self.nl(ast)
        write_out = ['Write'] + labels + ["to file 'result.csv' (with header)"]
        plan.add_step(write_out)
        return plan
    
    def _alias(self, expression):
        """ Extract alias from alias expression. """
        assert expression.key == 'alias', 'No alias type expression'
        alias_id = expression.args['alias']
        return self._identifier_label(alias_id)
    
    def _select_nl(self, expression):
        """ Generates natural language plan for select query. """
        if expression.args['joins']:
            return self._filter_and_join(expression)

        else:
            from_labels, plan = self.nl(expression, 'from')
            last_labels = from_labels
            
            if expression.args.get('where'):
                where_expr = expression.args['where'].args['this']
                where_labels, where_prep = self.nl(where_expr)
                plan.add_plan(where_prep)
                where_step = ['Filter'] + from_labels + ['using'] + where_labels
                last_labels = [plan.add_step(where_step)]

            if expression.args.get('group'):
                group_expr = expression.args['group']
                group_labels, group_prep = self._expressions(group_expr)
                plan.add_plan(group_prep)
                group_step = \
                    ['Group rows from'] + last_labels + \
                    ['using'] + group_labels
                last_labels = [plan.add_step(group_step)]
            
            if expression.args.get('having'):
                having_expr = expression.args['having'].args['this']
                having_labels, having_prep = self.nl(having_expr)
                plan.add_plan(having_prep)
                having_step = \
                    ['Filter groups from'] + last_labels + \
                    ['using'] + having_labels
                last_labels = [plan.add_step(having_step)]
            
            if expression.args.get('order'):
                order_expr = expression.args['order']
                order_labels, order_prep = self._expressions(order_expr)
                plan.add_plan(order_prep)
                order_step = \
                    ['Order rows from'] + last_labels + \
                    ['using'] + order_labels
                last_labels = [plan.add_step(order_step)]
            
            if expression.args.get('limit'):
                limit_expr = expression.args['limit'].args['this']
                limit_labels, limit_prep = self.nl(limit_expr)
                plan.add_plan(limit_prep)
                limit_step = \
                    ['Keep only'] + limit_labels + \
                    ['rows from'] + last_labels
                last_labels = [plan.add_step(limit_step)]
            
            select_labels, select_prep = self._expressions(expression)
            plan.add_plan(select_prep)
            select_step = ['Create table with columns'] + select_labels + \
                ['from'] + last_labels
            last_labels = [plan.add_step(select_step)]
            
            if expression.args.get('distinct'):
                distinct_step = \
                    ['Only keep unique values in the rows from'] + \
                    last_labels
                last_labels = [plan.add_step(distinct_step)]
            
            return last_labels, plan
    
    def _filter_and_join(self, expression):
        """ Join tables and apply unary predicates. """
        # tbl_to_preds = self._unary_predicates(expression)
        from_expressions = expression.args['from'].args['expressions']
        join_expressions = expression.args.get('joins')
        
        tbl_expressions = from_expressions
        for join in join_expressions:
            tbl_expression = join.args['this']
            tbl_expressions += [tbl_expression]
        
        tables_aliases = []
        for tbl_expression in tbl_expressions:
            table = self._tables(tbl_expression).pop()
            alias = table
            if tbl_expression.key == 'alias':
                alias = self._alias(tbl_expression)
            tables_aliases += [(table, alias)]
        
        # Load data and assign aliases
        plan = NlPlan()
        for table, alias in tables_aliases:
            step = ['Load table'] + [table] + ['and store as'] + [alias]
            plan.add_step(step)
            
            # preds = tbl_to_preds[alias]
            # for pred in preds:
                # pred_label, pred_plan = self.nl(pred)
                # plan.add_plan(pred_plan)
                # step = ['Filter'] + [alias] + ['using'] + pred_label
                # plan.add_step(step)
        
        # Apply predicates in where clause
        if expression.args.get('where'):
            where_expr = expression.args['where'].args['this']
            conjuncts = self._conjuncts(where_expr)
            for pred in conjuncts:
                pred_labels, pred_plan = self.nl(pred)
                pred_plan = self._simplify_plan(pred_plan)
                tables = self._tables(pred)
                if len(tables) == 1:
                    table = tables.pop()
                    prefix = f'Filter {table}:'
                else:
                    prefix = 'Filter table:'
                pred_plan.id_steps[-1][1].insert(0, prefix)
                plan.add_plan(pred_plan)
                # plan.add_step(step)
        
        # Join tables considering join conditions
        left_label = tables_aliases[0][1]
        for idx, join in enumerate(join_expressions, 1):
            right_label = tables_aliases[idx][1]
            join = self._strip_tables(join)
            eq_label = self._join_eq_label(join)
            step = ['Join'] + [left_label] + ['with'] + \
                [right_label] + ['- condition:'] + [eq_label]
            left_label = plan.add_step(step)
        last_labels = [left_label]

        if expression.args.get('group'):
            group_expr = expression.args['group']
            group_expr = self._strip_tables(group_expr)
            group_labels, group_prep = self._expressions(group_expr)
            plan.add_plan(group_prep)
            group_step = ['Group'] + last_labels + ['by'] + group_labels
            last_labels = [plan.add_step(group_step)]
        
        if expression.args.get('having'):
            having_expr = expression.args['having'].args['this']
            having_expr = self._strip_tables(having_expr)
            having_labels, having_prep = self.nl(having_expr)
            plan.add_plan(having_prep)
            having_step = ['Filter groups from'] + last_labels + \
                ['using'] + having_labels
            last_labels = [plan.add_step(having_step)]
        
        if expression.args.get('order'):
            order_expr = expression.args['order']
            order_expr = self._strip_tables(order_expr)
            order_labels, order_prep = self._expressions(order_expr)
            plan.add_plan(order_prep)
            order_step = ['Order'] + last_labels + ['by'] + order_labels
            last_labels = [plan.add_step(order_step)]
        
        if expression.args.get('limit'):
            limit_expr = expression.args['limit'].args['this']
            limit_expr = self._strip_tables(limit_expr)
            limit_labels, limit_prep = self.nl(limit_expr)
            plan.add_plan(limit_prep)
            limit_step = ['Keep only'] + limit_labels + \
                ['rows from'] + last_labels
            last_labels = [plan.add_step(limit_step)]
        
        selectors = expression.args.get('expressions')
        select_labels = []
        for selector in selectors:
            selector = self._strip_tables(selector)
            select_cmd, select_prep = self.nl(selector)
            plan.add_plan(select_prep)
            step = ['Retrieve'] + select_cmd + ['from'] + last_labels
            select_label = plan.add_step(step)
            if select_labels:
                select_labels += [',']
            select_labels += [select_label]
        
        step = ['Create table with columns for'] + select_labels
        last_labels = [plan.add_step(step)]
        
        if expression.args.get('distinct'):
            distinct_step = ['Only keep unique rows from'] + last_labels
            last_labels = [plan.add_step(distinct_step)]

        return last_labels, plan
    
    def _agg_nl(self, expression, agg_name):
        """ Translates aggregate into natural language. 
        
        Args:
            expression: aggregate expression to translate
            agg_name: name of aggregate to use in description
        
        Returns:
            list of labels, plan preparing aggregate
        """
        arg_labels, prep = self.nl(expression, 'this')
        labels = [agg_name] + ['of'] + arg_labels
        return labels, prep
    
    def _avg_nl(self, expression):
        """ Translate average aggregate into natural language. """
        return self._agg_nl(expression, 'average')
    
    def _between_nl(self, expression):
        """ Translates between statement into natural language. """
        op = expression.args.get('this')
        low = expression.args.get('low')
        high = expression.args.get('high')
        op_label, op_prep = self.nl(op)
        low_label, low_prep = self.nl(low)
        high_label, high_prep = self.nl(high)
        plan = NlPlan()
        plan.add_plan(op_prep)
        plan.add_plan(low_prep)
        plan.add_plan(high_prep)
        step = ['Check if'] + op_label + ['is between'] + \
            low_label + ['and'] + high_label
        last_labels = [plan.add_step(step)]
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
        step = ['Check if'] + left + [comparator] + right
        last_labels = [plan.add_step(step)]
        return last_labels, plan

    def _column_nl(self, expression):
        """ Express a column reference in natural language. """
        labels, plan = self.nl(expression.args['this'])
        # labels += ['column']
        table = expression.args.get('table')
        if table:
            table_labels, table_prep = self.nl(table)
            plan.add_plan(table_prep)
            labels += ['in'] + table_labels
        database = expression.args.get('database')
        if database:
            db_labels, db_prep = self.nl(database)
            plan.add_plan(db_prep)
            labels += ['in'] + db_labels
        return labels, plan

    def _conjuncts(self, expression):
        """ Extract list of conjuncts from expression. """
        if expression.key == 'and':
            conjuncts = []
            conjuncts += [expression.args.get('this')]
            conjuncts += [expression.args.get('expression')]
            return conjuncts
        else:
            return [expression]

    def _count_nl(self, expression):
        """ Translate count aggregate into natural language. """
        count_args = expression.args.get('this')
        if count_args.args.get('this').key == 'star':
            return ['number of rows'], NlPlan()
        else:
            arg_labels, prep = self.nl(count_args)
            labels = ['count of rows without null values in'] + arg_labels
            return labels, prep

    def _eq_nl(self, expression):
        """ Translate equality condition into natural language. """
        return self._cmp(expression, 'equals')

    def _except_nl(self, expression):
        """ Translates SQL except expression into natural language. """
        return self._set_operation(expression, 'From', 'remove', None)

    def _expressions(self, expression):
        """ Translates associated expressions into natural language. """
        plan = NlPlan()
        labels = []
        for expr in expression.args.get('expressions'):
            new_labels, prep = self.nl(expr)
            plan.add_plan(prep)
            labels += new_labels + [', ']
        return labels[:-1], plan
    
    def _from_nl(self, expression):
        """ Translates from clause into natural language description. """
        last_label = None
        for expr in expression.args['expressions']:
            from_label, from_prep = self.nl(expr)
            if last_label is None:
                last_label = from_label
                plan = from_prep
            else:
                step = ['Join', last_label, 'with', from_label, '.']
                last_label = plan.add_step(step)
        return last_label, plan
    
    def _identifier_label(self, expression):
        """ Construct text label for identifier. """
        label = expression.args.get('this') or ''
        if not self.id_case:
            label = label.lower()
        if self.quote_ids or expression.args.get('quoted'):
            label = f"'{label}'"
        return label
    
    def _identifier_nl(self, expression):
        """ Express identifier (e.g., table name) in natural language. """
        label = self._identifier_label(expression)
        return [label], NlPlan()
    
    def _in_nl(self, expression):
        """ Translate SQL IN expression into natural language. """
        left_label, left_prep = self.nl(expression, 'this')
        right_label, right_prep = self.nl(expression, 'query')
        step = ['Check if'] + left_label + ['appears in'] + right_label
        plan = NlPlan()
        plan.add_plan(left_prep)
        plan.add_plan(right_prep)
        last_labels = [plan.add_step(step)]
        return last_labels, plan
    
    def _intersect_nl(self, expression):
        """ Translate set intersection into natural language. """
        distinct = expression.args.get('distinct')
        drop_duplicates = True if distinct is not None else False
        postfix = 'and eliminate duplicates' if drop_duplicates else None
        return self._set_operation(expression, 'Intersect', 'and', postfix)
    
    def _join_eq_label(self, expression):
        """ Translate equality join condition into natural language label. """
        predicate = expression.args['on']
        assert predicate.key == 'eq', 'No equality join predicate'
        left_op = predicate.args.get('this')
        right_op = predicate.args.get('expression')
        left_labels, _ = self._column_nl(left_op)
        right_labels, _ = self._column_nl(right_op)
        left_label = ' '.join(left_labels)
        right_label = ' '.join(right_labels)
        return left_label + ' equals ' + right_label
    
    def _join_nl(self, expression):
        """ Translates join expression into natural language. """
        raise NotImplementedError
    
    def _literal_nl(self, expression):
        """ Translates a literal into natural language. """
        text = expression.args.get('this') or ''
        try:
            float(text)
            is_string = False
        except:
            is_string = True
        # is_string = expression.args.get('is_string')
        if is_string:
            escape_code = sqlglot.tokens.Tokenizer.ESCAPE_CODE
            text = text.replace(escape_code, "'")
            text = f"'{text}'"
            if text == text.lower():
                text = text + ' (all lowercase)'
            # text = text.replace("'", "''")
            return [text], NlPlan()
        else:
            return [text], NlPlan()
    
    def _max_nl(self, expression):
        """ Translate maximum aggregate into natural language. """
        return self._agg_nl(expression, 'maximum')
    
    def _min_nl(self, expression):
        """ Translate minimum aggregate into natural language. """
        return self._agg_nl(expression, 'minimum')
    
    def _not_nl(self, expression):
        """ Express negation in natural language. """
        op_label, plan = self.nl(expression, 'this')
        step = ['Check if'] + op_label + ['is false']
        last_labels = [plan.add_step(step)]
        return last_labels, plan
    
    def _null_nl(self, _):
        """ Express SQL NULL value in natural language. """
        return 'unknown', NlPlan()
    
    def _ordered_nl(self, expression):
        """ Translates item in ORDER BY clause into natural language. """
        last_labels, plan = self.nl(expression, 'this')
        is_desc = True if expression.args.get('desc') else False
        direction = '(descending)' if is_desc else '(ascending)'
        return last_labels + [direction], plan

    def _gt_nl(self, expression):
        """ Translate greater than condition into natural language. """
        return self._cmp(expression, 'is greater than')

    def _gte_nl(self, expression):
        """ Translate greater or equal into natural language. """
        return self._cmp(expression, 'is greater or equal to')

    def _is_nl(self, expression):
        """ Translate SQL IS comparison into natural language. """
        return self._cmp(expression, 'is')

    def _like_nl(self, expression):
        """ Translate SQL LIKE into natural language. """
        return self._cmp(expression, 'matches')

    def _lt_nl(self, expression):
        """ Translate less than comparison into natural language. """
        return self._cmp(expression, 'is less than')

    def _lte_nl(self, expression):
        """ Translates less or equal than comparison into natural language. """
        return self._cmp(expression, 'is less than or equal to')
    
    def _neq_nl(self, expression):
        """ Translates inequality into natural language. """
        return self._cmp(expression, 'is not equal to')

    def _or_nl(self, expression):
        """ Translate logical or into natural language. """
        return self._cmp(expression, 'or')

    def _and_nl(self, expression):
        """ Translate logical and into natural language. """
        return self._cmp(expression, 'and')

    def _alias_nl(self, expression):
        """ Translate alias into natural language. """
        alias_labels, alias_prep = self.nl(expression, 'alias')
        this_labels, plan = self.nl(expression, 'this')
        plan.add_plan(alias_prep)
        last_labels = this_labels + ['(aka.'] + alias_labels + [')']
        return last_labels, plan

    def _paren_nl(self, expression):
        """ Translate parenthesis expression to natural language. """
        return self.nl(expression, 'this')
    
    def _set_operation(self, expression, prefix, connector, postfix):
        """ Translate set expression into natural language.
        
        Args:
            expression: SQL expression representing set operation
            prefix: start final step with this text
            connector: text between references to operands
            postfix: end final step with this text
        
        Returns:
            label and preparatory plan
        """
        left_label, left_prep = self.nl(expression, 'this')
        right_label, right_prep = self.nl(expression, 'expression')
        plan = NlPlan()
        plan.add_plan(left_prep)
        plan.add_plan(right_prep)
        step = [prefix] + left_label + [connector] + right_label
        if postfix is not None:
            step += [postfix]
        last_labels = [plan.add_step(step)]
        return last_labels, plan
    
    def _simplify_plan(self, plan):
        """ Try to simplify given plan by merging steps. 
        
        Args:
            plan: try to reduce number of steps in this plan
            
        Returns:
            simplified plan
        """
        id_to_step = plan.id_to_step()
        step_ref_counts = plan.step_ref_counts()
        for step_id, step in plan.id_steps:
            new_step = []
            for part in step:
                if isinstance(part, int):
                    ref_step = id_to_step[part]
                    if ref_step[0] == 'Check if':
                        new_step += ref_step[1:]
                        step_ref_counts[part] -= 1
                        if step_ref_counts[part] == 0:
                            del id_to_step[part]
                        continue
                
                new_step += [part]
            id_to_step[step_id] = new_step
        id_steps = sorted(id_to_step.items(), key=lambda t:t[0])
        
        new_plan = NlPlan()
        new_plan.id_steps = id_steps
        return new_plan
    
    def _star_nl(self, _):
        """ Translates star into natural language. """
        return ['all columns'], NlPlan()

    def _strip_tables(self, expression):
        """ Recursively strips table references from expression.
        
        Args:
            expression: strip table references from this expression
        
        Returns:
            expression without table references
        """
        def column_without_table(expression):
            """ Removes tables from column references. """
            if expression.key == 'column':
                if 'table' in expression.args:
                    del expression.args['table']
            return expression

        if isinstance(expression, str):
            return expression
        else:
            return expression.transform(
                lambda n:column_without_table(n))

    def _sum_nl(self, expression):
        """ Translate sum aggregate into natural language. """
        return self._agg_nl(expression, 'sum')

    def _table_nl(self, expression):
        """ Describe table in natural language. """
        table_labels, plan = self.nl(expression, 'this')
        step = ['Load data for table'] + table_labels
        last_labels = [plan.add_step(step)]
        return last_labels, plan
    
    def _tables(self, expression):
        """ Returns set of tables mentioned in expression. """
        tables = set()
        if isinstance(expression, list):
            for element in expression:
                tables.update(self._tables(element))
        
        elif isinstance(expression, sqlglot.expressions.Expression):
            if expression.key == 'table':
                tbl_expr = expression.args.get('this')
                tbl_label = self._identifier_label(tbl_expr)
                tables.add(tbl_label)
            else:
                for k, v in expression.args.items():
                    if k == 'table' and v is not None:
                        tbl_label = self._identifier_label(v)
                        tables.add(tbl_label)
                    else:
                        tables.update(self._tables(v))
            
        return tables
    
    def _unary_predicates(self, expression):
        """ Map tables to their unary predicates. """
        tbl_to_preds = collections.defaultdict(lambda:[])
        if expression.args.get('where'):
            where_expr = expression.args['where'].args['this']
            conjuncts = self._conjuncts(where_expr)
            for conjunct in conjuncts:
                tables = self._tables(conjunct)
                assert len(tables) == 1, 'Only unary predicates!'
                table = tables.pop()
                tbl_to_preds[table] += [conjunct]
        
        return tbl_to_preds
    
    def _neg_nl(self, expression):
        """ Translates negation into natural language. """
        labels, plan = self.nl(expression, 'this')
        return ['-'] + labels, plan

if __name__ == '__main__':
    
    with open('/Users/immanueltrummer/benchmarks/spider/results_dev.json') as file:
        test_cases = json.load(file)
        
    planner = NlPlanner(False)
    for idx, test_case in enumerate(test_cases[0:60:2]):
        db_id = test_case['db_id']
        query = test_case['query']
        print('-----------------------')
        print(f'Q{idx}: {db_id}/{query}')
        plan = planner.plan(query)
        for step in plan.steps():
            print(step)
    
    # query = "SELECT count(*) FROM student AS T1 JOIN has_pet AS T2 ON T1.stuid  =  T2.stuid WHERE T1.age  >  20"
    # query = "SELECT T1.CountryName FROM COUNTRIES AS T1 JOIN CONTINENTS AS T2 ON T1.Continent  =  T2.ContId JOIN CAR_MAKERS AS T3 ON T1.CountryId  =  T3.Country WHERE T2.Continent  =  'europe' GROUP BY T1.CountryName HAVING count(*)  >=  3"
    #query = "select count(*) from ta as a join tb as b on (a.x=b.x) where a.c = 1 and a.d = 2 and (b.i=1 or b.j=2)"
    # query = "SELECT T2.name FROM singer_in_concert AS T1 JOIN singer AS T2 ON T1.singer_id  =  T2.singer_id JOIN concert AS T3 ON T1.concert_id  =  T3.concert_id WHERE T3.year  =  2014"
    # query = "SELECT DISTINCT T1.Fname FROM student AS T1 JOIN has_pet AS T2 ON T1.stuid  =  T2.stuid JOIN pets AS T3 ON T3.petid  =  T2.petid WHERE T3.pettype  =  'cat' OR T3.pettype  =  'dog'"
    # planner = NlPlanner(False)
    # plan = planner.plan(query)
    # for step in plan.steps():
        # print(step)
    
    # with open('/Users/immanueltrummer/benchmarks/WikiSQL/data/results_test.json') as file:
        # test_cases = json.load(file)
        #
        #
    # for idx, test_case in enumerate(test_cases):
        # print(f'Idx: {idx}')
        # question = test_case['question']
        # query = test_case['query']
        # print(f'Question: {question}')
        # print(f'Query: {query}')
        # label, plan = planner.plan(query)
        # print(plan.steps())