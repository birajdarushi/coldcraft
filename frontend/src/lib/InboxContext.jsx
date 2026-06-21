/**
 * InboxContext — Caches Gmail threads across route navigations.
 *
 * Instead of re-fetching on every mount of Inbox.jsx, this context holds
 * thread state at the app level. Threads are considered fresh for 60s;
 * navigating away and back within that window skips the API call entirely.
 *
 * Call refresh(force=true) to bypass the stale check (e.g. after sending a reply).
 */
import { createContext, useCallback, useContext, useRef, useState } from "react";
import { api } from "./api.js";

const STALE_MS = 60_000; // 60 seconds

const InboxContext = createContext(null);

export function InboxProvider({ children }) {
  const [threads, setThreads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [nextPageToken, setNextPageToken] = useState(null);
  const [prevPageTokens, setPrevPageTokens] = useState([]);
  const [currentPageToken, setCurrentPageToken] = useState("");
  const [pageIndex, setPageIndex] = useState(1);

  // Track when we last successfully fetched
  const lastFetchedRef = useRef(null);

  const fetchThreads = useCallback(async (token = "", force = false) => {
    // Skip if data is still fresh and this is the same page
    const isStale =
      !lastFetchedRef.current ||
      Date.now() - lastFetchedRef.current > STALE_MS;

    if (!force && !isStale && token === "" && threads.length > 0) {
      // Data is fresh — skip re-fetch
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await api.listInboxThreads(token);
      if (res && Array.isArray(res.threads)) {
        setThreads(res.threads);
        setNextPageToken(res.next_page_token || null);
      } else {
        setThreads(Array.isArray(res) ? res : []);
        setNextPageToken(null);
      }
      setCurrentPageToken(token);
      lastFetchedRef.current = Date.now();
    } catch (err) {
      setError(err.detail || "Failed to load inbox threads.");
    } finally {
      setLoading(false);
    }
  }, [threads.length]);

  const goNextPage = useCallback(() => {
    if (nextPageToken) {
      setPrevPageTokens((prev) => [...prev, currentPageToken]);
      setPageIndex((p) => p + 1);
      fetchThreads(nextPageToken, true);
    }
  }, [nextPageToken, currentPageToken, fetchThreads]);

  const goPrevPage = useCallback(() => {
    if (prevPageTokens.length > 0) {
      const prevToken = prevPageTokens[prevPageTokens.length - 1];
      setPrevPageTokens((prev) => prev.slice(0, -1));
      setPageIndex((p) => p - 1);
      fetchThreads(prevToken, true);
    }
  }, [prevPageTokens, fetchThreads]);

  /** Remove a thread from local cache (after trash/archive/unsubscribe) */
  const removeThread = useCallback((threadId) => {
    setThreads((prev) => prev.filter((t) => t.id !== threadId));
  }, []);

  /** Force full refresh (e.g. after OAuth callback) */
  const refresh = useCallback(() => {
    lastFetchedRef.current = null;
    setPrevPageTokens([]);
    setPageIndex(1);
    fetchThreads("", true);
  }, [fetchThreads]);

  return (
    <InboxContext.Provider
      value={{
        threads,
        setThreads,
        loading,
        error,
        setError,
        nextPageToken,
        prevPageTokens,
        currentPageToken,
        pageIndex,
        fetchThreads,
        goNextPage,
        goPrevPage,
        removeThread,
        refresh,
      }}
    >
      {children}
    </InboxContext.Provider>
  );
}

export function useInbox() {
  const ctx = useContext(InboxContext);
  if (!ctx) throw new Error("useInbox must be used inside <InboxProvider>");
  return ctx;
}
