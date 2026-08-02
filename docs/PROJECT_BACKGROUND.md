# Evolution Project Background

> **Version**: 3.8.0 (2026-08-01)  
> **Author**: lemen  
> **Status**: Implemented (V3.8.0)

🌐 **Language / 语言**: [English](PROJECT_BACKGROUND.md) | [中文](PROJECT_BACKGROUND.zh-CN.md)

> **Version History**: See [`VERSION_HISTORY.md`](./VERSION_HISTORY.md)

---

## 1. Project Origin

### 1.1 Two Major Pain Points

#### Pain Point 1: AI's "Amnesia"

> AI often forgets important key information during long-running tasks, repeatedly makes the same mistakes, and even treats incorrect information as correct when passing it into context — forming a death loop.

**Specific manifestations**:
- Forgets environment configurations (e.g., Python version, network settings)
- Repeats the same mistakes (e.g., using incorrect commands)
- Propagates previous error information as correct information
- Falls into death loops, unable to break free

**Impact**:
- Low efficiency — users need to remind AI repeatedly
- Poor user experience — AI feels "unreliable"
- Wasted time and resources

---

#### Pain Point 2: Human "Growth Deficit"

> From the moment a human assigns a task to AI until receiving the results, there may be N rounds of communication. The human may only be repeatedly reviewing and correcting errors, without learning any new knowledge or achieving effective self-improvement. This is truly regrettable.

**Specific manifestations**:
- Users act merely as the "client" — submitting demands, reviewing, and receiving deliverables
- No new knowledge is gained from the collaboration process
- The next collaboration starts at the same level — no improvement
- Repeated communication wastes time

**Impact**:
- User capabilities do not grow
- Collaboration efficiency cannot improve
- Users remain "outsiders" and struggle to express requirements accurately

---

## 2. Core Insights

### 2.1 Understanding of LLMs

> LLMs are already trained. Making them smarter is very difficult unless retrained — which is impractical for most people. So the only option is to add plugin/extension capabilities to LLMs. My understanding of this "harness" includes memory stores, MCP, Skill, Plugin, Web Search, and other tool invocations.

**Core viewpoints**:
- Don't expect the LLM itself to become smarter
- Enhance LLM capabilities through "plugins/extensions"
- Extensions include: memory stores, MCP, Skill, Plugin, Web Search, etc.

---

### 2.2 Understanding of Task Completion

> Using AI to execute tasks — completing them and meeting expectations — is my most basic and direct goal. AI is smart enough, but it can be unstable, may explore down wrong paths for a long time, and can even form death loops. This brings us back to point 1 above: add plugin tools to AI so it better understands our intentions and completes our tasks more smoothly.

**Core viewpoints**:
- Basic goal: complete tasks and meet expectations
- AI's problems: unstable, may take detours, may enter death loops
- Solution: add plugin tools to help AI better understand intent

---

### 2.3 Understanding of Human Growth

> Humans should not merely serve as requirement proposers, process reviewers, and task deliverable receivers during AI task execution. They should also learn truly useful knowledge throughout the process, so that the next time they collaborate with AI, they can be more accurate, more efficient, more thorough, and more valuable.

**Core viewpoints**:
- Humans should not just be the "client"
- They should learn during the collaboration process
- Next collaboration should be more accurate, efficient, thorough, and valuable

---

## 3. Specific Requirements

### 3.1 Requirement 1: Environment Awareness and Condition Notification

> Let AI inform the human about what conditions are needed to complete the task, what conditions currently exist, what is still missing, and how it plans to handle it.

**Examples**:
- Task 1 requires a WSL environment; Ubuntu is already available, but the network cannot pass through directly — the plan is to configure mirror mode to share and pass through the host network
- Task 2 requires a local LLM; the computer has Ollama, but no model yet — the plan is to download the qwen4-36b model

**Value**:
- Lets users understand the full picture of the task
- Knows current status and missing conditions
- Understands AI's processing plan

---

### 3.2 Requirement 2: Easy-to-Understand Technical Explanations

> I'm a tech novice — I don't understand code or professional terminology. But I want to learn. However, comprehensive fine-grained learning seems impossible — there's no time. So this really tests AI: what to explain and how to explain it. The trade-offs are complex, and I haven't figured it all out myself.

**Specific challenges**:
- When explaining code: cover the framework? Or focus on key impactful parts?
- Select content to explain based on the user's basic profile?
- How to explain complex professional techniques in a way that is accessible, vivid, illustrated, and easy to understand?

**Expectations**:
- AI can adjust explanation depth based on user level
- Easy to understand, avoiding excessive jargon
- Vivid and illustrative, preferably with both text and images

---

### 3.3 Requirement 3: Prompt Improvement Guide

> The requirements or problems I raise may not be concise or accurate enough. This can lead to repeated communication with AI, which costs significant time. So I want AI to give me a better prompt guide once a task reaches a milestone (i.e., after a certain number of communication rounds), teaching me how to write prompts for that task or problem in the most efficient and clear way.

**Value**:
- Reduce time costs from repeated communication
- Help users learn to express requirements better
- Improve efficiency of the next collaboration

---

### 3.4 Requirement 4: Honest Acceptance Notification

> After many tasks are completed, AI cannot verify results the way humans do. For example, AI often verifies via CLI rather than GUI. The underlying verification may appear correct, but what humans see on the surface may actually have problems. In such cases, AI should honestly inform the human and let them perform a secondary verification.

**Specific scenarios**:
- AI verifies via CLI, but humans need to verify via GUI
- Underlying validation is correct, but the surface appears problematic
- AI cannot control the desktop for visual verification (too costly)

**Expectations**:
- AI honestly communicates verification limitations
- Let humans decide whether secondary verification is needed
- Don't hide problems or exaggerate results

---

## 4. System Characteristics

### 4.1 Operation Mode

> This system runs essentially silently (though it can also be triggered manually). Sub agents run quietly in the background without entering the main session tasks or polluting the main conversation. Humans are barely aware of it.

**Core features**:
- **Silent operation**: Does not interfere with the main conversation
- **Background execution**: Sub agents work in the background
- **No main conversation pollution**: Keeps the main session clean
- **Barely noticeable to humans**: No active user intervention needed
- **Supports manual triggering**: Users can also trigger it proactively

---

### 4.2 Design Principles

Based on the above requirements, the following design principles are distilled:

| Principle | Description |
|-----------|-------------|
| **Task First** | The primary goal is completing the task, not running the system |
| **Natural Occurrence** | Learning and knowledge accumulation happen naturally during task execution |
| **Human Unaware** | Runs in the background without interfering with the main conversation |
| **Progressive Growth** | Both AI and humans grow through collaboration |
| **Honest Transparency** | AI honestly communicates limitations and problems |

---

## 5. Implementation Plan

### 5.1 Technology Selection

Based on the "plugin/extension" philosophy, Claude Code's **Skill system** is chosen as the implementation approach:

| Feature | Description |
|---------|-------------|
| **Progressive Disclosure** | Only the description is loaded at startup; full content loads on demand |
| **Manual Trigger** | Users trigger manually via `/evolution` |
| **Project-Level Storage** | Knowledge base is stored in `evolution/knowledge-base/` |
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
├── evolution/                       # Knowledge base
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

### 5.3 Bidirectional Functionality

**Evolution is a bidirectional sync system**:

| Function | Description |
|----------|-------------|
| **📖 Read** | Lets AI know "what is already known" |
| **✍️ Write** | Lets AI record "what has been newly learned" |

**Sync flow**:
```
User inputs /evolution
    ↓
📖 Read phase → Understand existing knowledge
    ↓
✍️ Write phase → Record new knowledge
    ↓
Report summary
```

---

## 6. Expected Benefits

### 6.1 Benefits for AI

| Benefit | Description |
|---------|-------------|
| **More Reliable** | Remembers key information, avoids repeated errors |
| **More Stable** | Won't go too far down the wrong path |
| **More Efficient** | Makes quick decisions based on historical experience |
| **More Honest** | Truthfully reports limitations and problems |

### 6.2 Benefits for Humans

| Benefit | Description |
|---------|-------------|
| **Learn Knowledge** | Gain technical knowledge from the collaboration process |
| **Improve Efficiency** | Learn to write better prompts |
| **Understand the Full Picture** | Know the task's conditions and status |
| **Participate in Verification** | Honest acceptance notifications let humans participate |

---

## 7. Success Metrics

### 7.1 AI-Side Metrics

| Metric | Target |
|--------|--------|
| **Repeated Error Rate** | Reduce by 80% |
| **Task Completion Rate** | Improve by 50% |
| **Context Consumption** | Save 66% (progressive disclosure) |

### 7.2 Human-Side Metrics

| Metric | Target |
|--------|--------|
| **Learning Efficiency** | Learn 1–2 knowledge points per collaboration |
| **Prompt Quality** | Reduce repeated communication rounds by 50% |
| **User Satisfaction** | Improve by 30% |

---

## 8. Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2026-07-21 | Initial version (Slash Command) |
| v2.0 | 2026-07-28 | Refactored to Skill system (progressive disclosure) |
| v3.0 | 2026-07-28 | Removed auto version, simplified system |
| v3.1 | 2026-07-29 | Added initialization command, conversation export mechanism |
| v3.3 | 2026-07-30 | Fixed JSON serialization crash, CJK token estimation, cleanup safety |
| v3.4 | 2026-07-31 | Modular refactoring, SKILL.md split, config.yaml unified configuration |
| v3.5 | 2026-07-31 | Refactored based on writing-great-skills rules, SKILL.md streamlined |
| v3.6 | 2026-08-01 | Split `/evolution init` into standalone command `/evolution-init` |
| v3.7 | 2026-08-01 | Fixed `/evolution-init` command, full history export via evolution-export.py |
| v3.8 | 2026-08-01 | Fixed three bugs: enforced script + disabled manual glob, find_jsonl_file, validation |

---

## 9. References

### 9.1 Project Documentation

- [Design Document](./DESIGN_V3.1.0.md)
- [Installation Guide](./INSTALLATION_GUIDE.md)
- [Version History](./VERSION_HISTORY.md)
- [Documentation Index](./README.md)

### 9.2 Official Documentation

- [Extend Claude with skills](https://code.claude.com/docs/en/skills)
- [How Claude remembers your project](https://code.claude.com/docs/en/memory)

---

## 10. Conclusion

> **Evolution is not a tool — it is a way of collaboration.**
> 
> It makes AI more reliable through collaboration, and makes humans more powerful through collaboration.
> 
> The ultimate goal: AI and humans growing together through collaboration.

---

**End of Document**
