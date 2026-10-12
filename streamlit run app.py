warning: in the working copy of 'ARCHITECTURE.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'README.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'assistant/chat.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'data/rag.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'evals/compare_models.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_app.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_chat.py', LF will be replaced by CRLF the next time Git touches it
[1mdiff --git a/ARCHITECTURE.md b/ARCHITECTURE.md[m
[1mindex e7096e3..8479ab2 100644[m
[1m--- a/ARCHITECTURE.md[m
[1m+++ b/ARCHITECTURE.md[m
[36m@@ -112,7 +112,7 @@[m [mretrieval, tools and model code.[m
 ```mermaid[m
 flowchart LR[m
     message --> screen[m
[31m-    screen -.->|refused| answer[m
[32m+[m[32m    screen -.->|refused or courtesy| answer[m
     screen -.-> choose_tool[m
     choose_tool -.-> documents[m
     documents -.->|not covered| web_search[m
[36m@@ -131,7 +131,10 @@[m [mDashed arrows are decisions. In order:[m
 [m
 1. **Screen.** The message is refused if it is longer than 1,000[m
    characters or if a classifier scores it as a likely prompt[m
[31m-   injection.[m
[32m+[m[32m   injection. A message that is only a courtesy, such as "thanks" or[m
[32m+[m[32m   "hi", is matched against a short fixed list and given a fixed[m
[32m+[m[32m   reply here, before any model is called. It does not count against[m
[32m+[m[32m   the question limit.[m
 2. **Choose a tool.** One model call picks a source (documents,[m
    GitHub or NYC data) and, if the message is a follow-up, rewrites it[m
    as a standalone question.[m
[36m@@ -199,7 +202,7 @@[m [mproject's own functions.[m
 [m
 | Node | Job | Model calls |[m
 |---|---|---|[m
[31m-| `screen` | Refuse a message that is too long or looks like an injection | 1 classifier |[m
[32m+[m[32m| `screen` | Refuse a message that is too long or looks like an injection; reply to a courtesy | 1 classifier, or none for a courtesy |[m
 | `choose_tool` | Pick a source and make the question standalone | 1 |[m
 | `documents` | Answer from retrieved passages | 1 |[m
 | `web_search` | Answer from web results | 1 |[m
[36m@@ -212,7 +215,7 @@[m [mproject's own functions.[m
 [m
 | After | Goes to | When |[m
 |---|---|---|[m
[31m-| `screen` | end, or `choose_tool` | The message was refused, or not |[m
[32m+[m[32m| `screen` | end, or `choose_tool` | The message was refused or was a courtesy, or not |[m
 | `choose_tool` | `documents`, `github` or `write_sql` | By the tool the model named |[m
 | `documents` | `web_search`, or end | Not covered and a web search is allowed, or otherwise |[m
 | `run_sql` | `write_sql`, or `data_answer` | The query failed or was empty and has not been retried, or otherwise |[m
[36m@@ -290,7 +293,8 @@[m [mthe chunks.[m
 model is told to reply with a fixed marker. Code detects the marker[m
 and produces the refusal itself, so the wording is consistent and the[m
 program knows for certain whether a question was answered. A second[m
[31m-marker covers greetings and messages too unclear to answer.[m
[32m+[m[32mmarker covers messages too unclear to answer, and greetings worded in[m
[32m+[m[32ma way the fixed courtesy list does not hold.[m
 [m
 A distance cutoff was considered for refusals and rejected after[m
 measurement: an unanswerable question scored closer (1.05) than an[m
[36m@@ -563,12 +567,12 @@[m [mfrom the repository.[m
 [m
 ## 14. Testing and continuous integration[m
 [m
[31m-There are 317 automated tests, run with pytest.[m
[32m+[m[32mThere are 332 automated tests, run with pytest.[m
 [m
 | File | Test cases | Covers |[m
 |---|---|---|[m
[31m-| `test_chat.py` | 47 | Tool choice, each route, retries, web fallback, privacy rules, injection |[m
[31m-| `test_app.py` | 32 | The page, driven with Streamlit's test tool |[m
[32m+[m[32m| `test_chat.py` | 60 | Tool choice, each route, retries, web fallback, privacy rules, injection, courtesies |[m
[32m+[m[32m| `test_app.py` | 34 | The page, driven with Streamlit's test tool |[m
 | `test_tools.py` | 29 | GitHub, the SQL tool and its safety rules, web search |[m
 | `test_rag.py` | 17 | Prompts, markers, conversation memory, rewriting |[m
 | `test_mcp_server.py` | 15 | Tools called through a real in-process MCP client |[m
[36m@@ -628,7 +632,7 @@[m [mClaude_Demo/[m
 ├── data/               the knowledge base: 10 documents[m
 ├── docs/               the design for version 2[m
 ├── evals/              model and retrieval evaluation: scripts, run logs, report[m
[31m-├── tests/              317 tests and shared fakes[m
[32m+[m[32m├── tests/              332 tests and shared fakes[m
 ├── .github/workflows/  continuous integration[m
 ├── .mcp.json           registers the MCP server with Claude Code[m
 ├── .env.example        template for settings[m
[1mdiff --git a/README.md b/README.md[m
[1mindex 8427aac..a04b3b3 100644[m
[1m--- a/README.md[m
[1m+++ b/README.md[m
[36m@@ -57,7 +57,7 @@[m [malong the way.[m
 ```mermaid[m
 flowchart LR[m
     message --> screen[m
[31m-    screen -.->|refused| answer[m
[32m+[m[32m    screen -.->|refused or courtesy| answer[m
     screen -.-> choose_tool[m
     choose_tool -.-> documents[m
     documents -.->|not covered| web_search[m
[1mdiff --git a/app.py b/app.py[m
[1mindex 0cb3d47..7d0d41a 100644[m
[1m--- a/app.py[m
[1m+++ b/app.py[m
[36m@@ -297,7 +297,8 @@[m [mdef show_message(message):[m
         # Only the bot's answers have a source; a visitor's own[m
         # message and the reply to an unclear one do not.[m
         if (message.get("tool")[m
[31m-                and message["status"] not in ("unclear", "blocked")):[m
[32m+[m[32m                and message["status"] not in ("unclear", "blocked",[m
[32m+[m[32m                                              "courtesy")):[m
             st.caption(SOURCE_LABELS[message["tool"]])[m
         if message.get("commits"):[m
             show_commits(message["commits"])[m
[36m@@ -398,13 +399,20 @@[m [mquestion = st.chat_input([m
 if not messages and not question:[m
     question = pick_example()[m
 if question and question.strip() and not limit_reached:[m
[31m-    st.session_state.asked += 1[m
[31m-    # Failed answers are left out: they say nothing about the topic.[m
[32m+[m[32m    # Failed answers and courtesies are left out: they say nothing[m
[32m+[m[32m    # about the topic.[m
     history = [message for message in messages[m
[31m-               if not message.get("error")][m
[31m-    messages.append({"role": "user", "content": question})[m
[32m+[m[32m               if not message.get("error") and not message.get("courtesy")][m
     with st.spinner("Searching the documents..."):[m
[31m-        messages.append(answer_question(question, history))[m
[32m+[m[32m        reply = answer_question(question, history)[m
[32m+[m[32m    # A courtesy such as "thanks" calls no model, so it is not counted[m
[32m+[m[32m    # as a question.[m
[32m+[m[32m    reply["courtesy"] = reply.get("status") == "courtesy"[m
[32m+[m[32m    if not reply["courtesy"]:[m
[32m+[m[32m        st.session_state.asked += 1[m
[32m+[m[32m    messages.append({"role": "user", "content": question,[m
[32m+[m[32m                     "courtesy": reply["courtesy"]})[m
[32m+[m[32m    messages.append(reply)[m
     # Redraw from the top so the chat box and the counter reflect the[m
     # question just asked.[m
     st.rerun()[m
[1mdiff --git a/assistant/chat.py b/assistant/chat.py[m
[1mindex 9d2dbf6..0a53a60 100644[m
[1m--- a/assistant/chat.py[m
[1m+++ b/assistant/chat.py[m
[36m@@ -52,6 +52,31 @@[m [mBLOCKED_MESSAGE = ([m
     "about the project instead."[m
 )[m
 [m
[32m+[m[32m# A message that is only a courtesy gets a fixed reply from code, so[m
[32m+[m[32m# no model is called for it.  The lists are deliberately short: any[m
[32m+[m[32m# other wording goes to the model as before.[m
[32m+[m[32mTHANKS = frozenset({[m
[32m+[m[32m    "thanks", "thank you", "thanks a lot", "thanks so much",[m
[32m+[m[32m    "thanks very much", "thank you so much", "thank you very much",[m
[32m+[m[32m    "many thanks", "much appreciated", "thx", "ty", "cheers",[m
[32m+[m[32m})[m
[32m+[m[32mGREETINGS = frozenset({[m
[32m+[m[32m    "hi", "hello", "hey", "hi there", "hello there", "hey there",[m
[32m+[m[32m    "good morning", "good afternoon", "good evening", "greetings",[m
[32m+[m[32m})[m
[32m+[m[32mGOODBYES = frozenset({[m
[32m+[m[32m    "bye", "goodbye", "good bye", "bye bye", "see you", "see you later",[m
[32m+[m[32m    "good night", "take care", "have a good day", "have a nice day",[m
[32m+[m[32m})[m
[32m+[m[32m# Words that may come before a courtesy, as in "ok thanks".[m
[32m+[m[32mCOURTESY_FILLERS = ("ok", "okay", "alright", "great", "awesome",[m
[32m+[m[32m                    "perfect", "cool", "nice", "got it")[m
[32m+[m[32mCOURTESY_REPLIES = ([m
[32m+[m[32m    (THANKS, "You're welcome! Ask me anything else about the project."),[m
[32m+[m[32m    (GREETINGS, f"Hello! {rag.UNCLEAR_MESSAGE}"),[m
[32m+[m[32m    (GOODBYES, "Goodbye, and thanks for trying the demo!"),[m
[32m+[m[32m)[m
[32m+[m
 # Shown at the start of an answer that came from the web, so the[m
 # reader is never left to assume it came from the documents.[m
 WEB_NOTICE = ([m
[36m@@ -82,6 +107,24 @@[m [mEMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")[m
 PHONE_PATTERN = re.compile(r"(?:\d[\s().-]*){9,}")[m
 [m
 [m
[32m+[m[32mdef courtesy_reply(text):[m
[32m+[m[32m    """Return the fixed reply to a message that is only a courtesy.[m
[32m+[m
[32m+[m[32m    Return None for any other message.  The whole message must be a[m
[32m+[m[32m    courtesy: "thanks, and what is a chunk?" is still a question.[m
[32m+[m[32m    Capitals, punctuation and emoji are ignored.[m
[32m+[m[32m    """[m
[32m+[m[32m    phrase = " ".join(re.sub(r"[^a-z ]", " ", text.lower()).split())[m
[32m+[m[32m    candidates = {phrase}[m
[32m+[m[32m    for filler in COURTESY_FILLERS:[m
[32m+[m[32m        if phrase.startswith(f"{filler} "):[m
[32m+[m[32m            candidates.add(phrase[len(filler) + 1:])[m
[32m+[m[32m    for phrases, reply in COURTESY_REPLIES:[m
[32m+[m[32m        if candidates & phrases:[m
[32m+[m[32m            return reply[m
[32m+[m[32m    return None[m
[32m+[m
[32m+[m
 def choose_tool(question, history=None, client=None):[m
     """Return the tool for `question` and the question made standalone.[m
 [m
[36m@@ -299,11 +342,26 @@[m [mdef blocked(question, message):[m
             "search_query": question}[m
 [m
 [m
[32m+[m[32mdef courtesy(question, reply):[m
[32m+[m[32m    """Return the result for a courtesy answered with a fixed reply."""[m
[32m+[m[32m    return {"answer": reply, "status": "courtesy", "answered": False,[m
[32m+[m[32m            "tool": "courtesy", "sources": [], "passages": [],[m
[32m+[m[32m            "search_query": question}[m
[32m+[m
[32m+[m
 def screen_node(state, runtime: Runtime[ChatContext]):[m
[31m-    """Refuse a message that is too long or looks like an injection."""[m
[32m+[m[32m    """Settle a message that needs no answer from a source.[m
[32m+[m
[32m+[m[32m    A message that is too long is refused, a courtesy such as "thanks"[m
[32m+[m[32m    gets its fixed reply, and a message that looks like an injection[m
[32m+[m[32m    is refused.  The first two cost no model call.[m
[32m+[m[32m    """[m
     question = state["question"][m
     if len(question) > MAX_QUESTION_CHARS:[m
         return {"result": blocked(question, TOO_LONG_MESSAGE)}[m
[32m+[m[32m    reply = courtesy_reply(question)[m
[32m+[m[32m    if reply:[m
[32m+[m[32m        return {"result": courtesy(question, reply)}[m
     if guard.looks_like_injection(question,[m
                                   client=runtime.context["client"]):[m
         return {"result": blocked(question, BLOCKED_MESSAGE)}[m
[36m@@ -418,7 +476,8 @@[m [mdef build_graph():[m
     graph.add_node("data_answer", data_answer_node)[m
     graph.add_node("web_search", web_search_node)[m
     graph.add_edge(START, "screen")[m
[31m-    # A message that was refused goes no further.[m
[32m+[m[32m    # A message that was refused, or was only a courtesy, goes no[m
[32m+[m[32m    # further.[m
     graph.add_conditional_edges([m
         "screen",[m
         lambda state: "refuse" if state.get("result") else "continue",[m
[36m@@ -472,7 +531,8 @@[m [mdef respond(question, collection, history=None, client=None):[m
     """Answer `question` with whichever tool fits it.[m
 [m
     Return the same dict as `rag.answer`, plus `tool`: the name of the[m
[31m-    tool that produced the answer.  A github answer also has[m
[32m+[m[32m    tool that produced the answer.  A message that is only a courtesy[m
[32m+[m[32m    has the status "courtesy".  A github answer also has[m
     `commits`, the list the answer was drawn from, an nyc_data[m
     answer has `query`, the SQL that ran and its result, and a web[m
     answer has `web_results`.  A tool that fails raises[m
[1mdiff --git a/data/rag.md b/data/rag.md[m
[1mindex 1b00a80..72ab795 100644[m
[1m--- a/data/rag.md[m
[1m+++ b/data/rag.md[m
[36m@@ -171,10 +171,13 @@[m [mrewritten question with the retrieved passages.[m
 [m
 ## What happens when a message is a greeting, thanks or unclear?[m
 [m
[31m-The model is told to reply with a second fixed marker when a message[m
[31m-is only a greeting or thanks, or is too unclear to answer. The code[m
[31m-detects that marker and replies with a short list of what the bot can[m
[31m-help with. This is different from a real question the documents do[m
[32m+[m[32mA message that is only a courtesy, such as "thanks", "hi" or "bye", is[m
[32m+[m[32mmatched against a short fixed list in the code and gets a fixed[m
[32m+[m[32mfriendly reply. No model is called, so it costs no tokens and does not[m
[32m+[m[32mcount against the question limit. Any other wording goes to the model,[m
[32m+[m[32mwhich is told to reply with a second fixed marker when a message is a[m
[32m+[m[32mgreeting or thanks, or is too unclear to answer. The code detects that[m
[32m+[m[32mmarker and replies with a short list of what the bot can help with. This is different from a real question the documents do[m
 not cover, such as the capital of France, which is still refused.[m
 [m
 ## Why is the model's temperature set to 0?[m
[1mdiff --git a/evals/compare_models.py b/evals/compare_models.py[m
[1mindex d1dff8e..24f11f7 100644[m
[1m--- a/evals/compare_models.py[m
[1m+++ b/evals/compare_models.py[m
[36m@@ -221,6 +221,9 @@[m [mdef main():[m
     # Measure each model alone, and the documents path without the web.[m
     llm.FALLBACK_MODEL = ""[m
     tools.web_search_available = lambda: False[m
[32m+[m[32m    # The greeting case measures whether a model returns the marker it[m
[32m+[m[32m    # is told to, so the fixed courtesy replies are switched off.[m
[32m+[m[32m    chat.courtesy_reply = lambda text: None[m
 [m
     collection = get_collection()[m
     add_documents(collection, DATA_FOLDER)[m
[1mdiff --git a/tests/test_app.py b/tests/test_app.py[m
[1mindex b762ec6..a893fab 100644[m
[1m--- a/tests/test_app.py[m
[1m+++ b/tests/test_app.py[m
[36m@@ -476,3 +476,41 @@[m [mdef test_secrets_are_removed_from_error_details(app, monkeypatch):[m
 [m
     detail = app.chat_message[1].code[0].value[m
     assert detail == "RuntimeError: bad key [redacted] used"[m
[32m+[m
[32m+[m
[32m+[m[32mdef fake_courtesy(question, collection, history=None):[m
[32m+[m[32m    return {"answer": "You're welcome!", "status": "courtesy",[m
[32m+[m[32m            "answered": False, "tool": "courtesy", "sources": [],[m
[32m+[m[32m            "passages": [], "search_query": question}[m
[32m+[m
[32m+[m
[32m+[m[32mdef test_courtesy_is_not_counted_as_a_question(app, monkeypatch):[m
[32m+[m[32m    log_in(app)[m
[32m+[m[32m    monkeypatch.setattr(chat, "respond", fake_courtesy)[m
[32m+[m[32m    ask(app, "thanks")[m
[32m+[m[32m    ask(app, "thanks")[m
[32m+[m[32m    ask(app, "thanks")[m
[32m+[m
[32m+[m[32m    # The limit in these tests is 2 questions.[m
[32m+[m[32m    assert not app.exception[m
[32m+[m[32m    assert not app.chat_input[0].disabled[m
[32m+[m[32m    reply = app.chat_message[-1][m
[32m