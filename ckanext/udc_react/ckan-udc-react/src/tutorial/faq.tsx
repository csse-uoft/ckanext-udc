import React, { useEffect, useState } from "react";
import { MarkdownWithTOC } from "./MarkdownWithTOC";
import { Container } from "@mui/system";
import { Box, Button, CssBaseline, CircularProgress, Paper } from "@mui/material";
import { FAQ } from "./faq-list";


const FAQItem: React.FC<FAQ> = ({ question, beforeTOC, markdown, markdownPath, component }) => {
  const [md, setMd] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (component) {
      setLoading(false);
      return;
    }

    if (markdown) {
      setMd(markdown);
      setLoading(false);
    } else {
      fetch(markdownPath!)
        .then(response => response.text())
        .then(text => {
          setMd(text);
          setLoading(false);
        })
    }
  }, [component, markdown, markdownPath]);

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
        {component ? component : <MarkdownWithTOC markdown={md} beforeTOC={beforeTOC} />}

      </Box>
    </Container>
  );
};

export default FAQItem;
