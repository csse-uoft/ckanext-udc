import { useAuth } from './authContext';

export function useAuthErrorHandler() {
  const { showError } = useAuth();

  const handleError = (error: any) => {
    if (error?.error?.__type === 'Authorization Error') {
      showError(error.error.message);
    }
  };

  return { handleError };
}
