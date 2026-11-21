/**
 * Section header on the grid's margin: the index sits in the first two columns,
 * the heading starts on column three. Repeated structure, so it reads as a spine
 * rather than a stack of labels.
 */
export function SectionHead({
  index,
  label,
  title,
  intro,
}: {
  index?: string
  label: string
  title: React.ReactNode
  intro?: React.ReactNode
}) {
  return (
    <div className="grid gap-3 border-t border-line pt-6 md:grid-cols-12 md:gap-8">
      <p className="micro md:col-span-2 md:pt-2">
        {index ? `${index} · ` : ""}
        {label}
      </p>
      <div className="md:col-span-10">
        <h2 className="max-w-3xl text-[clamp(1.75rem,4vw,2.75rem)] leading-[1.02]">{title}</h2>
        {intro ? (
          <p className="mt-4 max-w-xl text-[0.9375rem] leading-relaxed text-muted">{intro}</p>
        ) : null}
      </div>
    </div>
  )
}
