import { Reveal } from "@/components/motion/Reveal";

export function LegalPage({
  title,
  updated,
  sections,
}: {
  title: string;
  updated: string;
  sections: { heading: string; body: string }[];
}) {
  return (
    <main id="main" className="mx-auto w-full max-w-3xl px-md py-xl">
      <Reveal>
        <h1 className="font-display text-hero text-ink">{title}</h1>
        <p className="mt-sm text-sm text-muted">{updated}</p>
      </Reveal>
      <div className="mt-xl flex flex-col gap-xl">
        {sections.map((section) => (
          <Reveal key={section.heading}>
            <h2 className="font-display text-display text-ink">{section.heading}</h2>
            <p className="mt-sm whitespace-pre-line text-muted">{section.body}</p>
          </Reveal>
        ))}
      </div>
    </main>
  );
}
