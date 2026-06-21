import { useEffect, useState } from "react";
import { api } from "./api.js";

// Module-level cache so the constitution floors are fetched once per session.
let cache = null;
let inflight = null;

export function loadPolicies() {
  if (cache) return Promise.resolve(cache);
  if (!inflight) {
    inflight = api
      .getPolicies()
      .then((p) => {
        cache = p;
        return p;
      })
      .finally(() => {
        inflight = null;
      });
  }
  return inflight;
}

// Returns { policies, floors }. floors is the immutable constitution_floors dict.
export function usePolicies() {
  const [policies, setPolicies] = useState(cache);
  useEffect(() => {
    let alive = true;
    loadPolicies().then((p) => alive && setPolicies(p)).catch(() => {});
    return () => {
      alive = false;
    };
  }, []);
  return { policies, floors: policies?.constitution_floors || null };
}
