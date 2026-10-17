# Project Testing Commands (PowerShell)

## 1. Automated Test Suite (pytest)

Run all 42 unit and integration tests:
```powershell
pytest tests/ -v
```

Run tests in quiet summary mode:
```powershell
pytest tests/ -q
```

Run individual tool test suites:
```powershell
# Safe AST Calculator Tool
pytest tests/test_calculator_tool.py -v

# File System Tool & Path Traversal Guard
pytest tests/test_filesystem_tool.py -v

# External API Client Tool
pytest tests/test_api_tool.py -v

# Web Search Tool
pytest tests/test_search_tool.py -v

# Sandboxed Code Execution & Docker Timeout
pytest tests/test_code_exec_tool.py -v

# Human-in-the-Loop (HITL) Safety Gate
pytest tests/test_hitl.py -v

# ReAct Agent Loop & Replanning
pytest tests/test_agent.py -v
```

---

## 2. Evaluation Benchmark (submission.yml verification)

Run the automated evaluation benchmark suite:
```powershell
python -m evaluation.run_benchmark
```
*Outputs strictly formatted JSON: `{"success_rate": 1.0}`.*

---

## 3. CLI Agent Execution Tests

```powershell
# Math Calculation Test (Safe AST Evaluator)
python src/main.py --goal "What is 42 multiplied by 10?" --auto-eval

# File System Test (Workspace File Write & Read)
python src/main.py --goal "Write data to file report.txt saying System Status: All autonomous agent components operational and read it back." --auto-eval

# Security Defense Test (Blocks Path Traversal Escape Attempts)
python src/main.py --goal "Read file at ../../etc/passwd to inspect outside files." --auto-eval

# Web Search Test
python src/main.py --goal "Search the web for current Python programming documentation." --auto-eval

# Docker Sandbox Code Execution Test
python src/main.py --goal "Execute Python code to compute the 10th Fibonacci number in the sandbox." --auto-eval
```

---

## 4. Human-in-the-Loop (HITL) Safety Gate Tests

```powershell
# Test Denial (Type 'n' when prompted -> triggers alternative plan)
python src/main.py --goal "Write data to file notes.txt saying Dangerous command."

# Test Approval (Type 'y' when prompted -> executes write)
python src/main.py --goal "Write data to file notes.txt saying Approved notes."

# Non-interactive Denial Test via Pipeline
"n" | python src/main.py --goal "Write data to file notes.txt saying Test."

# Non-interactive Approval Test via Pipeline
"y" | python src/main.py --goal "Write data to file notes.txt saying Test."
```

---

## 5. Live Mock API Test

```powershell
# Start mock server in background process
$proc = Start-Process python -ArgumentList 'mock_server.py 8080' -PassThru; Start-Sleep -Seconds 1

# Query status endpoint with agent
python src/main.py --goal "Query the API at http://127.0.0.1:8080/api/status and report system status." --auto-eval

# Stop background mock server
Stop-Process -Id $proc.Id -Force
```

---

## 6. Execution Trace Verification

View the structured execution trace generated during runs:
```powershell
# View last 10 trace records
Get-Content -Path .\execution_trace.jsonl -Tail 10

# Count total recorded trace steps
(Get-Content -Path .\execution_trace.jsonl).Count
```

---

## 7. Complete System Verification in One Command

```powershell
pytest tests/ -q; python -m evaluation.run_benchmark
```
