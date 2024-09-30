import React, { useEffect, useState } from "react";
import { MarkdownWithTOC } from "./MarkdownWithTOC";
import { Container } from "@mui/system";
import { Box, Button, CssBaseline, CircularProgress, Paper } from "@mui/material";
import { OpenInNew as OpenInNewIcon, Add as CreateIcon } from '@mui/icons-material';
import { Link } from "./components/Link";

const CreateCatalogueEntry: React.FC = () => {
  const [md, setMd] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    fetch('/udc-react/create-catalogue-entry.md')
      .then(response => response.text())
      .then(text => {
        setMd(text);
        setLoading(false);
      })
  }, []);

  if (loading) {
    return (
      <Container sx={{ padding: 4, textAlign: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container>
      <Box sx={{ p: 3, m: 2 }}>
        <CssBaseline />

        <MarkdownWithTOC markdown={md}
          beforeTOC={<>
            <Link label="Create Catalogue Entry Now" url="/catalogue/new"/>
            <Link label="Create Organization Now" url="/organization/new"/>
            <Link label="Maturity Levels" url="/udc-react/tutorial/maturity-levels"/>
          </>}
           />

      </Box>
    </Container>
  );
};

export default CreateCatalogueEntry;
