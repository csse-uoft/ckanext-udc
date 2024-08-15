import { useCallback } from 'react';
import { useAuthErrorHandler } from './useAuthErrorHandler';
import * as api from './api'; // Import all functions from api.ts

export function useApi() {
  const { handleError } = useAuthErrorHandler();

  const executeApiCall = useCallback(
    async <T,>(apiCall: () => Promise<T>): Promise<T> => {
      try {
        return await apiCall();
      } catch (error) {
        handleError(error);
        throw error; // Optionally rethrow the error if needed
      }
    },
    [handleError]
  );

  return {
    executeApiCall,
    api,
  };
}
