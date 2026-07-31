# Evolution Project Background

> **Version**: 3.3.0 (2026-07-31)  
> **Author**: lemen  
> **Status**: Implemented (V3.3.0)

> **Version History**: See [`VERSION_HISTORY.md`](./VERSION_HISTORY.md)

---

## 1. Project Origins

### 1.1 Two Major Pain Points

#### Pain Point 1: AI's "Amnesia"

> During long-running tasks, AI often forgets important key information, repeatedly makes the same mistakes, and even treats incorrect information as correct — feeding it back into context and creating a vicious cycle.

**Specific Manifestations**:
- Forgetting environment configurations (e.g., Python version, network settings)
- Repeating the same mistakes (e.g., using incorrect commands)
- Propagating previous errors as correct information
- Getting trapped in a vicious cycle with no way out

**Impact**:
- Low efficiency — users need to repeat reminders
- Poor user experience — AI feels "unreliable"
- Wasted time and resources

---

#### Pain Point 2: Humans' "Growth Gap"

> Between the moment a human gives a task to an AI and the moment they receive the result, there may be N rounds of communication. The human may end up merely accepting deliverables and fixing errors, without learning anything new or achieving meaningful self-improvement — and that is a real missed opportunity.

**Specific Manifestations**:
- The user acts merely as a "client" — submitting requirements, reviewing, and receiving deliverables
- No new knowledge gained from the collaboration process
- Same skill level at the next collaboration — no growth
- Repeated communication wastes time

**Impact**:
- User capabilities do not grow
- Collaboration efficiency cannot improve
- Users remain "outsiders," struggling to express requirements accurately

---

## 2. Core Insights

### 2.1 Understanding LLMs

> LLMs are already fully trained. Making them smarter is extremely difficult unless you retrain them, which is impractical for most people. So the only option is to give LLMs extensions — and by extensions, I mean the harness: tool invocations like knowledge bases, MCP, Skill, plugins, and web search.

**Core Viewpoints**:
- Don't expect the LLM itself to become smarter
- Enhance LLM capabilities through "extensions"
- Extensions include: knowledge bases, MCP, Skill, plugins, web search, etc.

---

### 2.2 Understanding Task Completion

> When using AI to execute tasks, completing the task and meeting expectations is my most basic and direct goal. AI is smart enough, but it can be unstable — it may wander down the wrong path for a long time, or even get stuck in an infinite loop. That's exactly why I mentioned point 1 earlier: give AI extension tools so it can better understand our intent and complete our tasks more smoothly.

**Core Viewpoints**:
- Basic goal: Complete the task and meet expectations
- AI's problems: Unstable, may take detours, may get stuck in loops
- Solution: Add extension tools so AI better understands intent

---

### 2.3 Understanding Human Growth

> Humans should not merely be the ones who submit requirements, review progress, and receive deliverables during an AI task. They should also learn genuinely useful knowledge throughout the process — so that next time they collaborate with AI, they can be more accurate, more efficient, more thorough, and more valuable.

**Core Viewpoints**:
- Humans should not just be "clients"
- They should learn during the collaboration process
- Next collaboration should be more accurate, efficient, thorough, and valuable

---

## 3. Specific Requirements

### 3.1 Requirement 1: Environment Awareness and Condition Reporting

> Let the AI tell the human what conditions are needed to complete the task, what conditions currently exist, what is still missing, and how it plans to handle the gaps.

**Examples**:
- Task 1 requires a WSL environment; Ubuntu is already available, but the network cannot reach it directly yet — the plan is to configure mirror mode to share the host's network
- Task 2 requires a local LLM; Ollama is installed, but no model is downloaded yet — the plan is to download the qwen4-36b model

**Value**:
- Lets the user understand the full picture of the task
- Shows current state and missing conditions
- Explains the AI's execution plan

---

### 3.2 Requirement 2: Plain-Language Technical Explanations

> I'm a tech novice — I don't understand code or many technical terms, but I want to learn. However, exhaustive fine-grained learning is not realistic given time constraints. This is where the real test for AI begins: what to explain and how to explain it. The trade-offs involved are complex, and I haven't fully figured it out myself.

**Specific Challenges**:
- When explaining code, should it cover the overall framework? Or just the key parts that matter?
- Should it tailor content to the user's basic profile?
- How to explain complex technical topics in a way that is accessible, vivid, illustrated, and easy to understand?

**Expectations**:
- AI adjusts explanation depth based on user level
- Plain language, avoiding excessive jargon
- Vivid and engaging, ideally with illustrations

---

### 3.3 Requirement 3: Prompt Improvement Guide

> The requirements or problems I raise may not be concise or accurate enough, leading to repeated rounds of communication with AI — which costs a lot of time. So I'd like that when a task reaches a milestone (i.e., after a certain number of communication rounds), AI could give me a better prompt guide, teaching me how to write prompts for that task or problem in the most efficient and clearest way.

**Value**:
- Reduces time cost from repeated communication
- Helps users learn to express requirements more effectively
- Improves efficiency of the next collaboration

---

### 3.4 Requirement 4: Honest Acceptance Reporting

> After many tasks are completed, AI cannot verify results the way humans do. For example, AI often verifies via CLI rather than GUI. The underlying verification may look correct, but the surface-level result may actually have problems. In such cases, AI should honestly inform the human and ask them to perform a secondary verification.

**Specific Scenarios**:
- AI verifies via CLI, but the human needs to verify via GUI
- Underlying verification passes, but the surface appearance has issues
- AI cannot control the desktop for visual verification (too costly)

**Expectations**:
- AI honestly reports verification limitations
- Lets humans decide whether re-verification is needed
- Does not hide problems or exaggerate results

---

## 4. System Features

### 4.1 Mode of Operation

> This system runs mostly in silent mode (though it can also be manually triggered), with sub agents running quietly in the background. It does not enter the main session task stream and does not pollute the main conversation. Humans are largely unaware of it.

**Core Features**:
- **Silent operation**: Does not interfere with the main conversation
- **Background execution**: Sub agents work in the background
- **No main conversation pollution**: Keeps the main session clean
- **Largely transparent to humans**: No active user intervention needed
- **Supports manual trigger**: Users can also trigger it proactively

---

### 4.2 Design Principles

Based on the requirements above, the following design principles are distilled:

| Principle | Description |
|-----------|-------------|
| **Task First** | The primary goal is to complete the task, not to run the system |
| **Natural Occurrence** | Learning and knowledge accumulation happen naturally during task execution |
| **Transparent to Humans** | Runs in the background without disrupting the main conversation |
| **Progressive Growth** | Both AI and humans grow through collaboration |
| **Honest and Transparent** | AI honestly reports limitations and issues |

---

## 5. Implementation

### 5.1 Technology Choice

Based on the "extension" philosophy, the **Skill system** of Claude Code was chosen as the implementation:

| Feature | Description |
|---------|-------------|
| **Progressive Disclosure** | Only the description is loaded at startup; full content loaded on demand |
| **Manual Trigger** | Users trigger manually via `/evolution` |
| **Project-Level Storage** | Knowledge base stored in `evolution/knowledge-base/` |
| **Separated from Auto Memory** | Does not pollute Claude Code's Auto Memory system |

---

### 5.2 System Architecture

```
<project>/
├── .claude/
│   └── skills/
│       └── evolution/
│           └── SKILL.md              # Skill definition
│
── evolution/                       # Knowledge base
    └── knowledge-base/
        ├── kb-index.md               # Index
        ├── facts.md                  # Key facts
        ├── pitfalls.md               # Pitfalls
        ├── state.md                  # Current state
        ├── growth-notes.md           # Learning notes
        ├── prompt-improvements.md    # Prompt improvements
        ├── alignment.md              # Alignment checklist
        └── decisions.md              # Decision log
```

---

### 5.3 Bidirectional Capability

**Evolution is a bidirectional sync system**:

| Function | Description |
|----------|-------------|
| **📖 Read** | Lets AI know "what is already known" |
| **✍️ Write** | Lets AI record "what was newly learned" |

**Sync Flow**:
```
User inputs /evolution
    ↓
📖 Read Phase → Understand existing knowledge
    ↓
✍️ Write Phase → Record new knowledge
    ↓
Summary report
```

---

## 6. Expected Benefits

### 6.1 Benefits for AI

| Benefit | Description |
|---------|-------------|
| **More Reliable** | Remembers key information, avoids repeated mistakes |
| **More Stable** | Won't go too far down the wrong path |
| **More Efficient** | Makes quick decisions based on historical experience |
| **More Honest** | Truthfully reports limitations and issues |

### 6.2 Benefits for Humans

| Benefit | Description |
|---------|-------------|
| **Knowledge Learning** | Learn technical knowledge from the collaboration process |
| **Improved Efficiency** | Learn to write better prompts |
| **Full Picture** | Understand task conditions and status |
| **Verification Participation** | Honest acceptance reporting lets humans participate |

---

## 7. Success Metrics

### 7.1 AI-Side Metrics

| Metric | Target |
|--------|--------|
| **Repeated Error Rate** | Reduced by 80% |
| **Task Completion Rate** | Improved by 50% |
| **Context Consumption** | Saved 66% (via progressive disclosure) |

### 7.2 Human-Side Metrics

| Metric | Target |
|--------|--------|
| **Learning Efficiency** | Learn 1-2 knowledge points per collaboration |
| **Prompt Quality** | Repeated communication rounds reduced by 50% |
| **User Satisfaction** | Improved by 30% |

---

## 8. Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-07-21 | Initial release (Slash Command) |
| v2.0 | 2026-07-28 | Refactored to Skill system (progressive disclosure) |

---

## 9. References

### 9.1 Project Documentation

- [Design Document](./DESIGN_V3.1.0.md)
- [Installation Guide](./INSTALLATION_GUIDE.md)
- [Version History](./VERSION_HISTORY.md)
- [Document Index](./README.md)

### 9.2 Official Documentation

- [Extend Claude with skills](https://code.claude.com/docs/en/skills)
- [How Claude remembers your project](https://code.claude.com/docs/en/memory)

---

## 10. Conclusion

> **Evolution is not a tool — it is a way of collaborating.**
> 
> It makes AI more reliable through collaboration, and makes humans more capable through collaboration.
> 
> The ultimate goal: AI and humans growing together through collaboration.

---

**End of Document**
