# The assistant in SAP diagram conventions

The assistant described at three levels of design, from the overall
solution down to the order of calls inside it, drawn the way SAP draws
solution diagrams. Read from the top and stop at the level you need.
For the full specification, see [ARCHITECTURE.md](../ARCHITECTURE.md).

## Which SAP conventions, and how they map

SAP publishes two sources of guidance for solution diagrams:

- the **[SAP BTP Solution Diagram Guidelines](https://sap.github.io/btp-solution-diagrams/)**,
  which set the colours, areas, line styles and numbering
- the **[SAP Architecture Center](https://architecture.learning.sap.com/docs/community/diagrams)**,
  which defines two levels of diagram and recommends Mermaid for
  lightweight flows and sequence diagrams for component interactions

| Level here | SAP diagram | SAP's definition |
|---|---|---|
| 1. Solution architecture | **L1 solution diagram** | "A high-level overview of solution architectures, focusing on key components and their relationships" |
| 2. System design | **L2 solution diagram** | "Detailed technical representations, including service interactions, data flows, and integration points" |
| 3. Detailed design | **Sequence diagram** | Recommended by the Architecture Center for component interactions |

**Conventions applied**

| Convention | SAP rule | Here |
|---|---|---|
| Areas | Blue for SAP-owned areas (`#0070F2` border, `#EBF8FF` fill); grey for non-SAP (`#475E75`, `#F5F6F7`) | Blue for the solution this project owns; grey for third parties. See the adaptation note below. |
| Nesting | Alternate filled and unfilled areas so nested areas contrast | The blue solution area sits inside the grey hosting area |
| Solid line | Direct, synchronous request and response | Every API call and page request |
| Dashed line | Indirect, asynchronous flow | The redeploy triggered by a push to GitHub |
| Dotted line | Optional flow | The web search, which runs only as a fallback |
| Authentication flow | Usually green | The visitor's password sign-in |
| Numbers | Mark a specific path through the diagram | The path of one question, in order |
| Legend | Every diagram includes one | Under each diagram |
| Text | Titles `#1D2D3E`, body `#556B82` | Applied to every box |

**Adaptations, stated openly**

- **Blue means "ours", not "SAP's".** This project contains no SAP
  products. In SAP's diagrams the blue area is SAP's platform; here it
  stands for the solution being described, and everything provided by
  someone else is grey.
- **No official icons.** SAP's diagrams use official service icons in
  draw.io. Mermaid cannot use them, so each box names its technology
  in text. The Architecture Center accepts Mermaid for lightweight,
  non-product-specific flows.
- **SAP's internal notation is not used.** For internal technical
  architecture SAP has historically used TAM (Technical Architecture
  Modeling), built from FMC block diagrams and parts of UML. Its rules
  are not fully public, so it is not imitated here.

## 1. L1 solution diagram

**L1: AI assistant, solution overview**

```mermaid
flowchart LR
    visitor(["Visitor<br/>web browser"])
    peer(["Claude Code<br/>or another AI assistant"])

    subgraph solution ["AI assistant (this project)"]
        app["Chat app<br/>Streamlit, LangGraph"]
        server["MCP server<br/>4 tools"]
        kb[("Knowledge base<br/>10 documents")]
    end

    subgraph third ["Third-party services"]
        groq["Groq<br/>hosted language models"]
        github["GitHub<br/>code and commit history"]
        nyc["NYC Open Data<br/>public city data"]
        tavily["Tavily<br/>web search"]
    end

    visitor -->|"1. Signs in with the password"| app
    visitor -->|"2. Asks a question"| app
    app -->|"3. Generates the answer"| groq
    app -->|"4. Reads live data"| github
    app -->|"4. Reads live data"| nyc
    app -->|"5. Searches the web, fallback only"| tavily
    app -->|"Retrieves passages"| kb
    peer -->|"Calls tools over MCP"| server
    server -->|"Generates answers"| groq
    github -->|"Redeploys on push"| app

    classDef ours fill:#FFFFFF,stroke:#0070F2,color:#1D2D3E
    classDef theirs fill:#FFFFFF,stroke:#475E75,color:#1D2D3E
    classDef person fill:#FFFFFF,stroke:#556B82,color:#1D2D3E
    class app,server,kb ours
    class groq,github,nyc,tavily theirs
    class visitor,peer person
    style solution fill:#EBF8FF,stroke:#0070F2,color:#1D2D3E
    style third fill:#F5F6F7,stroke:#475E75,color:#1D2D3E
    linkStyle 0 stroke:#188918,stroke-width:2px
    linkStyle 5 stroke:#475E75,stroke-dasharray:2 3
    linkStyle 9 stroke:#475E75,stroke-dasharray:6 4
```

*Legend: blue area, the solution this project owns; grey area, third-party
services. Green line, authentication. Solid line, synchronous request and
response. Dotted line, optional flow. Dashed line, asynchronous flow.
Numbers, the path of one question, in order; the two steps numbered 4
are alternatives, chosen by the question.*

**Constraint: cost.** Everything runs on free tiers, so the design uses
a small model by default, limits each visit to 20 questions and caches
tool results. In a paid deployment the running cost would come from
two metered services, language-model tokens (Groq) and web searches
(Tavily), plus hosting. The L2 and sequence sections below show
where each is spent.

**Decisions made at this level**

| Decision | Alternative rejected | Why |
|---|---|---|
| Build the RAG pipeline | Buy a ready-made RAG platform | The demo exists to show the mechanics |
| Hosted models through an API (Groq) | Run models on own hardware | No hardware, free tier, fast responses |
| Free hosting (Streamlit Community Cloud) | A paid cloud platform | Cost, and enough for a demo |
| Public repository | Private | The code is part of what is being shown |

## 2. L2 solution diagram

**L2: AI assistant, services, data flows and integration points**

```mermaid
flowchart LR
    visitor(["Visitor<br/>web browser"])
    claude(["Claude Code<br/>owner's machine"])

    subgraph host ["Streamlit Community Cloud (third-party host)"]
        subgraph app ["Chat app (this project)"]
            page["Chat page<br/>Streamlit"]
            guard["Input guardrail<br/>guard.py"]
            router["Router and orchestration<br/>LangGraph"]
            rag["RAG retriever<br/>rag.py"]
            chroma[("Vector store<br/>Chroma, embedded")]
            sql["SQL tool<br/>SQLite, in memory"]
            client["MCP client<br/>mcp_client.py"]
        end
    end

    subgraph local ["Owner's machine"]
        server["MCP server (this project)<br/>search, ask, commits, data"]
    end

    subgraph third ["Third-party services"]
        prompt["Groq: Llama Prompt Guard 2<br/>injection classifier"]
        llm["Groq: gpt-oss-20b<br/>gpt-oss-120b as fallback"]
        github["GitHub REST API"]
        nyc["NYC Open Data API"]
        tavily["Tavily MCP server"]
    end

    visitor -->|"1. Signs in, HTTPS"| page
    visitor -->|"2. Asks a question, HTTPS"| page
    page -->|"3. Passes the message"| guard
    guard -->|"4. Scores for injection, HTTPS"| prompt
    guard -->|"5. Passes a safe message"| router
    router -->|"6. Routes and rewrites, HTTPS"| llm
    router -->|"7a. Documents"| rag
    rag -->|"8. Retrieves top 5 passages"| chroma
    rag -->|"9. Answers from passages, HTTPS"| llm
    router -->|"7b. Commits, HTTPS"| github
    router -->|"7c. Taxi data"| sql
    sql -->|"Fetches counts, HTTPS"| nyc
    router -->|"10. Web fallback"| client
    client -->|"Calls tavily_search, MCP over HTTP"| tavily
    claude -->|"Calls tools, MCP over stdio"| server
    server -->|"HTTPS"| llm
    github -->|"Redeploys on push"| page
    server -->|"HTTPS"| github
    server -->|"HTTPS"| nyc

    classDef ours fill:#FFFFFF,stroke:#0070F2,color:#1D2D3E
    classDef theirs fill:#FFFFFF,stroke:#475E75,color:#1D2D3E
    classDef person fill:#FFFFFF,stroke:#556B82,color:#1D2D3E
    class page,guard,router,rag,chroma,sql,client,server ours
    class prompt,llm,github,nyc,tavily theirs
    class visitor,claude person
    style host fill:#F5F6F7,stroke:#475E75,color:#1D2D3E
    style app fill:#EBF8FF,stroke:#0070F2,color:#1D2D3E
    style local fill:#F5F6F7,stroke:#475E75,color:#1D2D3E
    style third fill:#F5F6F7,stroke:#475E75,color:#1D2D3E
    linkStyle 0 stroke:#188918,stroke-width:2px
    linkStyle 12 stroke:#475E75,stroke-dasharray:2 3
    linkStyle 13 stroke:#475E75,stroke-dasharray:2 3
    linkStyle 16 stroke:#475E75,stroke-dasharray:6 4
```

*Legend: blue area, components this project owns; grey area, third
parties, including the host the app runs on. Green line,
authentication. Solid line, synchronous request and response. Dotted
line, optional flow. Dashed line, asynchronous flow. Numbers, the path
of one question; 7a, 7b and 7c are alternatives chosen by the router,
and step 10 runs only when the documents do not cover a general
question.*

**Cost view**

Where money would be spent in a paid deployment. Prices are left out
because they change; the cost of each line is its volume times the
provider's current price.

| Cost item | Where | Driver | Today |
|---|---|---|---|
| Language-model tokens | Chat app and MCP server, to Groq | Model calls per message, and tokens per call | Free tier: 8,000 tokens a minute and 200,000 a day per model |
| Classifier calls | Chat app, to Groq | One per message that reaches the input guardrail | Free tier, with its own allowance |
| Web searches | Chat app, to Tavily | One credit per web answer | Free tier |
| Hosting | Streamlit Community Cloud | Uptime and memory | Free |
| Embeddings | Inside the chat app | Computed locally at indexing and per question | No per-call fee; uses the app's own compute |
| GitHub and NYC Open Data | Chat app and MCP server | Requests | Free public APIs; results cached to stay within rate limits |

Tokens are the main variable cost; the sequence section below breaks
them down per message.

**Decisions made at this level**

| Decision | Alternative rejected | Why |
|---|---|---|
| Embedded vector store (Chroma in-process) | A separate vector database server | Small corpus; nothing extra to run |
| Rebuild the index at startup | A persistent hosted index | The host's storage is temporary, and the index is derived from `data/` anyway |
| One shared core, two front ends | Separate code for the chat page and the MCP server | Both give the same answers from the same code |
| Text-to-SQL on a temporary SQLite table | Indexing the data as text for retrieval | Retrieval cannot total a column or count rows; SQL can, and can be checked in code |

## 3. Sequence diagram

**One question answered from the documents, with the web fallback**

```mermaid
sequenceDiagram
    autonumber
    actor Visitor
    box rgb(235,248,255) Chat app (this project)
        participant Page as Chat page
        participant Graph as Orchestration (LangGraph)
        participant Guard as Input guardrail
        participant RAG as RAG retriever
        participant Chroma as Vector store (Chroma)
        participant Client as MCP client
    end
    box rgb(245,246,247) Third-party services
        participant Groq
        participant Tavily
    end

    Visitor->>Page: Asks a question
    Page->>Graph: respond(question, history)
    alt Small talk, such as "thanks"
        Graph-->>Page: Fixed reply, no model call
    else Any other message
        Graph->>Guard: Check the message
        Guard->>Groq: Score with Prompt Guard 2
        Groq-->>Guard: Score from 0 to 1
        alt Score 0.5 or above
            Guard-->>Graph: Refuse
        else Score below 0.5
            Graph->>Groq: Route and rewrite (gpt-oss-20b)
            Groq-->>Graph: Tool: documents, standalone question
            Graph->>RAG: Answer from the documents
            RAG->>Chroma: Search, top 5 passages
            Chroma-->>RAG: Passages with distances
            RAG->>Groq: Answer from these passages only
            Groq-->>RAG: Answer, or the sentinel value NOT_IN_DOCUMENTS
            RAG-->>Graph: Result with status
            opt Not covered, and a web search is allowed
                Graph->>Client: Search the web
                Client->>Tavily: tavily_search, MCP over HTTP
                Tavily-->>Client: 3 results
                Client-->>Graph: Results
                Graph->>Groq: Answer from the results only
                Groq-->>Graph: Answer, with the web notice added by code
            end
        end
    end
    Graph-->>Page: Result: answer, status, sources, evidence
    Page-->>Visitor: Answer with its source and evidence
```

*Legend: blue box, components this project owns; grey box, third-party
services. Solid arrow, a request; dashed arrow, its response. "alt"
marks alternatives, one of which happens; "opt" marks an optional
step. Numbers give the order of messages.*

**Model calls and tokens per message**, by the path a message takes
through the graph. Token figures are estimates from development, not
measurements of live traffic.

| Path | Classifier calls | Language-model calls | Tokens, roughly | Other metered use |
|---|---|---|---|---|
| Small talk | 0 | 0 | 0 | None |
| Refused for length | 0 | 0 | 0 | None |
| Refused by the input guardrail | 1 | 0 | Classifier only | None |
| Documents | 1 | 2: route, answer | 2,000 to 3,000 | None |
| GitHub | 1 | 2: route, answer | Somewhat fewer than documents | None |
| NYC data | 1 | 3: route, write SQL, answer; 4 if the SQL is retried | Not measured separately; most messages use 2,500 to 4,000 | None |
| Web fallback | 1 | 3: route, documents attempt, answer | About 1,000 more than documents | 1 Tavily search credit |

Most of a documents answer's tokens are the five retrieved passages.
The model evaluation measured about 14,000 tokens for its 11 cases on
each model.

**Design choices that keep token spend down**

| Choice | Effect |
|---|---|
| Small talk answered in code | No model call for "thanks" or "hi" |
| Routing and query rewriting in one call | One call where two would be usual |
| 5 passages of about 500 characters each | Bounds the largest part of every prompt |
| History cut to 4 messages of 400 characters | Bounds the conversation's share of every prompt |
| Web results cut to 3, each 500 characters | Bounds the most expensive path |
| Smaller model by default | Several times cheaper per token on a paid plan |
| Cached GitHub and NYC results | Fewer outside requests; no effect on tokens |
| 20 questions per visit | Caps the spend of any one visitor |

**Main interfaces**

| Function | Module | Takes | Returns |
|---|---|---|---|
| `respond` | `chat` | A question, the collection, recent history | A result: answer, status, tool, sources, evidence |
| `route` | `chat` | A question and history | The tool to use and the question rewritten as a standalone question |
| `answer` | `rag` | A question and the collection | The answer, its sources and the retrieved passages |
| `search` | `store` | The collection, a query, how many results | Passages with their source and distance |
| `ask` | `llm` | A prompt, instructions, a model | The model's reply, with fallback on a rate limit |
| `looks_like_injection` | `guard` | A message | True if the classifier's score is 0.5 or above |
| `query_license_data` | `tools` | A SQL statement | Columns and rows, after the statement passes the checks |
| `call_tavily` | `mcp_client` | A query and a key | The search tool's result |

Every result carries a **status**: `answered`, `not_covered`,
`unclear`, `blocked` or `small_talk`. The page decides what to show
from the status, not from the wording of the answer.

Sources: [SAP BTP Solution Diagram Guidelines: foundation](https://sap.github.io/btp-solution-diagrams/docs/btp_guideline/foundation/),
[areas](https://sap.github.io/btp-solution-diagrams/docs/btp_guideline/diagr_comp/areas/),
[connectors](https://sap.github.io/btp-solution-diagrams/docs/btp_guideline/diagr_comp/lines_connectors/),
[numbers](https://sap.github.io/btp-solution-diagrams/docs/btp_guideline/diagr_comp/numbers/);
[SAP Architecture Center: diagrams](https://architecture.learning.sap.com/docs/community/diagrams).
