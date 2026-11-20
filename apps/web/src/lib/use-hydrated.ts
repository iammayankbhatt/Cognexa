import { useSyncExternalStore } from "react";

const subscribe = () => () => undefined;

/**
 * False during server rendering and while React hydrates server HTML; true afterwards (and on
 * client-side mounts). Data that can already be in a client cache when a later boundary
 * hydrates (for example /me, fetched early by the app shell) must not be shown before this is
 * true, or the first client render will not match the server HTML (BUG-026).
 */
export function useHydrated(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
}
