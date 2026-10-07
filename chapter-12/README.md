# Chapter 12 — Beyond the Recipes: Design the Application People Will Use

**Documentation and code snippets only. This chapter does not ship a runnable application.**

Each guide explains the intended use, the surrounding responsibilities, and the limits of one unchanged chapter code block. The snippets stay inside Markdown fences; there are no Python modules, package metadata, entry points, or application downloads for this chapter.

Read the guides in order when one fragment depends on an earlier helper. A syntax check is not an end-to-end test of an integration or product.

| Guide | Teaching point |
| --- | --- |
| [Give the User a Place in the Workflow](01-workflow-state-and-screen.md) | workflow state and screen |
| [Turn Requirements into a Problem You Can Solve](02-constrained-assignment.md) | constrained assignment |
| [Spend Model Calls Where They Help](03-model-routing-policy.md) | model routing policy |
| [Learn from Corrections Without Learning the Wrong Lesson](04-grouped-evaluation-split.md) | grouped evaluation split |
| [Choose the Next Change Deliberately](05-planning-outcome-message.md) | planning outcome message |

The chapter also discusses queueing and responsiveness without a code block. Its capacity argument assumes consistent measurement boundaries: waiting time and service time are different. Admission and duplicate detection belong in the same transaction; adding workers also requires exclusive job ownership and recovery rules. No queue implementation is implied by these snippet guides.
