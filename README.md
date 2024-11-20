# Overview

CodexDB allows users to specify natural language instructions, together with their SQL queries. It uses OpenAI's GPT-3 Codex model to generate code for query processing that complies with those instructions. This enables far-reaching customization, ranging from the selection of frameworks for query processing to custom logging output. In doing so, CodexDB blurs the line between user and developer.

# Setup

The following instructions have been tested on an EC2 instance of type t2.medium with Ubuntu 22.04 OS, Python 3.12, and 25 GB of disk space.

1. After logging into the EC2 instance, run the following command (from ```/home/ubuntu```):
```
git clone https://github.com/itrummer/CodexDB
```
2. Switch into the CodexDB root directory:
```
cd CodexDB/
```
3. Install pip if it is not yet installed, e.g., run:
```
sudo apt update
sudo apt install python3-pip
```
4. Create and activate a virtual environment and use pip to install dependencies:
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
5. Download and unzip the SPIDER dataset for benchmarking:
```
cd ..
pip install gdown
gdown 1iRDVHLr4mX2wQKSgA9J8Pire73Jahh0m
sudo apt install unzip
unzip spider.zip
```
6. Pre-process the SPIDER data set:
```
cd CodexDB
PYTHONPATH=src python3 src/codexdb/prep/spider.py /home/ubuntu/spider
```
7. Set the following environment variables:
- `CODEXDB_TMP` designates a working directory into which CodexDB writes temporary files (e.g., Python code for query execution).
- `CODEXDB_PYTHON` is the name (or path) of the Python interpreter CodexDB uses to test the Python code it generates.
E.g., set the two variables using the following commands:
```
export CODEXDB_TMP=/tmp
export CODEXDB_PYTHON=python3
```

# Running CodexDB

**WARNING: CodexDB generates Python code for query execution via large language models. Since CodexDB cannot guarantee to generate correct code, it is highly recommended to avoid running CodexDB on your primary machine. Instead, run CodexDB on a temporary EC2 instance and log into the Web interface from your primary machine.**

1. Start the CodexDB Web interface (replace `[OPENAI_API_ACCESS_KEY]` with your OpenAI access key!):
```
streamlit run src/codexdb/gui.py [OPENAI_API_ACCESS_KEY] /home/ubuntu/spider
```
2. After executing the command above, you should see two URLs on the console:
- Network URL
- External URL

If using CodexDB on your local machine, open the first URL on your Web browser. If using CodexDB on a remote machine, open the second URL via your local Web browser. You may have to enable external access in the second case. E.g., when running CodexDB on Amazon EC2, make sure to add an inbound rule allowing TCP access on port 8501.

# Troubleshooting

CodexDB only works with specific versions of the `sqlglot` SQL parsing library. If you encounter frequent errors in `plan.py`, check the installed version of sqlglot by running `pip show sqlglot` in the terminal. The required version is 1.16.1. If you see a different version number, uninstall sqlglot (`sudo pip uninstall sqlglot`) and reinstall the required version (e.g., by running `pip install sqlglot==1.16.1`).

CodexDB only supports a restricted class of SQL queries via the "plan" prompt. In particular, it only supports the specific join syntax used in the queries of the SPIDER benchmark. If your query falls outside of the class of supported queries, you can switch to the "query" prompt by selecting the corresponding prompt style in the "Prompt Configuration" section (see buttons on the left side of the Web interface). This prompt style does not integrate a summary of processing steps into the prompt and may therefore degrade quality.

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
