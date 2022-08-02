# Overview

CodexDB allows users to specify natural language instructions, together with their SQL queries. It uses OpenAI's GPT-3 Codex model to generate code for query processing that complies with those instructions. This enables far-reaching customization, ranging from the selection of frameworks for query processing to custom logging output. In doing so, CodexDB blurs the line between user and developer.

# How to Run Benchmarks

The code under "/src/codexdb/bench/run.py" reads SQL queries from an input file and generates code that complies with additional instructions. 
It first performs a training run in which it solves 50 training queries with a high number of retries, increasing the chances to generate accurate code. 
Next, it uses the generated examples as part of the prompt (few-shot learning) to solve test queries with a lower number of retries.

## How to cite

```
@article{Trummer2022b,
author = {Trummer, Immanuel},
journal = {PVLDB},
number = {11},
pages = {2921 -- 2928},
title = {{CodexDB: Synthesizing code for query processing from natural language instructions using GPT-3 Codex}},
volume = {15},
year = {2022}
}
```
