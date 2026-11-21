import { createElement, type ReactElement } from "react"
import { ArchitectureFlow } from "./architecture-flow"
import { LockerSequence } from "./locker-sequence"
import { ThreadModel } from "./thread-model"
import { FocusPageLayout } from "./focus-page"
import { RoadmapMilestones } from "./roadmap"

/**
 * Which figure replaces which fence in which document. Keyed by source file,
 * then by the heading the diagram sits under, then by its order in that
 * section, so inserting a Mermaid block cannot silently move a figure.
 */
const registry: Record<string, Record<string, Array<() => ReactElement>>> = {
  "docs/ARCHITECTURE.md": {
    "1. System Architecture Overview": [ArchitectureFlow],
    "2. Core Subsystems": [LockerSequence],
    "3. Concurrency & Threading Model": [ThreadModel],
  },
  "docs/ATTENTION_WELLNESS.md": {
    "5. Focus page redesign": [FocusPageLayout],
  },
  "ROADMAP.md": {
    "Roadmap Milestones Overview": [RoadmapMilestones],
  },
}

/**
 * Documents that draw a figure in ```text box characters rather than Mermaid.
 * The key is the H2 the art sits under.
 */
const textArt: Record<string, Record<string, Array<() => ReactElement>>> = {
  "docs/ATTENTION_WELLNESS.md": {
    "5. Focus page redesign": [FocusPageLayout],
  },
}

/** The figure for a fence, or null when the block is not one we have drawn. */
export function diagramFor(file: string, heading: string, seen: { n: number }) {
  const at = (registry[file] ?? textArt[file])?.[heading]
  const index = seen.n
  seen.n += 1
  if (!at || !at[index]) return null
  // The registry holds components; the renderer only needs their output.
  return createElement(at[index])
}
