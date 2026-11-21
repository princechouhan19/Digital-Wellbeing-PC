import type { ReactNode } from "react"
import { site } from "@/data/site"
import { diagramFor } from "./diagrams"

/**
 * A small Markdown renderer for the repository's own documentation.
 *
 * It covers what those files actually use: ATX headings, paragraphs, flat and
 * nested bullet and numbered lists, fenced code, blockquotes, GFM tables,
 * horizontal rules, and inline code, bold, italic and links. Long-form prose
 * is read here, so the parser is intentionally conservative: anything it does
 * not recognise is rendered as text rather than swallowed.
 */

export type Heading = { level: number; text: string; id: string }

/** GitHub's heading anchor rule, with the punctuation those documents use. */
export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[`*_~[\]()]/g, "")
    .replace(/[^\p{L}\p{N}\s-]/gu, "")
    .trim()
    .replace(/\s+/g, "-")
}

/**
 * Points a stale version reference at the current release. Off for the
 * changelog, where every old number is the point of the file.
 */
function rewriteVersions(text: string): string {
  if (!text.includes("4.")) return text
  // Keep the prefix the author used: file names have no "v", prose does.
  return text
    .replace(/\b([vV])?4\.\d\.\d\b/g, (_m, v?: string) => `${v ?? ""}${site.version}`)
    .replace(/\bv4\.\d\b/g, `v4.${site.version.split(".")[1]}`)
}

/** Splits a line into text and inline spans. Order matters: code, then links. */
function inline(source: string, keyBase = "", keepVersions = false): ReactNode[] {
  const out: ReactNode[] = []
  const pattern =
    /(`[^`]+`)|(\*\*[^*]+\*\*)|(\*[^*]+\*)|(\[[^\]]+\]\([^)]+\))|(https?:\/\/[^\s)]+)/g
  let last = 0
  let match: RegExpExecArray | null
  let n = 0

  // The docs are written against older builds. The number is data, so it is
  // corrected here once instead of being silently repeated on every page.
  const pushText = (value: string) => {
    if (!value) return
    out.push(keepVersions ? value : rewriteVersions(value))
  }

  while ((match = pattern.exec(source))) {
    pushText(source.slice(last, match.index))
    const token = match[0]
    const key = `${keyBase}-i${n++}`

    if (token.startsWith("`")) {
      const literal = token.slice(1, -1)
      out.push(
        <code key={key} className="doc-code">
          {keepVersions ? literal : rewriteVersions(literal)}
        </code>,
      )
    } else if (token.startsWith("**")) {
      out.push(
        <strong key={key} className="font-semibold text-ink">
          {token.slice(2, -2)}
        </strong>,
      )
    } else if (token.startsWith("*")) {
      out.push(<em key={key}>{token.slice(1, -1)}</em>)
    } else if (token.startsWith("[")) {
      const close = token.indexOf("](")
      const label = token.slice(1, close)
      const href = token.slice(close + 2, -1)
      const external = /^https?:/i.test(href)
      out.push(
        <a
          key={key}
          href={href}
          className="link-inline"
          {...(external ? { rel: "noreferrer", target: "_blank" } : {})}
        >
          {label}
        </a>,
      )
    } else {
      out.push(
        <a key={key} href={token} className="link-inline" rel="noreferrer" target="_blank">
          {token}
        </a>,
      )
    }
    last = match.index + token.length
  }
  pushText(source.slice(last))
  return out
}

const ALERT_NAMES: Record<string, string> = {
  NOTE: "Note",
  TIP: "Tip",
  IMPORTANT: "Important",
  WARNING: "Warning",
  CAUTION: "Caution",
}

export function renderMarkdown(
  markdown: string,
  options: { keepVersions?: boolean; file?: string } = {},
): { nodes: ReactNode[]; headings: Heading[] } {
  const keep = options.keepVersions ?? false
  // Diagrams are bound to the last heading, so a new section cannot inherit
  // the figure of the section above it.
  let section = ""
  const counts: Record<string, { n: number }> = {}
  const lines = markdown.replace(/\r\n/g, "\n").split("\n")
  const nodes: ReactNode[] = []
  const headings: Heading[] = []
  const used = new Map<string, number>()
  let key = 0

  const withKey = (node: ReactNode) => {
    void key
    return node
  }

  let firstH1 = true
  const heading = (level: number, raw: string) => {
    const text = raw.replace(/#+\s*$/, "").trim()
    if (level === 1 && firstH1) {
      // The document's own title is already the page h1.
      firstH1 = false
      return
    }
    let id = slugify(text)
    const seen = used.get(id) ?? 0
    used.set(id, seen + 1)
    if (seen) id = `${id}-${seen}`
    headings.push({ level, text: text.replace(/`/g, ""), id })
    // Only an H2 starts a new diagram section. A document may put its figure
    // under an H3 inside that section.
    if (level === 2) section = text.replace(/`/g, "").trim()
    const content = inline(text, `h${key}`, keep)
    const cls =
      level === 1
        ? "text-[clamp(1.75rem,3.6vw,2.5rem)] leading-[1.05] tracking-[-0.03em]"
        : level === 2
          ? "mt-12 text-[1.375rem] leading-tight tracking-[-0.02em] md:text-[1.625rem]"
          : level === 3
            ? "mt-8 text-[1.0625rem] leading-snug tracking-[-0.01em]"
            : "mt-6 text-[0.9375rem] leading-snug"
    const Tag = level === 1 ? "h1" : level === 2 ? "h2" : level === 3 ? "h3" : "h4"
    nodes.push(
      <Tag key={`h-${key++}`} id={id} className={`${cls} scroll-mt-28`}>
        {content}
      </Tag>,
    )
  }

  let i = 0
  while (i < lines.length) {
    const line = lines[i]

    // Blank
    if (!line.trim()) {
      i++
      continue
    }

    // Fenced code
    const fence = line.match(/^\s*```(\w*)/)
    if (fence) {
      const lang = fence[1]
      const body: string[] = []
      i++
      while (i < lines.length && !/^\s*```/.test(lines[i])) body.push(lines[i++])
      i++
      // A Mermaid block is replaced by the figure it describes, drawn in the
      // site's own tokens. Unknown blocks are dropped rather than shown as
      // source: a reader cannot use graph syntax.
      if (lang === "mermaid") {
        if (options.file) {
          counts[section] = counts[section] ?? { n: 0 }
          const figure = diagramFor(options.file, section, counts[section])
          if (figure) nodes.push(<div key={`figure-${key++}`}>{figure}</div>)
        }
        continue
      }
      // ```text blocks in these documents are terminal art: a page layout
      // drawn in box characters. Drawing them would break the reading column,
      // so the block is swapped for the figure it describes, or dropped.
      if (lang === "text") {
        if (options.file) {
          counts[section] = counts[section] ?? { n: 0 }
          const figure = diagramFor(options.file, section, counts[section])
          if (figure) nodes.push(<div key={`figure-${key++}`}>{figure}</div>)
        }
        continue
      }
      nodes.push(
        <figure key={`code-${key++}`} className="my-6 overflow-hidden rounded-lg border border-line">
          {lang ? (
            <figcaption className="border-b border-line bg-panel-2 px-4 py-1.5 font-mono text-[0.6875rem] uppercase tracking-[0.12em] text-muted">
              {lang === "powershell" ? "PowerShell" : lang}
            </figcaption>
          ) : null}
          <pre
            tabIndex={0}
            className="overflow-x-auto bg-panel px-4 py-3.5 text-[0.8125rem] leading-relaxed"
          >
            <code className="font-mono">{body.join("\n")}</code>
          </pre>
        </figure>,
      )
      continue
    }

    // Heading
    const h = line.match(/^(#{1,6})\s+(.*)$/)
    if (h) {
      heading(h[1].length, h[2])
      i++
      continue
    }

    // Horizontal rule
    if (/^\s*([-*_])\1{2,}\s*$/.test(line)) {
      nodes.push(<hr key={`hr-${key++}`} className="my-10 border-line" />)
      i++
      continue
    }

    // Table
    if (/^\s*\|/.test(line) && /^\s*\|[\s:|-]+\|?\s*$/.test(lines[i + 1] ?? "")) {
      const split = (row: string) =>
        row
          .trim()
          .replace(/^\|/, "")
          .replace(/\|$/, "")
          .split("|")
          .map((cell) => cell.trim())
      const head = split(line)
      const rows: string[][] = []
      i += 2
      while (i < lines.length && /^\s*\|/.test(lines[i])) rows.push(split(lines[i++]))
      nodes.push(
        <div key={`table-${key++}`} className="my-6 overflow-x-auto">
          <table className="doc-table">
            <thead>
              <tr>
                {head.map((cell, c) => (
                  <th key={c} scope="col">
                    {inline(cell, `th${c}`, keep)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, r) => (
                <tr key={r}>
                  {row.map((cell, c) => (
                    <td key={c}>{inline(cell, `td${r}-${c}`, keep)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      )
      continue
    }

    // Blockquote, including GitHub alert syntax
    if (/^\s*>/.test(line)) {
      const body: string[] = []
      while (i < lines.length && /^\s*>/.test(lines[i])) {
        body.push(lines[i].replace(/^\s*>\s?/, ""))
        i++
      }
      let alert: string | undefined
      if (body.length && /^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]/.test(body[0])) {
        const kind = body[0].match(/^\[!(\w+)\]/)![1]
        alert = kind
        body.shift()
      }
      nodes.push(
        <blockquote
          key={`quote-${key++}`}
          className={alert ? "doc-quote doc-quote--alert" : "doc-quote"}
        >
          {alert ? <p className="micro mb-2">{ALERT_NAMES[alert]}</p> : null}
          <MarkdownText lines={body} keyBase={`q${key}`} keep={keep} />
        </blockquote>,
      )
      continue
    }

    // Lists
    const listStart = line.match(/^(\s*)([-*+]|\d+[.)])\s+/)
    if (listStart) {
      const ordered = /\d/.test(listStart[2])
      const items: { text: string; depth: number; check?: string }[] = []
      const baseIndent = listStart[1].length
      while (i < lines.length) {
        const current = lines[i]
        const m = current.match(/^(\s*)([-*+]|\d+[.)])\s+(.*)$/)
        if (m) {
          let text = m[3]
          let check: string | undefined
          const task = text.match(/^\[( |x|X)\]\s+(.*)$/)
          if (task) {
            check = task[1].toLowerCase() === "x" ? "done" : "open"
            text = task[2]
          }
          items.push({ text, depth: m[1].length > baseIndent + 1 ? 1 : 0, check })
          i++
        } else if (current.trim() && /^\s{2,}/.test(current) && items.length) {
          items[items.length - 1].text += " " + current.trim()
          i++
        } else {
          break
        }
      }
      const List = ordered ? "ol" : "ul"
      nodes.push(
        <List
          key={`list-${key++}`}
          className={ordered ? "doc-ol" : "doc-ul"}
          {...(ordered ? {} : {})}
        >
          {items.map((item, idx) => (
            <li
              key={idx}
              className={item.depth ? "ml-5" : undefined}
              {...(item.check ? { "data-task": item.check } : {})}
            >
              {item.check ? (
                <span
                  className="mr-2 inline-block w-3.5 shrink-0 align-[-0.0625em]"
                  aria-hidden="true"
                >
                  {item.check === "done" ? (
                    <svg viewBox="0 0 14 14" className="h-3.5 w-3.5" fill="none">
                      <rect x="0.5" y="0.5" width="13" height="13" rx="2.5" stroke="currentColor" />
                      <path
                        d="M3.5 7.2 6 9.6l4.5-5"
                        stroke="currentColor"
                        strokeWidth="1.6"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  ) : (
                    <svg viewBox="0 0 14 14" className="h-3.5 w-3.5" fill="none">
                      <rect x="0.5" y="0.5" width="13" height="13" rx="2.5" stroke="currentColor" />
                    </svg>
                  )}
                </span>
              ) : null}
              {item.check ? (
                <span className="sr-only">{item.check === "done" ? "Done: " : "To check: "}</span>
              ) : null}
              {inline(item.text, `li${idx}`, keep)}
            </li>
          ))}
        </List>,
      )
      continue
    }

    // Paragraph: gather until a blank line or a block that starts a new element.
    const para: string[] = []
    while (
      i < lines.length &&
      lines[i].trim() &&
      !/^(#{1,6}\s|\s*```|\s*>|\s*\||\s*([-*_])\1{2,}\s*$)/.test(lines[i]) &&
      !/^(\s*)([-*+]|\d+[.)])\s+/.test(lines[i])
    ) {
      para.push(lines[i])
      i++
    }
    const text = para.join(" ")
    // A remote image in a copied document would make the build depend on
    // someone else's network. Render a plain link instead.
    if (/^!\[[^\]]*\]\(https?:\/\/[^)]+\)$/.test(text)) {
      const remote = text.match(/^!\[([^\]]*)\]\(([^)]+)\)$/)!
      nodes.push(
        <p key={`img-remote-${key++}`} className="doc-p">
          <a href={remote[2]} className="link-inline" rel="noreferrer" target="_blank">
            {remote[1] || remote[2]}
          </a>
        </p>,
      )
      continue
    }
    const image = text.match(/^!\[([^\]]*)\]\(([^)]+)\)$/)
    if (image) {
      const alt = image[1]
      const src = image[2].replace(/^screenshots\//, "/images/docs/").replace(/^\.\//, "/docs/")
      nodes.push(
        <figure key={`img-${key++}`} className="my-8">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={src.startsWith("/") ? src : `/${src}`}
            alt={alt}
            loading="lazy"
            className="w-full rounded-lg border border-line bg-panel"
          />
          {alt ? (
            <figcaption className="mt-2 font-mono text-[0.6875rem] text-muted">{alt}</figcaption>
          ) : null}
        </figure>,
      )
      continue
    }
    nodes.push(
      <p key={`p-${key++}`} className="doc-p">
        {inline(text.replace(/\s+$/, ""), `p${key}`, keep)}
      </p>,
    )
  }

  return { nodes: nodes.map(withKey), headings }
}

/** Paragraph-level rendering for blockquote bodies. */
function MarkdownText({
  lines,
  keyBase,
  keep = false,
}: {
  lines: string[]
  keyBase: string
  keep?: boolean
}) {
  return (
    <>
      {lines.map((line, idx) =>
        line.trim() ? (
          <p key={idx} className={idx ? "doc-p mt-3" : "doc-p"}>
            {inline(line, `${keyBase}-${idx}`, keep)}
          </p>
        ) : null,
      )}
    </>
  )
}

/** Headings only, for the contents rail. Cheap enough to call twice. */
export function outline(markdown: string): Heading[] {
  return renderMarkdown(markdown).headings.filter((h) => h.level >= 2 && h.level <= 3)
}
