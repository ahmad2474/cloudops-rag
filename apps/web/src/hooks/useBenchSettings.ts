"use client";

import { useCallback, useState } from "react";
import type { ContextMode, Strategy } from "@/lib/types";

export interface BenchSettings {
  strategy: Strategy | null; // null = server default
  rerank: boolean | null;
  contextMode: ContextMode | null;
  includeDeprecated: boolean;
}

const KEY = "cloudops.bench";
const DEFAULT: BenchSettings = { strategy: null, rerank: null, contextMode: null, includeDeprecated: false };

export function useBenchSettings(): [BenchSettings, (patch: Partial<BenchSettings>) => void] {
  const [s, setS] = useState<BenchSettings>(() => {
    if (typeof window === "undefined") return DEFAULT;
    try {
      const raw = localStorage.getItem(KEY);
      return raw ? { ...DEFAULT, ...JSON.parse(raw) } : DEFAULT;
    } catch {
      return DEFAULT;
    }
  });
  const update = useCallback((patch: Partial<BenchSettings>) => {
    setS((prev) => {
      const next = { ...prev, ...patch };
      try {
        localStorage.setItem(KEY, JSON.stringify(next));
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);
  return [s, update];
}
