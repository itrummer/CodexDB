'''
Created on Sep 21, 2021

@author: immanueltrummer
'''
def set_compare(ref_res, output):
    """ Compares reference result to generated output.
    
    Args:
        ref_res: reference result in JSON representation
        output: string output when executing generated code
    
    Returns:
        true iff all tokens in reference appear in output
    """
    for row in ref_res:
        for field in row:
            if str(field) not in output.replace('\\\\', '\\'):
                return False
    return True