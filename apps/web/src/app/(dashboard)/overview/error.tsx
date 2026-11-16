"use client";

import { useEffect } from "react";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-col items-start gap-3 p-6">
      <h2 className="text-lg font-semibold">Something went wrong on this page</h2>
      <p className="text-sm text-neutral-600">Your data is unchanged. You can try again.</p>
      <button
        type="button"
        onClick={() => reset()}
        className="rounded bg-neutral-900 px-3 py-2 text-sm text-white"
      >
        Try again
      </button>
    </div>
  );
}
