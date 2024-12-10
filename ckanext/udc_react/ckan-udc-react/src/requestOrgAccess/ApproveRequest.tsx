import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Avatar,
  Container,
  Paper,
  CardActions,
  CardHeader,
  TableContainer,
  Table,
  TableBody,
  TableRow,
  TableCell,
  Alert,
  CircularProgress,
} from '@mui/material';
import { useParams } from 'react-router-dom';
import { useApi } from '../api/useApi';
import { Dialog } from './Dialog';
import { OpenInNew } from '@mui/icons-material';

interface ApproveRequestProps {
  requester: {
    id: string;
    name: string;
    fullname: string;
    email: string;
    picture?: string;
    notes?: string;
  };
  organization: {
    id: string;
    name: string;
  };
  status: "pending" | "expired" | "accepted" | "rejected";
}


const ApproveRequest: React.FC = () => {
  const { executeApiCall, api } = useApi();

  const { token } = useParams<{ token: string }>();
  const [data, setData] = useState<ApproveRequestProps | null>(null);
  const [showDialog, setShowDialog] = useState<boolean>(false);
  const [dialog, setDialog] = useState<{ title: string, message: string }>({ title: '', message: '' });

  useEffect(() => {
    // Fetch user and organization from API
    if (token) {
      executeApiCall(() => api.decodeOrganizationAccessToken(token)).then((data) => {
        setData(data);
        console.log(data);
      }).catch((error) => {
        console.error('Failed to fetch user and organization:', error);
        setDialog({ title: 'Error', message: error });
        setShowDialog(true);
      });
    }


  }, [token]);


  const submit = (approve: boolean) => () => {
    if (token) {
      executeApiCall(() => api.approveOrDenyOrganizationAccess(token, approve)).then(() => {
        console.log('User approved');
        if (approve) {
          setDialog({ title: 'Success', message: 'User approved' });
          setShowDialog(true);
        } else {
          setDialog({ title: 'Success', message: 'User declined' });
          setShowDialog(true);
        }
      }).catch((error) => {
        console.error(`Failed to ${approve ? 'approve' : 'decline'} user:`, error);
        setDialog({ title: 'Error', message: error });
        setShowDialog(true);
      });
    }
  }

  const handleCloseError = () => {
    setShowDialog(false);
  }

  if (!data) {
    return (
      <Container>
        <Paper elevation={3} sx={{ padding: 3, m: 2 }}>
          <CircularProgress />
          <Typography variant="h6" gutterBottom>
            Loading...
          </Typography>
        </Paper>
        <Dialog title={dialog.title} open={showDialog} onClose={() => {
          setShowDialog(false);
          if (dialog.title.includes("Invalid User")) {
            window.location.href = "/user/login?next=" + encodeURIComponent(window.location.href);
          }
        }} message={dialog.message} />

      </Container>
    );
  }

  return (
    <Container>
      <Paper elevation={3} sx={{ padding: 3, m: 2 }}>
        <Typography variant="h6" gutterBottom>
          Approve {data.requester.name} to join {data.organization.name}?
        </Typography>

        {data.status === "expired" && (
          <Alert severity="error" sx={{ mb: 2 }}>
            This request has expired.
          </Alert>
        )}

        {data.status === "accepted" && (
          <Alert severity="success" sx={{ mb: 2 }}>
            This request has been accepted.
          </Alert>
        )}

        {data.status === "rejected" && (
          <Alert severity="error" sx={{ mb: 2 }}>
            This request has been rejected.
          </Alert>
        )}

        <Card variant='outlined'>
          <CardContent>
            <Box display="flex" alignItems="center" mb={2} gap={2} sx={{ cursor: 'pointer' }}
              onClick={() => window.open("/user/" + data.requester.name, "_blank")}>
              {data.requester.picture ? (
                <Avatar alt={data.requester.name} src={data.requester.picture} />
              ) : (
                <Avatar>{data.requester.name.charAt(0).toUpperCase()}</Avatar>
              )}
              <Typography variant="body1">{data.requester.name}</Typography>
            </Box>
            <TableContainer component={Paper}>
              <Table>
                <TableBody>

                  <TableRow>
                    <TableCell>
                      <Typography variant="body2">Username:</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{data.requester.fullname}</Typography>
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>
                      <Typography variant="body2">
                        User Profile:
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        <a href={"/user/" + data.requester.name} target="_blank" rel="noopener noreferrer">
                          Go to User Profile <OpenInNew fontSize="small" />
                        </a>
                      </Typography>
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>
                      <Typography variant="body2">Email:</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{data.requester.email}</Typography>
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>
                      <Typography variant="body2">Message:</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" whiteSpace="pre">{data.requester.notes}</Typography>
                    </TableCell>
                  </TableRow>

                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
          <CardActions sx={{ ml: 1, mb: 1 }}>
            <Button variant="contained" color="primary" onClick={submit(true)} disabled={data.status !== "pending"}>
              Accept
            </Button>
            <Button variant="contained" color="error" onClick={submit(false)} disabled={data.status !== "pending"}>
              Reject
            </Button>
          </CardActions>
        </Card>

      </Paper>
      <Dialog title={dialog.title} open={showDialog} onClose={handleCloseError} message={dialog.message} />

    </Container>
  );
};

export default ApproveRequest;
