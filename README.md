# Agentic RoboCup – Hospital Guide Robot Agent

An LLM-driven interaction agent for a hospital guide robot, built for the **Healthcare Challenge @ RoboCup 2027**. The robot greets or picks up patients, verifies their identity, explains their procedure in plain language, and guides them to the right room before handing over to staff.

The LLM decides *what to say and do*, but a deterministic **state machine** and **tool registry** decide *what it is allowed to do*. Safety-critical rules (identity checks, escalation to staff) are enforced in code, not left to the model.

---

## How it works

```
 patient input ─▶ build_prompt() ─▶ LLM (Groq / Ollama) ─▶ JSON action
                       ▲                                       │
                       │                                       ▼
                  RESULT fed back ◀── tool registry ◀── state machine check
```

1. Each turn, a system prompt is built from the **current mode, phase, phase instruction, patient job, and the tools allowed in that phase**.
2. The LLM replies with exactly **one JSON action**, e.g. `{"action": "speak", "text": "Please follow me."}`.
3. The action is checked against the state machine (is this tool allowed in this phase? is this phase transition legal?).
4. If allowed, the tool registry runs it and the result is appended to the history so the LLM sees it on the next step.
5. The robot can chain up to 5 actions per turn and stops once it speaks or calls a patient, waiting for the next input.

### Modes

| Mode | Scenario | Phase flow |
|------|----------|------------|
| `walk_in` | A patient walks up to the robot | `GREET → IDENTIFY → EXPLAIN → GUIDE → HANDOVER → DONE` |
| `pickup` | The robot fetches a known patient from a waiting area | `CALL_PATIENT → VERIFY → EXPLAIN → GUIDE → HANDOVER → DONE` |

### Safety rules (enforced in code)

- **No skipping verification:** in `pickup` mode, the agent cannot move from `VERIFY` to `EXPLAIN` until `verify_patient` returns a match.
- **Wrong person → call again:** a failed date-of-birth check sends the agent back to `CALL_PATIENT` and tells it to politely look for the right patient.
- **Escalation:** after 3 failed verification attempts, the task stops and staff are alerted (no LLM involved).
- **Date of birth is never put in the prompt**, so the LLM cannot leak it or "verify" by guessing.
- **Per-phase tool whitelist:** e.g. `navigate` is blocked during `GREET`.

---

## Project structure

```
Agentic_robocup/
├── core/
│   ├── llm.py        # LLM backend switch (Groq / Ollama) + JSON parsing
│   └── state.py      # Phases, transitions, per-phase instructions and tool whitelist
├── tools/
│   └── registry.py   # @register_tool decorator, run_tool() dispatcher, robot tools
├── test.py           # Interactive text-based agent loop (main entry point)
└── config/           # (git-ignored) API keys
```

### Available tools as of now

| Tool | Required fields | Description |
|------|-----------------|-------------|
| `speak` | `text` | Say something to the patient |
| `navigate` | `location` | Start guiding to a location (placeholder – ROS 2 later) |
| `call_patient` | `name` | Announce a patient's name in the waiting area |
| `verify_patient` | `dob` | Compare the stated date of birth with the job (format-insensitive) |
| `set_phase` | `phase` | Move to the next phase (handled by the agent loop, not the registry) |

Adding a tool is a single decorator:

```python
@register_tool("my_tool", ["arg"], "What this tool does.")
def my_tool(arg):
    return "result"
```

Then whitelist it for the relevant phases in `PHASE_TOOLS` in `core/state.py`.

---

## Setup

### Requirements

- Python 3.11+
- `groq` and `requests`

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install groq requests
```

### API key (Groq backend)

Create `config/key.json` (this folder is git-ignored):

```json
{
  "GROQ_API_KEY": "your-groq-api-key"
}
```

### Choosing a backend

In `core/llm.py`:

```python
BACKEND = "groq"     # cloud, for development
# BACKEND = "ollama" # local, requires Ollama running on localhost:11434
```

For Ollama, pull the model first: `ollama pull qwen2.5:3b`.

---

## Usage

Run the interactive agent:

```bash
python test.py
```

You will be asked for a mode:

- **`walk_in`** – type as the patient; the robot greets you and finds out where you need to go.
- **`pickup`** – enter the patient job (name, date of birth, procedure, waiting area, destination): passed on to the robot while the task is given. The robot starts on its own by navigating to the waiting area and calling the patient. Answer as the patient; you'll be asked for your date of birth.



### Testing individual modules

```bash
python -m tools.registry   # tool registry tests (unknown tool, missing field, …)
python -m core.state       # state machine transition tests
python -m core.llm         # LLM latency / JSON output check
```

---

## Roadmap

- [ ] Replace the `navigate` placeholder function with navigation pipeline
- [ ] Load patient jobs from the hospital system instead of manual input
- [ ] `requirements.txt` and automated tests

---

## Context

Developed as the Task 1 (patient interaction) agent for a team entry in the Healthcare Challenge @ RoboCup 2027, hosted by Siemens Healthineers.