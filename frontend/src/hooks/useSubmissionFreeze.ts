import { useCallback, useEffect, useState } from 'react';
import { platformApi } from '../services/api/platform';

/**
 * Reads the platform submission-freeze state. While frozen, non-admin users
 * cannot upload, delete, or re-point agents — so callers can show a banner and
 * disable the relevant controls.
 */
export function useSubmissionFreeze() {
  const [frozen, setFrozen] = useState(false);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const state = await platformApi.getSubmissionFreeze();
      setFrozen(state.enabled);
    } catch (err) {
      console.error('Failed to load submission-freeze state:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { frozen, loading, refresh };
}
