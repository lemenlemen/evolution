# Evolution Project Background

🌐 **Language / 语言**: [English](PROJECT_BACKGROUND.md) | [中文](PROJECT_BACKGROUND.zh-CN.md)

> **Version**: 3.9.0 (2026-08-01)  
> **Author**: lemen  
> **Status**: Implemented (V3.9.0)

> **Version history**: see [`VERSION_HISTORY.md`](./VERSION_HISTORY.md)

---

## 1. Project Origin

### 1.1 Two Major Pain Points

#### Pain Point 1: AI's "Amnesia"

> When executing long-horizon tasks, AI often forgets important key information, repeatedly makes the same mistake, and even passes erroneous information into the context as if it were correct, thus forming an infinite loop.

**Specific manifestations**:
- Forgetting environment configuration (such as Python version, network configuration)
- Repeatedly making the same mistake (such as using the wrong command)
- Spreading previous erroneous information as if it were correct
- Forming an infinite loop, unable to break free

**Impact**:
- Low efficiency; the user needs to remind repeatedly
- Poor user experience; AI feels "unreliable"
- Wasting time and resources

---

#### Pain Point 2: Humanity's "Missing Growth"

> From assigning a task to AI to receiving the result, there may be N rounds of communication. The human may just be repeatedly accepting and correcting, without learning new knowledge or achieving effective self-improvement. This is a great pity.

**Specific manifestations**:
- The user is just the "client", proposing requirements, accepting, and receiving results
- No new knowledge is learned from the collaboration process
- The next collaboration is at the same level, with no improvement
- Repeated communication wastes time cost

**Impact**:
- The user's abilities do not grow
- Collaboration efficiency cannot improve
- The user remains a "layman", unable to express requirements accurately

---

## 2. Core Insights

### 2.1 Understanding of LLMs

> An LLM is already trained. Making it smarter is very hard unless it is retrained, which is impractical for ordinary people. So we can only add an extension to the LLM. This extension, in my understanding, is the harness—it can be a memory store, MCP, skill, plugin, web search, and other tool invocations.

**Core viewpoints**:
- We do not expect the LLM itself to become smarter
- Enhance the LLM's capabilities through "extensions"
- Extensions include: memory store, MCP, Skill, Plugin, Web Search, etc.

---

### 2.2 Understanding of Task Completion

> Using AI to execute tasks, being able to complete them and meet expectations is my most basic and most direct goal. AI is smart enough, but it may be unstable, may explore and dig into a wrong path for a long time, and may even form an infinite loop. This calls for the point 1 I just mentioned: add extension tools to the AI so that it can better understand our intent and complete our tasks more smoothly.

**Core viewpoints**:
- Basic goal: complete the task and meet expectations
- AI's problems: unstable, may take detours, may loop infinitely
- Solution: add extension tools so AI understands intent better

---

### 2.3 Understanding of Human Growth

> In AI task execution, humans should not only act as the requirement proposer, process acceptor, and task result receiver. They should also learn genuinely useful knowledge in the process, so that the next collaboration with AI can be more accurate, more efficient, more thorough, and more valuable.

**Core viewpoints**:
- Humans should not just be the "client"
- They should learn during the collaboration process
- The next collaboration should be more accurate, efficient, thorough, and valuable

---

## 3. Specific Requirements

### 3.1 Requirement 1: Environment Awareness and Condition Notification

> Let AI inform humans what conditions are needed to complete the task, what conditions currently exist, what is still missing, and how it plans to handle it.

**Examples**:
- Completing task 1 requires a WSL environment. Ubuntu is already available, but the network cannot pass through directly yet. The plan is to configure it into mirror mode to share the host's direct network.
- Completing task 2 requires a local LLM. The current computer has Ollama, but no model yet. The plan is to download the qwen4-36b model.

**Value**:
- Let the user understand the full picture of the task
- Know the current state and missing conditions
- Understand AI's handling plan

---

### 3.2 Requirement 2: Plain and Easy-to-Understand Technical Explanations

> I am a tech novice and do not understand code or many technical terms, but I want to learn. Yet full, detailed learning seems impossible—there is no time. So this heavily tests the AI: what to explain and how to explain it. The trade-offs here are complex, and I have not figured them out myself.

**Specific challenges**:
- When explaining code, explain only the framework? Or the few key impactful ones?
- Pick out corresponding content to explain based on the user's basic profile?
- How to explain professional, complex technology in an accessible, vivid, illustrated, and easy-to-understand way?

**Expectations**:
- AI can adjust the depth of explanation according to the user's level
- Plain and easy to understand, avoiding excessive technical terms
- Vivid; ideally illustrated with both text and images

---

### 3.3 Requirement 3: Prompt Improvement Guide

> The requirements or questions I propose may not be concise or accurate enough. This process may involve repeated communication with AI, which is actually a considerable time cost. So I want AI, when the task reaches a milestone (that is, after a certain number of communication rounds), to give me a better prompt guide, so I can learn how to write a prompt for this task or question in the most efficient and clearest way.

**Value**:
- Reduce the time cost of repeated communication
- Let the user learn how to express requirements better
- Improve the efficiency of the next collaboration

---

### 3.4 Requirement 4: Honest Acceptance Notification

> After many tasks are completed, AI cannot accept them the way humans do. For example, much of the time AI accepts from the CLI rather than the GUI. The underlying acceptance may look correct, but the surface may actually have problems for humans. At this point, AI should honestly inform humans and let them accept again.

**Specific scenarios**:
- AI accepts from the CLI, but humans need to accept from the GUI
- Underlying verification is correct, but the surface looks problematic
- AI cannot control the computer desktop for visual acceptance (high cost)

**Expectations**:
- AI honestly informs about the limitations of acceptance
- Let humans decide whether acceptance is needed again
- Do not conceal problems, do not exaggerate results

---

## 4. System Characteristics

### 4.1 Operation Mode

> This system is **manually triggered**: after the user enters `/evolution-init` or `/evolution`, sub agents
> execute export and analysis in the background, without entering the main session task, so as to pollute the main conversation as little as possible.
> (v3.0.0 has removed the auto-trigger version; auto-trigger exists only as a future plan and is not implemented.)

**Core characteristics**:
- **Manual trigger**: all synchronization requires the user to actively run `/evolution-init` / `/evolution`
- **Background execution**: sub agents work in the background; the main agent only does scheduling and summary display
- **No pollution of the main conversation**: knowledge base operations are completed in sub agents, keeping the main session clean

> ⚠️ If not manually triggered for a long time, conversations during that period will not be exported and analyzed, and the knowledge base will stop updating.

---

### 4.2 Design Principles

Based on the above requirements, the following design principles are distilled:

| Principle | Description |
|------|------|
| **Task first** | The primary goal is to complete the task, not to run the system |
| **Natural occurrence** | Learning and accumulation occur naturally during task execution |
| **Background isolation** | sub agents run in the background without disturbing the main conversation |
| **Progressive growth** | Both AI and humans grow through collaboration |
| **Honest and transparent** | AI honestly informs about limitations and problems |

---

## 5. Implementation Plan

### 5.1 Technology Choice

Based on the "extension" concept, Claude Code's **Skill system** is chosen as the implementation plan:

| Feature | Description |
|------|------|
| **Progressive disclosure** | At startup only the description is loaded; full content is loaded on demand |
| **Manual trigger** | The user triggers manually via `/evolution-init` / `/evolution` (no auto-trigger) |
| **Project-level storage** | The knowledge base is stored in `evolution/knowledge-base/` |
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
└── evolution/                       # knowledge base
    └── knowledge-base/
        ├── kb-index.md               # index
        ├── facts.md                  # key facts
        ├── pitfalls.md               # pitfalls
        ├── state.md                  # current state
        ├── growth-notes.md           # learning notes
        ├── prompt-improvements.md    # Prompt improvements
        ├── alignment.md              # alignment checklist
        └── decisions.md              # decision log
```

---

### 5.3 Bidirectional Capabilities

**Evolution is a bidirectional synchronization system**:

| Capability | Description |
|------|------|
| **📖 Read** | Let AI know "what it already knows" |
| **✍️ Write** | Let AI record "what it newly learned" |

**Synchronization flow**:
```
User enters /evolution
    ↓
📖 Read phase → understand existing knowledge
    ↓
✍️ Write phase → record new knowledge
    ↓
Report summary
```

---

## 6. Expected Benefits

### 6.1 Benefits for AI

| Benefit | Description |
|------|------|
| **More reliable** | Remembers key information, avoids repeated mistakes |
| **More stable** | Will not go too far down a wrong path |
| **More efficient** | Makes decisions quickly based on historical experience |
| **More honest** | Truthfully informs about limitations and problems |

### 6.2 Benefits for Humans

| Benefit | Description |
|------|------|
| **Learning knowledge** | Learn technical knowledge from the collaboration process |
| **Improved efficiency** | Learn to write prompts better |
| **Understanding the full picture** | Understand the task's conditions and state |
| **Participating in acceptance** | Honest acceptance notification lets humans participate |

---

## 7. Success Metrics

### 7.1 AI-side Metrics

| Metric | Target |
|------|------|
| **Repeated error rate** | Reduced by 80% |
| **Task completion rate** | Increased by 50% |
| **Context consumption** | Saved by 66% (progressive disclosure) |

### 7.2 Human-side Metrics

| Metric | Target |
|------|------|
| **Learning efficiency** | Learn 1-2 knowledge points per collaboration |
| **Prompt quality** | 50% fewer repeated communication rounds |
| **User satisfaction** | Increased by 30% |

---

## 8. Version History

For the complete version history, see [`docsV3/VERSION_HISTORY.md`](./VERSION_HISTORY.md).

---

## 9. References

### 9.1 Project Documents

- [Design Document](./DESIGN_V3.1.0.md)
- [Installation Guide](./INSTALLATION_GUIDE.md)
- [Version History](./VERSION_HISTORY.md)
- [Documentation Index](./README.md)

### 9.2 Official Documentation

- [Extend Claude with skills](https://code.claude.com/docs/en/skills)
- [How Claude remembers your project](https://code.claude.com/docs/en/memory)

---

## 10. Conclusion

> **Evolution is not a tool, but a way of collaborating.**
> 
> It makes AI more reliable through collaboration, and makes humans more capable through collaboration.
> 
> Ultimately achieving: AI and humans growing together through collaboration.

---

**End of document**
