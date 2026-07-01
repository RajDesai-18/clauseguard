"use client";

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

interface RailContextValue {
  collapsed: boolean;
  toggle: () => void;
  setCollapsed: (value: boolean) => void;
}

const RailContext = createContext<RailContextValue | null>(null);

/**
 * Holds the rail's collapsed state so both the rail's own toggle button
 * and global keyboard shortcuts drive the same value. Seeded from the
 * server-read `rail_collapsed` cookie via `defaultCollapsed`, so first
 * paint matches with no width flicker. Persistence stays here: every
 * change writes the cookie (1 year, lax, site-wide), which the server
 * layout reads on the next request.
 */
export function RailProvider({
  defaultCollapsed = false,
  children,
}: {
  defaultCollapsed?: boolean;
  children: ReactNode;
}) {
  const [collapsed, setCollapsedState] = useState(defaultCollapsed);

  const persist = useCallback((value: boolean) => {
    document.cookie = `rail_collapsed=${value ? "1" : "0"}; path=/; max-age=31536000; samesite=lax`;
  }, []);

  const setCollapsed = useCallback(
    (value: boolean) => {
      setCollapsedState(value);
      persist(value);
    },
    [persist]
  );

  const toggle = useCallback(() => {
    setCollapsedState((prev) => {
      const next = !prev;
      persist(next);
      return next;
    });
  }, [persist]);

  return (
    <RailContext.Provider value={{ collapsed, toggle, setCollapsed }}>
      {children}
    </RailContext.Provider>
  );
}

export function useRail(): RailContextValue {
  const ctx = useContext(RailContext);
  if (!ctx) {
    throw new Error("useRail must be used within a RailProvider.");
  }
  return ctx;
}
