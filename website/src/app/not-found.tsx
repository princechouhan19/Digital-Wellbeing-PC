import Link from "next/link"

export const metadata = { title: "Nothing on this route" }

export default function NotFound() {
  return (
    <section className="relative overflow-hidden border-b border-line">
      <div aria-hidden="true" className="grid-field absolute inset-0 -z-10" />
      <div className="shell flex min-h-[62svh] flex-col justify-center py-20">
        <p className="micro flex items-center gap-2.5">
          <span className="dot dot--alert" aria-hidden="true" />
          404 · process not found
        </p>
        <h1 className="mt-5 max-w-2xl text-[clamp(2rem,6vw,3.75rem)] leading-[0.98] tracking-[-0.04em]">
          No process by that name.
        </h1>
        <p className="mt-5 max-w-md text-[0.9375rem] leading-relaxed text-muted">
          The tracker looked for this address in the foreground window list and found nothing. It is
          not a page, and it is not going to become one.
        </p>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <Link href="/" className="btn btn--primary">
            <span>Back to the overview</span>
          </Link>
          <a
            href="https://github.com/princechouhan19/Digital-Wellbeing-PC/issues"
            rel="noreferrer"
            className="btn btn--ghost"
          >
            <span>Report the broken link</span>
          </a>
        </div>
      </div>
    </section>
  )
}
