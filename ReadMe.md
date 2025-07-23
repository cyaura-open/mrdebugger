# Multi-AI Bug Investigator

A productivity tool that orchestrates multiple Large-Language Models (LLMs) (e.g. OpenAI GPT-4, Anthropic Claude) to **analyse a bug report, audit your codebase, and propose definitive fixes**.

## Table of Contents

- [Features](#features)
- [Project Layout](#project-layout)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Configuration (`config.yaml`)](#configuration-configyaml)
- [Prompt Templates](#prompt-templates)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

The workflow automatically:
1. Parses your bug description ( `bug.txt` ).
2. Scans your source files in the `codebase/` folder (or a custom set of files).
3. Runs a three-phase dialogue between two independent AIs and an arbitrator AI to cross-audit findings.
4. Saves structured reports and a final **`definitive_fixes.md`** file in a versioned results folder (`bug0001_results/`, `bug0002_results/`, …).

---

## Features

* Multi-agent architecture (AI A, AI B, Final Arbitrator)
* Chunking & token-management to fit large repositories
* Pluggable prompt templates (configured in `config.yaml`)
* YAML/JSON config loading with environment-variable substitution
* Works on Windows, macOS & Linux (Python 3.9+)

---

## Project Layout

```text
├── bug.txt                  # Your bug / stack-trace description
├── codebase/                # Source code to analyse (any language)
├── prompts/                 # Prompt templates (markdown / txt)
│   ├── bug_slayer_prompt.txt
│   ├── audit_consolidator_prompt.txt
│   └── final_consolidator_prompt.txt
├── config.yaml              # Main configuration file
├── main.py                  # Entry point
├── workflow_orchestrator.py # Core logic
└── ...
```

---

## Prerequisites

* **Python 3.9 or newer**
* An OpenAI account (for `OPENAI_API_KEY`)
* An Anthropic account (for `ANTHROPIC_API_KEY`)
* Git (optional, to clone the repository)

---

## Installation

```bash
# 1) Clone the repository
$ git clone https://github.com/your-org/multi-ai-bug-investigator.git
$ cd multi-ai-bug-investigator

# 2) Create & activate a virtual environment (recommended)
$ python -m venv .venv
$ source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3) Install Python dependencies
$ pip install -r requirements.txt
```

> **requirements.txt** (minimal example)
>
> ```text
> openai>=1.12.0
> anthropic>=0.5.0
> python-dotenv>=1.0.0
> requests>=2.32.0
> pyyaml>=6.0
> ```

---

## Environment Variables

Set your API keys **before** running the tool (or save them in a `.env` file):

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="cla-..."
```

Windows PowerShell:
```powershell
setx OPENAI_API_KEY "sk-..."
setx ANTHROPIC_API_KEY "cla-..."
```

---

## Configuration (`config.yaml`)

Key sections:

* `apis` – per-provider credentials & model names.
* `api_defaults` – shared temperature / max_tokens / retry policy.
* `workflow` – selects which provider is AI A, AI B & the arbitrator.
* `paths` – default locations for bug file, codebase folder & prompts.
* `prompts` – mapping of logical names to prompt-template files.
* `output` – filenames for generated reports.

Edit values as needed; environment placeholders like `${OPENAI_API_KEY}` are substituted automatically.

---

## Prompt Templates

Prompt files live in `prompts/` and are referenced via the `prompts` mapping in `config.yaml`.
Feel free to tweak the wording to suit your coding standards.

---

## Usage

### 1. First-time setup

```bash
# Creates default folders (codebase/, prompts/) and a sample bug.txt
python main.py --setup
```

1. **Describe your bug** – open `bug.txt` and replace the placeholder text with:
   * A concise overview of the problem.
   * Any relevant terminal output / stack trace (copy–paste directly).  
     The more context you give, the better the analysis.
2. **Populate the codebase** – copy the files (e.g. *.py, *.yaml...) that are _directly related_ or even the whole codebase as files to the bug into the `codebase/` directory.
   * Language-agnostic: Python, JavaScript, C++, etc. are all accepted.

### 2. Verify API connectivity (optional)
```bash
python main.py --test-connections
```

### 3. Run the investigation

```bash
python main.py   # analyses bug.txt + all files inside codebase/
```

#### Common Flags

| Flag | Description |
|------|-------------|
| `--bug MY_BUG.txt` | Use a different bug file, or keep the name and paste your bug here (e.g. terminal output). |
| `--codebase my_src/` | Analyse another folder, or copy and paste the files from your codebase here |
| `--files file1.py file2.js` | Legacy mode – analyse specific files only |
| `--validate-only` | Estimate token usage and exit |
| `--output-only` | Print the final report without progress logs |

### 4. View Results

Outputs are stored in an auto-numbered folder e.g. `bug0005_results/`:

```text
bug0005_results/
├── audit_report_A.md
├── audit_report_B.md
├── consolidation_A.md
├── consolidation_B.md
├── cross_audit_A_on_B.txt
├── cross_audit_B_on_A.txt
└── definitive_fixes.md  <- Your actionable fixes
```

---

## Troubleshooting

| Issue | Cause / Fix |
|-------|-------------|
| `Config file ... not found` | Ensure `config.yaml` exists or pass `--config my.yml` |
| `Prompt file ... not found` | Check filenames under `prompts:` section & folder path |
| `Environment variable ... not set` | Export `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` |
| `Temperature must be explicitly set` | Add `temperature` under the relevant provider in `config.yaml` |
| `Bug file '...' not found` | Run `python main.py --setup` or fix the path |

---

## Contributing

Pull requests are welcome! Please open an issue first to discuss major changes.

---

## License

MIT License

Copyright (c) 2024 Matheus J. T. Vargas, PhD

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

**Attribution Notice:** Any use of this software, in source or binary form,
must include clear attribution to the original author:  
**Matheus J. T. Vargas, PhD**

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
