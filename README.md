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
7. Set all required environment variables:
```
export CODEXDB_TMP=/tmp
export CODEXDB_PYTHON=python3
```

# Running CodexDB

1. Start the CodexDB Web interface (in the following command, replace the three dots with your OpenAI access key!):
```
streamlit run src/codexdb/gui.py ... /home/ubuntu/spider
```
2. Access the CodexDB Web interface via the Web browser.

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
