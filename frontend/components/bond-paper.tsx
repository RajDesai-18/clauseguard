"use client";

import { useEffect, useState } from "react";

/**
 * BondPaper renders the layered fibrous texture of legal bond paper.
 * Two SVG filter layers (noise + stretched turbulence) blended against
 * the page background to simulate paper fiber speckle and horizontal
 * laid lines.
 *
 * Runs client-side because the filter matrix depends on the current
 * theme, and SVG filter primitives don't respond to CSS class toggling
 * reliably across browsers. We read the theme from the document class
 * and update the matrix in JS.
 */
export function BondPaper({ className = "" }: { className?: string }) {
    const [isDark, setIsDark] = useState(false);

    useEffect(() => {
        const root = document.documentElement;
        const update = () => setIsDark(root.classList.contains("dark"));
        update();
        const observer = new MutationObserver(update);
        observer.observe(root, { attributes: true, attributeFilter: ["class"] });
        return () => observer.disconnect();
    }, []);

    const grainMatrix = isDark
        ? "0 0 0 0 0.94 0 0 0 0 0.92 0 0 0 0 0.87 0 0 0 0.18 0"
        : "0 0 0 0 0.08 0 0 0 0 0.08 0 0 0 0 0.07 0 0 0 0.32 0";

    const weaveMatrix = isDark
        ? "0 0 0 0 0.94 0 0 0 0 0.92 0 0 0 0 0.87 0 0 0 0.24 0"
        : "0 0 0 0 0.08 0 0 0 0 0.08 0 0 0 0 0.07 0 0 0 0.42 0";

    return (
        <div
            aria-hidden
            className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}
        >
            <svg
                width="100%"
                height="100%"
                preserveAspectRatio="xMidYMid slice"
                className="absolute inset-0 h-full w-full"
                style={{
                    opacity: isDark ? 0.32 : 0.55,
                    mixBlendMode: isDark ? "screen" : "multiply",
                }}
            >
                <defs>
                    <filter id="paper-grain" x="0" y="0" width="100%" height="100%">
                        <feTurbulence
                            type="fractalNoise"
                            baseFrequency="0.85"
                            numOctaves="2"
                            stitchTiles="stitch"
                            seed="2"
                        />
                        <feColorMatrix values={grainMatrix} />
                    </filter>
                </defs>
                <rect width="100%" height="100%" filter="url(#paper-grain)" />
            </svg>

            <svg
                width="100%"
                height="100%"
                preserveAspectRatio="xMidYMid slice"
                className="absolute inset-0 h-full w-full"
                style={{
                    opacity: isDark ? 0.24 : 0.38,
                    mixBlendMode: isDark ? "screen" : "multiply",
                }}
            >
                <defs>
                    <filter id="paper-weave" x="0" y="0" width="100%" height="100%">
                        <feTurbulence
                            type="turbulence"
                            baseFrequency="0.015 0.6"
                            numOctaves="1"
                            seed="5"
                        />
                        <feColorMatrix values={weaveMatrix} />
                    </filter>
                </defs>
                <rect width="100%" height="100%" filter="url(#paper-weave)" />
            </svg>
        </div>
    );
}