CodexDB synthesizes query-specific code for processing SQL queries using OpenAI's GPT-3 Codex model. Users customize generated code using natural language instructions. For instance, lay users may describe, in natural language, non-standard output to generate that helps debug their SQL queries. Advanced users may instruct the system to use specific techniques or libraries for query processing, enabling fast prototyping. This talk gives an overview of CodexDB:

<p align="center">
<iframe width="560" height="315" src="https://www.youtube.com/embed/vp5kXKnutSk?start=1786" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
</p>

# Implementation Details

CodexDB is a framework on top of OpenAI's GPT-3 Codex model. Given an SQL query and natural language instructions, CodexDB automatically generates a suitable prompt - a small text document instructing GPT-3 to generate code for query processing. This prompt contains a text description of the database schema and file locations. The largest part is an auto-generated query plan, described in _natural language_, that describes processing steps at a high level of abstraction. User instructions, inserted into the prompt as well, help GPT-3 to map abstract processing steps to concrete code snippets.


# Publications

- **VLDB 2022** CodexDB: synthesizing code for query processing from natural language instructions using GPT-3 Codex. _Immanuel Trummer_.
