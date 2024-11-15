import React, { createContext, useState, useContext, ReactNode } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button } from '@mui/material';
import { useLocation } from 'react-router-dom';

interface AuthContextType {
  showError: (message: string) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode, dismissable?: boolean }> = ({ children, dismissable = true }) => {
  const [open, setOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const location = useLocation()

  const showError = (message: string) => {
    setErrorMessage(message);
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
    window.location.href = `/user/login?came_from=${location.pathname}`; // Redirect to external login page
  };

  return (
    <AuthContext.Provider value={{ showError }}>
      {children}
      <Dialog open={open} onClose={dismissable ? handleClose : undefined}>
        <DialogTitle>Authorization Error</DialogTitle>
        <DialogContent>{errorMessage}</DialogContent>
        <DialogActions>
          {dismissable && <Button onClick={() => setOpen(false)} color="secondary">Dismiss</Button>}
          <Button onClick={handleClose} color="primary">
            Go to Login
          </Button>
        </DialogActions>
      </Dialog>
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
