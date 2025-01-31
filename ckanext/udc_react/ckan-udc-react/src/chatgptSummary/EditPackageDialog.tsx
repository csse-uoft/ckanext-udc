import React, { useState, useEffect, useRef } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, TextField, Button, Box, Table, TableBody, TableCell, TableContainer, TableRow, Paper, CircularProgress, Alert, IconButton, Collapse, Typography } from '@mui/material';
import { useApi } from '../api/useApi';
import { Package } from './PackageSearchTable';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';

interface EditPackageDialogProps {
  open: boolean;
  handleClose: (pkg?: Package) => void;
  packageData: Package | null;
}

const EditPackageDialog: React.FC<EditPackageDialogProps> = ({ open, handleClose, packageData }) => {
  const { api, executeApiCall } = useApi();
  const [formData, setFormData] = useState<Package | null>(packageData);
  const [chatgptSummary, setChatgptSummary] = useState<string>('');
  const [summaryOptions, setSummaryOptions] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [prompt, setPrompt] = useState<string>('');
  const [showPrompt, setShowPrompt] = useState<boolean>(false);
  const [showOptions, setShowOptions] = useState<boolean>(true);

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setFormData(packageData);
    setChatgptSummary(packageData?.chatgpt_summary || '');
    setSummaryOptions([]);
    setError(null);
    setPrompt('');
    setShowPrompt(false);
    setShowOptions(true);
  }, [packageData]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    if (formData) {
      setFormData({
        ...formData,
        [name]: value,
      });
    }
  };

  const handleSummaryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setChatgptSummary(e.target.value);
  };

  const handleSave = async () => {
    if (formData) {
      try {
        const updatedPkg = { ...formData, chatgpt_summary: chatgptSummary };
        await executeApiCall(() => api.updatePackage(formData.id, updatedPkg));
        handleClose(updatedPkg);
      } catch (error) {
        console.error('Failed to save package:', error);
      }
    }
  };

  const handleGenerateSummary = async () => {
    if (formData) {
      try {
        setLoading(true);
        // setSummaryOptions([]);
        // setPrompt('');
        setShowPrompt(false);
        setTimeout(() => {
          if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: 'smooth' });
          }
        }, 200)
        const result = await executeApiCall(() => api.generateSummary(formData.id));
        setSummaryOptions(options => ([...options, ...result.results]));
        setPrompt(result.prompt);
        setError(null);
        setLoading(false);

        setTimeout(() => {
          if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: 'smooth' });
          }
        }, 200)
      } catch (error: any) {
        console.error('Failed to generate summary:', error);
        if (error.response && error.response.data && error.response.data.error && error.response.data.error.message) {
          setError(error.response.data.error.message);
        } else {
          setError('Failed to generate summary.');
        }
        setLoading(false);
      }
    }
  };

  const handleSelectSummary = (summary: string) => {
    setChatgptSummary(summary);
    setShowOptions(false);
    // setSummaryOptions([]);
  };

  if (!formData) return null;

  return (
    <Dialog open={open} onClose={() => handleClose()} maxWidth="md" fullWidth>
      <DialogTitle>Edit Summary</DialogTitle>
      <DialogContent>
        <TableContainer component={Paper}>
          <Table>
            <TableBody>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>{formData.id}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>{formData.name}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Title</TableCell>
                <TableCell>{formData.title}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Author</TableCell>
                <TableCell>{formData.author}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Organization</TableCell>
                <TableCell>{formData.organization?.title || ''}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Access Category</TableCell>
                <TableCell>{formData.access_category}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Geographical Span</TableCell>
                <TableCell>{formData.geo_span}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>File Format</TableCell>
                <TableCell>{formData.file_format}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>License</TableCell>
                <TableCell>{formData.license_title}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Published Date</TableCell>
                <TableCell>{formData.published_date}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Notes</TableCell>
                <TableCell>{formData.notes}</TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Tags</TableCell>
                <TableCell>{formData.tags.map(tag => tag.name).join(', ')}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TableContainer>
        <Box sx={{ mt: 2 }}>
          <TextField
            fullWidth
            multiline
            minRows={4}
            label="Summary"
            name="chatgpt_summary"
            value={chatgptSummary}
            onChange={handleSummaryChange}
            sx={{ mb: 2 }}
          />
          <Button variant="outlined" onClick={handleGenerateSummary} disabled={loading}>
            Generate Summary
          </Button>
          {loading && (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
              <CircularProgress />
            </Box>
          )}
          {summaryOptions.length > 0 && (
            <Box sx={{ mt: 2 }}>
              <Button
                onClick={() => setShowPrompt(!showPrompt)}
                startIcon={showPrompt ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                size="large"
              >
                {showPrompt ? 'Hide Prompt' : 'Show Prompt'}
              </Button>
              <Collapse in={showPrompt}>
                <Box sx={{ mt: 2, mb: 2, p: 2, border: '1px solid', borderColor: 'grey.400', whiteSpace: 'pre-line'}}>
                  <Typography variant="body2">{prompt}</Typography>
                </Box>
              </Collapse>
              <Button
                onClick={() => setShowOptions(!showOptions)}
                size="large"
                startIcon={showOptions ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              >
                {showOptions ? 'Hide Options' : 'Show Options'}
              </Button>
              <Collapse in={showOptions}>
                <Box sx={{ mt: 2 }}>
                  {summaryOptions.map((option, index) => (
                    <Button
                      key={index}
                      fullWidth
                      variant="outlined"
                      sx={{ mb: 2, textAlign: 'left', whiteSpace: 'pre-line', textTransform: 'none' }}
                      onClick={() => handleSelectSummary(option)}
                    >
                      {option}
                    </Button>
                  ))}
                </Box>
              </Collapse>
            </Box>
          )}
          {error && (
            <Box sx={{ mt: 2 }}>
              <Alert severity="error">{error}</Alert>
            </Box>
          )}
          <div ref={scrollRef}></div>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => handleClose()} color="secondary">Cancel</Button>
        <Button onClick={handleSave} color="primary">Save</Button>
      </DialogActions>
    </Dialog>
  );
};

export default EditPackageDialog;
