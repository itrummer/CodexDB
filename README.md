# Overview

CodexDB allows users to specify natural language instructions, together with their SQL queries. It uses OpenAI's GPT-3 Codex model to generate code for query processing that complies with those instructions. This enables far-reaching customization, ranging from the selection of frameworks for query processing to custom logging output. In doing so, CodexDB blurs the line between user and developer.

# Setup

The following instructions have been tested on an EC2 instance of type t2.medium with Ubuntu 22.04 OS and 25 GB of disk space.

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
4. Use pip to install required dependencies (make sure to use sudo):
```
sudo pip install -r requirements.txt
```
5. Download and unzip the SPIDER dataset for benchmarking:
```
cd ..
sudo pip install gdown
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

**WARNING: CodexDB generates Python code for query execution via large language models. Since CodexDB cannot guarantee to generate correct code, it is highly recommended to execute code remotely on a temporary machine. If executing CodexDB locally, executing the generated code may alter system state or delete files on hard disk.**

1. Start the CodexDB Web interface (replace `[OPENAI_API_ACCESS_KEY]` with your OpenAI access key!):
```
streamlit run src/codexdb/gui.py [OPENAI_API_ACCESS_KEY] /home/ubuntu/spider
```
2. After executing the command above, you should see two URLs on the console:
- Network URL
- External URL

If using CodexDB on your local machine, open the first URL on your Web browser. If using CodexDB on a remote machine, open the second URL via your local Web browser. You may have to enable external access in the second case. E.g., when running CodexDB on Amazon EC2, make sure to add an inbound rule allowing TCP access on port 8501.

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
