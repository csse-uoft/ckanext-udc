import { useCallback } from 'react';
import { useAuth } from './authContext';

export function useAuthErrorHandler() {
  const { showError } = useAuth();

  const handleError = useCallback((error: any) => {
    if (error?.error?.__type === 'Authorization Error') {
      showError(error.error.message);
    }
  }, [showError]);

  return { handleError };
}
