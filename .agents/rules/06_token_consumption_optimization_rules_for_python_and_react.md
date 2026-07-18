---
name: 06_Token_Consumption_Optimization_Rules_for_Python_and_React
---
## 1. Objective
These rules define the architectural standards for backend (Python) and frontend (React) services to minimize token usage when interacting with Large Language Models (LLMs).

---

## 2. Python Backend Rules (Data & Context Control)

### Rule 2.1: Explicit Projection
**Never** pass raw ORM or database objects to the LLM. Always define a projection or DTO (Data Transfer Object) that explicitly selects only the fields required for the specific task.
- *Rationale:* Database objects often contain metadata (e.g., `created_at`, `updated_at`, `id`, `internal_flags`) that the LLM does not need to process.

### Rule 2.2: Computational Pre-processing
If the task requires arithmetic, data aggregation, or formatting, perform these operations in Python before sending the request to the LLM.
- *Rule:* If `f(data)` can be computed by Python, do not ask the LLM to perform `f(data)`.

### Rule 2.3: Intelligent Pagination & Chunking
For data retrieval tasks, implement strict limits.
- *Rule:* Default response limits to 10–20 items. Include metadata in the response: `{"total_count": X, "more_available": boolean}`.

### Rule 2.4: System Prompt Optimization
Separate static system instructions from dynamic conversation context.
- *Rule:* Use a constant system prompt for role definitions and core logic; do not re-send this as part of the dynamic prompt object if the API supports separating them.

---

## 3. React Frontend Rules (Request & State Management)

### Rule 3.1: Sliding Window Conversation
Do not store the entire conversation history in React state.
- *Rule:* Keep a buffer of the last N messages (e.g., N=5) for immediate context.

### Rule 3.2: Context Summarization
For long sessions, implement a background summarization service.
- *Rule:* Every X turns, trigger a silent request to the LLM to summarize the "historical context" into a concise block. Replace the old history in state with this summary.

### Rule 3.3: Request Throttling & Debouncing
Prevent unnecessary LLM calls during user input.
- *Rule:* Use `useDebounce` or similar hooks for auto-completion or analysis features to ensure requests are only sent after the user has finished typing.

### Rule 3.4: State-Based Tool Filtering
Do not provide the LLM with all available tool schemas at all times.
- *Rule:* Only inject the schemas for tools relevant to the current UI state of the user.

---

## 4. Summary Table

| Category | Optimization Strategy | Implementation |
| :--- | :--- | :--- |
| **Data** | Projection Pattern | Whitelist fields via Pydantic/dataclasses |
| **Logic** | Pre-calculation | Python-side computation of stats/summaries |
| **Memory** | Sliding Window | Keep last $N$ messages; drop/summarize older ones |
| **Network** | Debouncing | Wait for user silence before triggering API |
| **Tools** | Selective Injection | Provide tool schemas based on current UI context |

---
## 5. Implementation Example (Python Projection)

```python
# GOOD: Explicit projection
def get_user_summary(user_id):
    user = db.users.find_one({"id": user_id})
    return {
        "username": user["username"],
        "recent_history": user["logs"][-3:] # Truncate logs
    }
"""