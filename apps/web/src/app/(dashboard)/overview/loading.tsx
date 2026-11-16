export default function Loading() {
  return (
    <div role="status" aria-label="Loading" className="space-y-4 p-6">
      <div className="h-8 w-48 animate-pulse rounded bg-neutral-200 motion-reduce:animate-none" />
      <div className="h-24 animate-pulse rounded bg-neutral-200 motion-reduce:animate-none" />
      <div className="h-24 animate-pulse rounded bg-neutral-200 motion-reduce:animate-none" />
      <div className="h-24 animate-pulse rounded bg-neutral-200 motion-reduce:animate-none" />
    </div>
  );
}
