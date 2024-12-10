import { Dialog as MuiDialog, DialogTitle, DialogContent, DialogContentText, DialogActions, Button } from "@mui/material"


export const Dialog: React.FC<{ open: boolean, onClose: () => void, message: string, title?: string }> = ({ open, onClose, message, title }) => {
  return (
    <MuiDialog open={open} onClose={onClose}>
      <DialogTitle>{title ? title : 'Error'}</DialogTitle>
      <DialogContent>
        <DialogContentText sx={{whiteSpace: 'pre'}}>{message}</DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </MuiDialog>
  )
}
