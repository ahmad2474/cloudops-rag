"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { IncidentDetail } from "@/components/incidents/IncidentDetail";
import { useShell } from "@/components/layout/AppShell";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { api, ApiError } from "@/lib/api";
import type { DocumentDetail, DocumentSummary } from "@/lib/types";

export default function IncidentPage() {
  const { id } = useParams<{ id: string }>();
  const { setQueryField } = useShell();
  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [all, setAll] = useState<DocumentSummary[]>([]);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { setQueryField(<Link href="/incidents" className="font-mono text-[12px] text-text-secondary hover:text-text-primary">← all incidents</Link>); }, [setQueryField]);
  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => { if (!cancelled) { setDoc(null); setErr(null); } });
    api.document(id).then((d) => { if (!cancelled) setDoc(d); }).catch((e) => { if (!cancelled) setErr(e instanceof ApiError && e.status === 404 ? "Not found — or not visible to your role." : String(e)); });
    api.documents({ document_type: "incident", limit: 500 }).then((d) => { if (!cancelled) setAll(d); }).catch(() => { if (!cancelled) setAll([]); });
    return () => { cancelled = true; };
  }, [id]);
  if (err) return <div className="p-6"><EmptyState kicker="incident" title={err} /></div>;
  if (!doc) return <div className="grid gap-px p-3">{Array.from({ length: 10 }, (_, i) => <Skeleton key={i} className="h-6" />)}</div>;
  return <IncidentDetail doc={doc} related={all} />;
}
