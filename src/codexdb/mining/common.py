'''
Created on Sep 30, 2021

@author: immanueltrummer
'''
import openai

def summarize(text):
    """ Summarize text using OpenAI GPT-3 Codex.
    
    Args:
        text: the text to summarize
    
    Returns:
        one sentence summary
    """
    prompt = f'{text}\n\nTL;DR: In summary,'
    response = openai.Completion.create(
        engine='davinci-codex', prompt=prompt, 
        temperature=0, max_tokens=75)
    summary = response['choices'][0]['text']
    return summary
