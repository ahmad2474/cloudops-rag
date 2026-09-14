"use client";

import { Bench } from "@/components/answer/Bench";
import { useShell } from "@/components/layout/AppShell";

export default function BenchPage() {
  const { settings, setQueryField } = useShell();
  return <Bench settings={settings} registerQueryField={setQueryField} />;
}
