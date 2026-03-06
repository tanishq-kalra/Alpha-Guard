"use client";

import React, { useState, useRef, useEffect, useCallback, useMemo } from "react";
import tickers from "@/lib/tickers.json";

interface TickerSearchProps {
    onSearch?: (ticker: string) => void | Promise<void>;
    isLoading?: boolean;
}

interface TickerEntry {
    symbol: string;
    name: string;
    sector: string;
}

export default function TickerSearch({ onSearch, isLoading: externalLoading }: TickerSearchProps) {
    const [query, setQuery] = useState("");
    const [isFocused, setIsFocused] = useState(false);
    const [internalLoading, setInternalLoading] = useState(false);
    const [showDropdown, setShowDropdown] = useState(false);
    const [selectedIndex, setSelectedIndex] = useState(-1);
    const inputRef = useRef<HTMLInputElement>(null);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    const isLoading = externalLoading ?? internalLoading;

    // Filter tickers based on query — match symbol OR company name
    const suggestions = useMemo((): TickerEntry[] => {
        if (!query.trim()) return [];
        const q = query.toLowerCase();
        return (tickers as TickerEntry[])
            .filter(
                (t) =>
                    t.symbol.toLowerCase().includes(q) ||
                    t.name.toLowerCase().includes(q)
            )
            .slice(0, 8); // Show top 8 results
    }, [query]);

    // Show dropdown when there are suggestions and input is focused
    useEffect(() => {
        setShowDropdown(isFocused && suggestions.length > 0 && !isLoading);
        setSelectedIndex(-1);
    }, [suggestions, isFocused, isLoading]);

    // Close dropdown on outside click
    useEffect(() => {
        const handleClick = (e: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
                setShowDropdown(false);
            }
        };
        document.addEventListener("mousedown", handleClick);
        return () => document.removeEventListener("mousedown", handleClick);
    }, []);

    // Ctrl+K shortcut to focus the search
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.ctrlKey || e.metaKey) && e.key === "k") {
                e.preventDefault();
                inputRef.current?.focus();
            }
        };
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, []);

    const submitTicker = useCallback(
        async (ticker: string) => {
            if (!ticker || isLoading) return;
            setShowDropdown(false);
            setInternalLoading(true);
            try {
                await onSearch?.(ticker);
            } finally {
                setInternalLoading(false);
            }
        },
        [onSearch, isLoading]
    );

    const handleSelect = useCallback(
        (entry: TickerEntry) => {
            setQuery(entry.symbol);
            setShowDropdown(false);
            inputRef.current?.blur();
            submitTicker(entry.symbol);
        },
        [submitTicker]
    );

    const handleSubmit = useCallback(
        async (e: React.FormEvent) => {
            e.preventDefault();
            const ticker = query.trim().toUpperCase();
            if (!ticker) return;

            // If a dropdown item is highlighted, use it
            if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
                handleSelect(suggestions[selectedIndex]);
                return;
            }

            submitTicker(ticker);
        },
        [query, selectedIndex, suggestions, handleSelect, submitTicker]
    );

    const handleKeyDown = useCallback(
        (e: React.KeyboardEvent) => {
            if (!showDropdown) return;

            switch (e.key) {
                case "ArrowDown":
                    e.preventDefault();
                    setSelectedIndex((prev) => Math.min(prev + 1, suggestions.length - 1));
                    break;
                case "ArrowUp":
                    e.preventDefault();
                    setSelectedIndex((prev) => Math.max(prev - 1, -1));
                    break;
                case "Escape":
                    setShowDropdown(false);
                    break;
            }
        },
        [showDropdown, suggestions.length]
    );

    // Scroll selected item into view
    useEffect(() => {
        if (selectedIndex >= 0 && dropdownRef.current) {
            const items = dropdownRef.current.querySelectorAll("[data-ticker-item]");
            items[selectedIndex]?.scrollIntoView({ block: "nearest" });
        }
    }, [selectedIndex]);

    // Sector color mapping
    const sectorColor = (sector: string) => {
        const map: Record<string, string> = {
            Technology: "text-ag-cyan",
            "Financial Services": "text-ag-green",
            Healthcare: "text-ag-amber",
            Energy: "text-ag-red",
            Industrials: "text-ag-text2",
            "Consumer Cyclical": "text-ag-amber",
            "Consumer Defensive": "text-ag-green",
            "Communication Services": "text-ag-cyan",
            Utilities: "text-ag-muted",
            "Basic Materials": "text-ag-amber",
        };
        return map[sector] || "text-ag-muted";
    };

    return (
        <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
            <div ref={containerRef} className="relative">
                <div
                    className={`
            relative flex items-center gap-3 px-4 py-3
            rounded-xl border transition-all duration-300
            ${isFocused
                            ? "border-ag-green/40 bg-ag-card shadow-[0_0_30px_rgba(0,230,122,0.06)]"
                            : "border-ag-border bg-ag-bg2 hover:border-ag-border-hover"
                        }
            ${showDropdown ? "rounded-b-none border-b-ag-border/50" : ""}
          `}
                >
                    {/* Search Icon */}
                    <svg
                        className={`w-5 h-5 flex-shrink-0 transition-colors duration-200 ${isFocused ? "text-ag-green" : "text-ag-muted"}`}
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth={2}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    >
                        <circle cx="11" cy="11" r="8" />
                        <line x1="21" y1="21" x2="16.65" y2="16.65" />
                    </svg>

                    {/* Input */}
                    <input
                        id="ticker-search"
                        ref={inputRef}
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value.toUpperCase())}
                        onFocus={() => setIsFocused(true)}
                        onBlur={() => {
                            // Delay blur to allow dropdown click
                            setTimeout(() => setIsFocused(false), 150);
                        }}
                        onKeyDown={handleKeyDown}
                        placeholder="Search ticker or company... e.g. AAPL, Apple"
                        className="
              flex-1 bg-transparent outline-none text-ag-text text-sm
              font-mono placeholder:text-ag-muted tracking-wide
            "
                        autoComplete="off"
                        spellCheck={false}
                        disabled={isLoading}
                        role="combobox"
                        aria-expanded={showDropdown}
                        aria-autocomplete="list"
                        aria-controls="ticker-listbox"
                    />

                    {/* Loading Spinner */}
                    {isLoading && (
                        <div className="w-4 h-4 border-2 border-ag-green/30 border-t-ag-green rounded-full animate-spin" />
                    )}

                    {/* Keyboard Shortcut Badge */}
                    {!isFocused && !query && (
                        <div className="hidden sm:flex items-center gap-0.5">
                            <kbd className="px-1.5 py-0.5 rounded bg-ag-surface text-[10px] font-mono text-ag-muted border border-ag-border">
                                Ctrl
                            </kbd>
                            <kbd className="px-1.5 py-0.5 rounded bg-ag-surface text-[10px] font-mono text-ag-muted border border-ag-border">
                                K
                            </kbd>
                        </div>
                    )}

                    {/* Submit Button */}
                    {query && (
                        <button
                            type="submit"
                            disabled={isLoading}
                            className="
                px-4 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider
                bg-ag-green/10 text-ag-green border border-ag-green/20
                hover:bg-ag-green/20 hover:border-ag-green/40
                transition-all duration-200
                disabled:opacity-40 disabled:cursor-not-allowed
              "
                        >
                            {isLoading ? "Analyzing..." : "Analyze"}
                        </button>
                    )}
                </div>

                {/* ── Dropdown ── */}
                {showDropdown && (
                    <div
                        ref={dropdownRef}
                        id="ticker-listbox"
                        role="listbox"
                        className="
              absolute z-50 w-full
              rounded-b-xl border border-t-0 border-ag-green/40
              bg-ag-card/95 backdrop-blur-xl
              shadow-[0_12px_40px_rgba(0,0,0,0.5)]
              overflow-hidden
            "
                    >
                        {suggestions.map((entry, i) => (
                            <div
                                key={entry.symbol}
                                data-ticker-item
                                role="option"
                                aria-selected={i === selectedIndex}
                                onMouseDown={() => handleSelect(entry)}
                                onMouseEnter={() => setSelectedIndex(i)}
                                className={`
                  flex items-center justify-between px-4 py-2.5 cursor-pointer
                  transition-colors duration-100
                  ${i === selectedIndex
                                        ? "bg-ag-green/10 border-l-2 border-l-ag-green"
                                        : "border-l-2 border-l-transparent hover:bg-ag-surface/60"
                                    }
                  ${i < suggestions.length - 1 ? "border-b border-b-ag-border/40" : ""}
                `}
                            >
                                <div className="flex items-center gap-3 min-w-0">
                                    <span className={`text-sm font-mono font-bold ${i === selectedIndex ? "text-ag-green" : "text-ag-text"} w-[60px] flex-shrink-0`}>
                                        {entry.symbol}
                                    </span>
                                    <span className="text-xs text-ag-text2 truncate">
                                        {entry.name}
                                    </span>
                                </div>
                                <span className={`text-[9px] font-mono uppercase tracking-wider flex-shrink-0 ml-2 ${sectorColor(entry.sector)}`}>
                                    {entry.sector}
                                </span>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Helper text */}
            <p className="text-center text-[11px] text-ag-muted mt-2 font-mono">
                Real-time global market access enabled · {(tickers as TickerEntry[]).length} companies indexed
            </p>
        </form>
    );
}
