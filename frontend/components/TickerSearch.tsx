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
    exchange?: string;
}

export default function TickerSearch({ onSearch, isLoading: externalLoading }: TickerSearchProps) {
    const [query, setQuery] = useState("");
    const [isFocused, setIsFocused] = useState(false);
    const [internalLoading, setInternalLoading] = useState(false);
    const [showDropdown, setShowDropdown] = useState(false);
    const [selectedIndex, setSelectedIndex] = useState(-1);
    const [globalMode, setGlobalMode] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    const isLoading = externalLoading ?? internalLoading;
    const allTickers = tickers as TickerEntry[];

    const suggestions = useMemo((): TickerEntry[] => {
        if (!query.trim()) return [];
        const q = query.toLowerCase();
        return allTickers
            .filter((t) => {
                if (!globalMode && t.exchange && !["NYSE", "NASDAQ", "S&P500"].includes(t.exchange)) return false;
                return t.symbol.toLowerCase().includes(q) || t.name.toLowerCase().includes(q);
            })
            .slice(0, 8);
    }, [query, globalMode, allTickers]);

    useEffect(() => {
        setShowDropdown(isFocused && suggestions.length > 0 && !isLoading);
        setSelectedIndex(-1);
    }, [suggestions, isFocused, isLoading]);

    useEffect(() => {
        const handleClick = (e: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
                setShowDropdown(false);
            }
        };
        document.addEventListener("mousedown", handleClick);
        return () => document.removeEventListener("mousedown", handleClick);
    }, []);

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
            try { await onSearch?.(ticker); }
            finally { setInternalLoading(false); }
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

    useEffect(() => {
        if (selectedIndex >= 0 && dropdownRef.current) {
            const items = dropdownRef.current.querySelectorAll("[data-ticker-item]");
            items[selectedIndex]?.scrollIntoView({ block: "nearest" });
        }
    }, [selectedIndex]);

    const usCount = allTickers.filter(t => !t.exchange || ["NYSE", "NASDAQ", "S&P500"].includes(t.exchange)).length;
    const globalCount = allTickers.length;

    return (
        <form onSubmit={handleSubmit} style={{ width: "100%", maxWidth: 640, margin: "0 auto" }}>
            <div ref={containerRef} style={{ position: "relative" }}>
                {/* Main search row */}
                <div
                    style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                        padding: "10px 14px",
                        background: "var(--paper-2)",
                        border: `1px solid ${isFocused ? "var(--green)" : "var(--rule-strong)"}`,
                        borderRadius: showDropdown ? "4px 4px 0 0" : 4,
                        transition: "border-color 0.15s ease",
                        boxShadow: isFocused ? "0 0 0 3px var(--green-tint)" : "none",
                    }}
                >
                    {/* Search icon */}
                    <svg
                        style={{
                            width: 15,
                            height: 15,
                            flexShrink: 0,
                            color: isFocused ? "var(--green)" : "var(--ink-faint)",
                            transition: "color 0.15s ease",
                        }}
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
                        onBlur={() => { setTimeout(() => setIsFocused(false), 150); }}
                        onKeyDown={handleKeyDown}
                        placeholder={
                            globalMode
                                ? "Search global markets... e.g. RELIANCE, TCS.NS, TSLA"
                                : "Search ticker or company... e.g. AAPL, Apple"
                        }
                        style={{
                            flex: 1,
                            background: "transparent",
                            border: "none",
                            outline: "none",
                            fontFamily: "var(--font-ibm-plex-mono, monospace)",
                            fontSize: 13,
                            color: "var(--ink)",
                        }}
                        autoComplete="off"
                        spellCheck={false}
                        disabled={isLoading}
                        role="combobox"
                        aria-expanded={showDropdown}
                        aria-autocomplete="list"
                        aria-controls="ticker-listbox"
                    />

                    {/* Global toggle — outlined style */}
                    <button
                        type="button"
                        id="ticker-global-toggle"
                        onClick={() => setGlobalMode(!globalMode)}
                        style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 5,
                            padding: "4px 10px",
                            borderRadius: 4,
                            border: `1px solid ${globalMode ? "var(--blue)" : "var(--rule-strong)"}`,
                            background: globalMode ? "var(--blue-tint)" : "var(--paper-2)",
                            color: globalMode ? "var(--blue)" : "var(--ink-2)",
                            fontFamily: "var(--font-ibm-plex-mono, monospace)",
                            fontSize: 9,
                            fontWeight: 600,
                            letterSpacing: "0.1em",
                            textTransform: "uppercase",
                            cursor: "pointer",
                            transition: "all 0.15s ease",
                        }}
                    >
                        <svg style={{ width: 10, height: 10 }} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                            <circle cx="12" cy="12" r="10" />
                            <path d="M2 12h20" />
                            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                        </svg>
                        Global
                    </button>

                    {/* Loading spinner */}
                    {isLoading && (
                        <div
                            style={{
                                width: 14,
                                height: 14,
                                border: "2px solid var(--rule)",
                                borderTopColor: "var(--green)",
                                borderRadius: "50%",
                                animation: "spin 0.8s linear infinite",
                                flexShrink: 0,
                            }}
                        />
                    )}

                    {/* Keyboard shortcut hint */}
                    {!isFocused && !query && (
                        <div className="hidden sm:flex" style={{ alignItems: "center", gap: 2 }}>
                            <kbd
                                style={{
                                    padding: "2px 6px",
                                    borderRadius: 3,
                                    background: "var(--paper)",
                                    border: "1px solid var(--rule-strong)",
                                    fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                    fontSize: 9,
                                    color: "var(--ink-faint)",
                                }}
                            >
                                Ctrl
                            </kbd>
                            <kbd
                                style={{
                                    padding: "2px 6px",
                                    borderRadius: 3,
                                    background: "var(--paper)",
                                    border: "1px solid var(--rule-strong)",
                                    fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                    fontSize: 9,
                                    color: "var(--ink-faint)",
                                }}
                            >
                                K
                            </kbd>
                        </div>
                    )}

                    {/* Submit / Analyze button — solid primary */}
                    {query && (
                        <button
                            id="ticker-analyze-btn"
                            type="submit"
                            disabled={isLoading}
                            style={{
                                padding: "6px 16px",
                                borderRadius: 4,
                                background: "var(--green)",
                                color: "#ffffff",
                                border: "1px solid var(--green)",
                                fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                fontSize: 10,
                                fontWeight: 600,
                                letterSpacing: "0.1em",
                                textTransform: "uppercase",
                                cursor: isLoading ? "not-allowed" : "pointer",
                                opacity: isLoading ? 0.5 : 1,
                                transition: "background 0.15s ease",
                                flexShrink: 0,
                            }}
                        >
                            {isLoading ? "Analyzing..." : "Analyze"}
                        </button>
                    )}
                </div>

                {/* Dropdown */}
                {showDropdown && (
                    <div
                        ref={dropdownRef}
                        id="ticker-listbox"
                        role="listbox"
                        style={{
                            position: "absolute",
                            zIndex: 50,
                            width: "100%",
                            background: "var(--paper-2)",
                            border: "1px solid var(--rule-strong)",
                            borderTop: "none",
                            borderRadius: "0 0 4px 4px",
                            boxShadow: "var(--shadow-md)",
                            overflow: "hidden",
                        }}
                    >
                        {suggestions.map((entry, i) => (
                            <div
                                key={entry.symbol}
                                data-ticker-item
                                role="option"
                                aria-selected={i === selectedIndex}
                                onMouseDown={() => handleSelect(entry)}
                                onMouseEnter={() => setSelectedIndex(i)}
                                style={{
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "space-between",
                                    padding: "9px 14px",
                                    cursor: "pointer",
                                    background: i === selectedIndex ? "var(--green-tint)" : "transparent",
                                    borderLeft: `2px solid ${i === selectedIndex ? "var(--green)" : "transparent"}`,
                                    borderBottom: i < suggestions.length - 1 ? "1px solid var(--rule)" : "none",
                                    transition: "background 0.1s ease",
                                }}
                            >
                                <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0 }}>
                                    <span
                                        style={{
                                            fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                            fontSize: 12,
                                            fontWeight: 600,
                                            color: i === selectedIndex ? "var(--green)" : "var(--ink)",
                                            width: 80,
                                            flexShrink: 0,
                                        }}
                                    >
                                        {entry.symbol}
                                    </span>
                                    <span
                                        style={{
                                            fontFamily: "var(--font-ibm-plex-sans, system-ui, sans-serif)",
                                            fontSize: 12,
                                            color: "var(--ink-2)",
                                            overflow: "hidden",
                                            textOverflow: "ellipsis",
                                            whiteSpace: "nowrap",
                                        }}
                                    >
                                        {entry.name}
                                    </span>
                                </div>
                                <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0, marginLeft: 8 }}>
                                    {entry.exchange && (
                                        <span
                                            style={{
                                                padding: "1px 5px",
                                                borderRadius: 3,
                                                background: "var(--paper)",
                                                border: "1px solid var(--rule)",
                                                fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                                fontSize: 8,
                                                letterSpacing: "0.08em",
                                                textTransform: "uppercase",
                                                color: "var(--ink-faint)",
                                            }}
                                        >
                                            {entry.exchange}
                                        </span>
                                    )}
                                    <span
                                        style={{
                                            fontFamily: "var(--font-ibm-plex-mono, monospace)",
                                            fontSize: 8,
                                            letterSpacing: "0.1em",
                                            textTransform: "uppercase",
                                            color: "var(--ink-faint)",
                                        }}
                                    >
                                        {entry.sector}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Helper text */}
            <p
                style={{
                    textAlign: "center",
                    fontFamily: "var(--font-ibm-plex-mono, monospace)",
                    fontSize: 9,
                    color: "var(--ink-faint)",
                    marginTop: 8,
                }}
            >
                {globalMode
                    ? `Global search · ${globalCount} companies across BSE/NSE, NYSE, LSE & more`
                    : `US market · ${usCount} companies indexed · Enable Global for international`
                }
            </p>
        </form>
    );
}
