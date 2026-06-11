# ⬡ CodeGrapher

> **An Interactive AST Visualizer and GraphRAG-Powered Repository Understanding System for Python and Java Codebases**

CodeGrapher combines static code analysis, dependency graph generation, and Graph-Grounded Retrieval-Augmented Generation (GraphRAG) to help developers understand large codebases with greater accuracy and reduced hallucination compared to traditional LLM-based approaches.

Unlike conventional RAG systems that rely on vector similarity search, CodeGrapher performs **structural retrieval** using an AST-derived dependency graph. By grounding AI responses in actual repository topology, the system provides architecture-aware explanations, multi-file reasoning, and more trustworthy code insights.

---

# 📚 Table of Contents

1. Overview
2. Problem Statement
3. Motivation
4. Key Features
5. System Architecture
6. Methodology
7. Technology Stack
8. Project Structure
9. Screenshots
10. Installation
11. Usage
12. Research Contribution
13. Future Enhancements
14. Author

---

# 1. Overview

Developers often spend a significant amount of time understanding existing codebases before making modifications or contributing to a project. While Large Language Models (LLMs) can assist with code explanations, they frequently hallucinate dependencies, relationships, and architectural details because they lack a reliable understanding of repository structure.

CodeGrapher addresses this challenge by combining deterministic static analysis with AI-powered reasoning. Instead of relying solely on raw source code, the system first constructs a structural dependency graph using Abstract Syntax Tree (AST) analysis and then uses that graph as the retrieval mechanism for a GraphRAG pipeline.

The result is a repository-aware assistant capable of providing more reliable and context-aware explanations of software architecture.

---

# 2. Problem Statement

Understanding large and unfamiliar codebases remains one of the most time-consuming activities in software development.

Current AI-based coding assistants often:

* Analyze only a limited portion of the repository.
* Miss relationships between files and modules.
* Produce hallucinated dependencies.
* Generate explanations that are not grounded in actual code structure.
* Struggle with multi-file reasoning and repository-wide understanding.

This project bridges the gap between traditional static analysis and generative AI by grounding AI-generated explanations in a programmatically generated structural graph.

---

# 3. Motivation

Developers spend a significant portion of their time reading and understanding code rather than writing new functionality.

Existing static analysis tools provide structural insights but lack natural language explanations.

Existing AI assistants provide explanations but often lack structural awareness.

CodeGrapher aims to combine the strengths of both approaches by:

* Extracting repository structure deterministically.
* Representing code relationships as a graph.
* Using graph-based retrieval instead of simple keyword matching.
* Grounding LLM responses in actual repository topology.
* Improving trustworthiness through structural grounding.

---

# 4. Key Features

## Repository-Level Structural Understanding

Analyze complete multi-file repositories rather than isolated code snippets.

## AST-Based Dependency Extraction

Parse source code using language-specific AST parsers to identify:

* Functions
* Classes
* Imports
* Method calls
* Inheritance relationships
* Inter-module dependencies

## Interactive Dependency Graph

Generate an interactive graph representing repository topology and code relationships.

## GraphRAG Retrieval Pipeline

Perform structural retrieval using AST-derived dependency graphs instead of traditional vector similarity search.

## AI-Powered Explanations

Generate natural language explanations grounded in actual repository structure.

## Multi-File Reasoning

Trace execution paths and dependencies across multiple modules.

## Interactive Visualization

Explore repository architecture through a browser-based graph interface.
## Risk Analysis & Technical Debt Detection

Automatically analyze repository health using static analysis metrics and identify potential maintenance risks, including:

- Dead code detection
- Cyclomatic complexity analysis
- Deletion impact analysis
- Dependency coupling analysis
- High-risk function identification
- Repository health scoring
- Data I/O hotspot detection

Generate actionable risk reports to help developers improve maintainability and reduce technical debt.

## Automated Documentation Generation

Automatically generate repository documentation from extracted code structure and dependency relationships.

Documentation includes:

- Project overview
- Module summaries
- Function descriptions
- Dependency relationships
- Architecture insights
- Markdown export support

This helps developers quickly understand unfamiliar codebases without manually reading every file.

---

# 5. System Architecture

## High-Level Workflow


Flow:

```text
Repository
    │
    ▼
AST Parser
    │
    ▼
Feature Extraction
    │
    ▼
Dependency Graph Builder
    │
    ▼
Graph Metadata Generator
    │
    ▼
Graph Traversal Retrieval
    │
    ▼
Prompt Augmentation
    │
    ▼
Ollama (Llama 3.2)
    │
    ▼
Repository-Aware Explanation
```

---

# 6. Methodology

## Step 1: AST Parsing

Source files are parsed into Abstract Syntax Trees using:

* Python AST
* Javalang

This provides a structured representation of source code.

---

## Step 2: Feature Extraction

The parser extracts:

* Function definitions
* Class definitions
* Imports
* Method calls
* Inheritance relationships

---

## Step 3: Graph Construction

A directed dependency graph is generated where:

* Nodes represent files, classes, or functions.
* Edges represent imports, calls, and structural relationships.

---

## Step 4: Metadata Generation

Graph topology is transformed into searchable metadata.

Examples include:

* Function ownership
* Module relationships
* Dependency paths
* Call relationships
* Graph connectivity information

---

## Step 5: Graph-Grounded Retrieval

When a user submits a query, the system traverses the dependency graph to identify the most relevant functions, classes, and files.

Unlike traditional RAG systems that retrieve documents through embedding similarity, CodeGrapher retrieves context using structural relationships extracted from the repository.

---

## Step 6: Prompt Augmentation

The system injects:

* AST-derived call graph information
* Dependency relationships
* Relevant source code snippets
* Structural metadata

into the LLM prompt.

This grounding process significantly reduces hallucinations and improves repository-level reasoning.

---

## Step 7: Response Generation

Ollama generates repository-aware explanations using graph-grounded context.

---

# 7. Technology Stack

## Backend

* Python
* Flask

## Static Analysis

* Python `ast`
* `javalang`

## Graph Processing

* Custom Graph Algorithms
* Directed Call Graph Construction
* Dependency Traversal Logic

## Frontend

* HTML5
* CSS3
* Vanilla JavaScript
* SVG Rendering

## AI Engine

* Ollama
* Llama 3.2 1B

## GraphRAG Layer

* AST-Derived Dependency Graph
* Structural Retrieval Engine
* Prompt Augmentation Pipeline

---

# 8. Project Structure

```plaintext
CodeGrapher/
│
├── backend/
│   ├── app.py                # Flask server and API routes
│   ├── analysis.py           # AST parsing and graph construction
│   └── llm.py                # Ollama integration and GraphRAG prompt building
│
├── frontend/
│   ├── static/
│   │   ├── script.js
│   │   └── style.css
│   │
│   └── templates/
│       └── index.html
│
├── images/
│
├── dataset/
│
├── evaluation/
│
├── README.md
│
└── requirements.txt


```# 9. Screenshots

## Login Page

<p align="center">
  <img src="images/login.png" width="900">
</p>

---

## Registration Page

<p align="center">
  <img src="images/registeraccount.png" width="900">
</p>

---

## Homepage (Light Theme)

<p align="center">
  <img src="images/homepagelight.png" width="900">
</p>

---

## Homepage (Dark Theme)

<p align="center">
  <img src="images/homepagedark.png" width="900">
</p>

---

## Dependency Graph Visualization - View 1

<p align="center">
  <img src="images/dependency_g1.png" width="1000">
</p>

---

## Dependency Graph Visualization - View 2

<p align="center">
  <img src="images/dependency_g2.png" width="1000">
</p>

---

## AI Chat & Repository Explanation

<p align="center">
  <img src="images/chat.png" width="1000">
</p>

---

## Repository Analysis Report

<p align="center">
  <img src="images/report.png" width="1000">
</p>

---

## Risk Analysis Report

<p align="center">
  <img src="images/riskreport.png" width="1000">
</p>

# 10. Installation

## Clone Repository

```bash
git clone https://github.com/Saina545/CodeGrapher.git
cd CodeGrapher
```

---

## Create Virtual Environment

```bash
python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
```

### Linux / macOS

```bash
source venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### Required Packages

```text
flask
flask-cors
javalang
```

---

## Install Ollama

Start Ollama:

```bash
ollama serve
```

Pull the model:

```bash
ollama pull llama3.2:1b
```

---

# 11. Usage

Run the backend server:

```bash
python backend/app.py
```

Open:

```text
http://127.0.0.1:5000
```

Upload a repository and begin exploring its structure through the interactive graph interface.

---

# 12. Research Contribution

This project contributes:

* Repository-level structural understanding.
* GraphRAG for software repositories.
* Hallucination reduction through structural grounding.
* Interactive dependency graph visualization.
* Multi-file reasoning for software repositories.
* Integration of static analysis and LLM-based repository understanding.
* AST-driven structural retrieval for code intelligence.

---



# 13. Future Enhancements

* Support for C++
* Support for JavaScript and TypeScript
* Dynamic execution tracing
* Embedding-enhanced GraphRAG retrieval
* Automated documentation generation
* IDE plugin integration
* Architectural pattern detection
* Repository summarization
* Cross-repository reasoning
* Large-scale enterprise repository support

---

# 14. Author

## Saina Abdul Hamid

Built with a passion for software engineering, static analysis, repository understanding, GraphRAG systems, and explainable AI.

---

### Acknowledgements

This project draws inspiration from research in:

* Static Program Analysis
* Repository-Level Code Understanding
* Retrieval-Augmented Generation (RAG)
* GraphRAG Systems
* Explainable AI for Software Engineering

---
