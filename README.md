# support-agent

A customer-support chatbot built as an agentic LangGraph pipeline: it looks
up orders, refunds them, and opens support tickets by calling tools - with
a human-in-the-loop approval step before any refund actually executes.

This project exists to demonstrate agent **orchestration** (LangGraph state
machine, conditional routing, human-in-the-loop, persistent memory), not
backend engineering - the "e-commerce API" behind the tools is an in-memory
fake store (`src/db.py`), on purpose, so all the effort goes into the agent
itself.

## Architecture

```
        START
          |
          v
     +---------+
     |  agent  |----no tool call---> END
     +---------+
       |      |
  auto tool  refund_order requested
       |      |
       v      v
  +--------+ +---------------+
  | tools  | | human_review  |  <-- interrupt(): pauses the graph,
  +--------+ +---------------+      waits for {"approved": bool}
       |            |
       +-----+------+
             v
          (back to agent)
```

- `agent` calls the LLM (Groq) with the conversation history and the tool
  schemas bound to it. It either answers directly or requests a tool call.
- `check_order` and `create_ticket` are considered safe and run immediately
  via a prebuilt `ToolNode`.
- `refund_order` is routed to `human_review` instead: the graph calls
  `interrupt()`, which pauses execution and persists state via the
  checkpointer. The caller (see `main.py`) resumes it with a `Command`
  carrying the human's decision.
- Every turn loops back to `agent` until it produces a plain answer.

## Project layout

```
src/
  db.py              in-memory fake store (orders, tickets)
  tools/             one file per tool (check_order, refund_order, create_ticket)
  state.py           AgentState (LangGraph MessagesState)
  prompts.py         system prompt
  config.py          Groq LLM client (cached)
  nodes.py           agent_node, human_review_node
  graph.py           StateGraph wiring + routing logic
main.py              CLI chat loop, resumes interrupts
evals/               scenario-based eval harness (real Groq calls)
tests/               unit tests for the tools (no LLM required)
```

## Setup

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
cp .env.example .env            # then fill in GROQ_API_KEY
```

Get a free Groq API key at https://console.groq.com. Default model is
`openai/gpt-oss-20b` (fast, native tool calling); swap `GROQ_MODEL` in
`.env` to try `llama-3.3-70b-versatile` or others.

## Run

```bash
python main.py
```

Try: *"I'd like a refund for order 4521, I paid 89.99"* - the agent will
call `check_order`, then pause and ask you (in the terminal) to approve or
reject the refund before it executes.

## Tests and evals

```bash
pytest                  # unit tests on the tools, no API key needed
python evals/run_eval.py  # scenario-based eval, makes real Groq calls
```

## Known limitations

- `human_review_node` only handles the first tool call of a turn - fine
  here since the model requests at most one sensitive action per turn in
  practice, but not a general solution for parallel tool calls.
- The fake store is in-memory and resets whenever the process restarts.
- No retry/backoff around the Groq client; a transient API error currently
  surfaces as an exception in `main.py`.
