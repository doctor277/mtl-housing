// A titled section of the text pages (How it works, Sources and limitations): one h2, then
// paragraphs and lists with even spacing.

export default function Section({
  heading,
  id,
  children,
}: {
  heading: string;
  id?: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="mt-10 scroll-mt-4">
      <h2 className="text-lg font-semibold">{heading}</h2>
      <div className="mt-3 flex flex-col gap-3">{children}</div>
    </section>
  );
}
