"use client";
import { useEffect, useRef } from "react";
import type { ApiFailure } from "../lib/api";

/** Error summary that takes focus when it appears, so keyboard and screen-reader users land on it. */
export function FormErrors({ failure, local }: { failure: ApiFailure | null; local?: string[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const messages = [...(local ?? []), ...(failure ? [failure.message] : [])];
  useEffect(() => { if (messages.length) ref.current?.focus(); }, [messages.length, failure]);
  if (!messages.length) return null;
  return (
    <div className="errors" role="alert" tabIndex={-1} ref={ref}>
      <strong>Chưa lưu được:</strong>
      <ul>{messages.map((m) => <li key={m}>{m}</li>)}</ul>
      {failure?.fields.length ? <p className="caption">Trường cần kiểm tra: {failure.fields.join(", ")}</p> : null}
    </div>
  );
}
