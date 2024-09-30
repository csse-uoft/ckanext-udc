import { Box, Button } from "@mui/material";
import { OpenInNew as OpenInNewIcon } from '@mui/icons-material';


interface LinkProps {
  label: string;
  url: string;
}

export const Link: React.FC<LinkProps> = ({ label, url }) => {
  return (
    <Box display="flex" alignItems="center" sx={{ pb: 1 }}>
      <Button variant="outlined" startIcon={<OpenInNewIcon />} color="secondary"
        sx={{ textTransform: 'none' }}
        onClick={() => window.open(url, '_blank')}
      >
        {label}
      </Button>
    </Box>
  );
};