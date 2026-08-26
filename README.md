# langgraph-customer-support-agent

An agentic customer-support chatbot built with **LangGraph** and **Groq**
(open-weight GPT-OSS-20B). It looks up orders, refunds them, and opens
categorized support tickets by calling tools - with a human-in-the-loop
approval step before any refund actually executes.

The point of this project isn't a polished e-commerce backend (the store
behind the tools is a small in-memory fake, on purpose - see
[Scope](#scope)). The point is agent **orchestration and reliability**:
a real LangGraph state machine, structured tool calling with schema-level
enums, human-in-the-loop approval, and - most importantly - a set of
evals that caught and drove fixes for three real LLM reliability bugs
during development (see [Findings from evals](#findings-from-evals)).

## Demo

- **Streamlit UI**: `streamlit run streamlit_app.py` - chat interface with
  live order/ticket state in the sidebar, approve/reject buttons for
  refunds, clickable example prompts.
- **CLI**: `python main.py` - same graph, terminal-based.

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
  checkpointer. The caller (CLI or Streamlit) resumes it with a `Command`
  carrying the human's decision.
- Every turn loops back to `agent` until it produces a plain answer.
- It's a **single agent** looping over itself across tool calls, not a
  multi-agent system - see [Known limitations](#known-limitations).

## Ticket data model

Tickets aren't just an id and a status - each one carries:

| Field | Type | Notes |
|---|---|---|
| `category` | enum | `damaged_item`, `defective_item`, `missing_delivery`, `wrong_item`, `billing_dispute`, `safety_hazard`, `other` |
| `priority` | enum | `low`, `normal`, `urgent` |
| `status` | enum | `open`, `in_progress`, `resolved`, `closed` |
| `created_at` / `updated_at` | timestamp | |
| `history` | list | timestamped log, one entry per status change |

`category` and `priority` are `typing.Literal` types, so LangChain compiles
them into a real JSON Schema `enum` - the model is structurally constrained,
not just prompted to pick from a list (see [Findings](#findings-from-evals)
for why that distinction mattered in practice).

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
streamlit_app.py     Streamlit chat UI with live order/ticket sidebar
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
streamlit run streamlit_app.py   # UI, recommended
python main.py                   # CLI
```

Try: *"I'd like a refund for order 4521, I paid 89.99"* - the agent will
call `check_order`, then pause and ask you to approve or reject the refund
before it executes. Try *"my order arrived damaged"* to see a ticket get
created with an auto-classified category and priority.

## Tests and evals

```bash
pytest                    # unit tests on the tools, no API key needed
python evals/run_eval.py  # scenario-based eval, makes real Groq calls
```

## Findings from evals

Running the eval harness against the live model surfaced three real
reliability issues during development - not code bugs, LLM behavior bugs.
Each was diagnosed with a trace, fixed by changing the tool's docstring or
schema (not the graph logic), and re-verified.

**1. Hallucinated action.** Asked to help with a damaged order, the model
replied *"I've opened a support ticket for you"* without ever calling
`create_ticket`. Fixed by adding an explicit rule to the system prompt:
never claim an action unless the corresponding tool call succeeded first.

**2. Miscalibrated priority.** The `priority` field ("low"/"normal"/
"urgent") almost never came back as `"low"`, even for the exact case
described in the tool docstring as an example ("a small scratch on the
box"). The model defaulted to `"normal"` unless something was clearly
severe. Fixed by replacing the abstract description with concrete
input -> output examples for each priority level in the tool's docstring;
re-tested across 4 scenarios, all classified correctly afterward.

**3. Invented details in free text.** The `description` field the model
writes for a ticket sometimes added specific damage details the customer
never actually reported (*"the packaging was dented and the product
appears cracked"* from a customer who only said "arrived damaged").
Re-running the identical input multiple times produced different
descriptions - a sign the model was filling gaps with plausible-sounding
specifics rather than staying faithful to the source. Fixed with an
explicit instruction to summarize only what was said, with a fallback
phrasing for when no detail was given; verified stable across 3 repeated
runs afterward.

**Structural fix, not just prompting:** `category` and `priority` started
as plain `str` arguments constrained only by docstring text - the model
could technically return anything. Switching them to `typing.Literal`
made LangChain emit a real JSON Schema `enum`, so invalid values are now
rejected by Pydantic before the tool ever runs. Traced through LangGraph's
`ToolNode` source to confirm that rejection doesn't crash the graph: it's
caught and returned to the model as an error `ToolMessage`, giving it a
chance to self-correct on the next turn instead of failing the whole run.

## Known limitations

- Single agent, not multi-agent: `agent_node` loops over itself across
  tool calls rather than delegating to specialized sub-agents.
- `human_review_node` only handles the first tool call of a turn - fine
  here since the model requests at most one sensitive action per turn in
  practice, but not a general solution for parallel tool calls.
- The fake store is in-memory and resets whenever the process restarts.
- No retry/backoff around the Groq client; a transient API error currently
  surfaces as an exception.
- Free-text fields (`subject`, `description`) aren't schema-constrained
  like `category`/`priority` - prompt-level guidance reduced but can't
  fully eliminate variance across runs.

## Scope

The "e-commerce API" behind the tools (`src/db.py`) is a small in-memory
fake store, deliberately - the goal here is agent orchestration and
reliability, not backend engineering. All effort went into the LangGraph
graph, the tool schemas, and the evals that stress-tested them.
