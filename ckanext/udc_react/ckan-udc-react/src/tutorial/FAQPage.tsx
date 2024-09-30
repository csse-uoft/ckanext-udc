import React from 'react';
import { Drawer, List, ListItemButton, ListItemText, Box, CssBaseline } from '@mui/material';
import { useNavigate, useParams, Routes, Route } from 'react-router-dom';
import FAQItem from './faq';
import { FAQList } from './faq-list';

const drawerWidth = 300;

const FAQPage: React.FC = () => {
  const navigate = useNavigate();
  const { faqId } = useParams<{ faqId: string }>();

  // If no FAQ is selected from the URL, default to the first FAQ
  const selectedFAQ = faqId || FAQList[0].id;

  // Function to find the selected FAQ by id
  const selectedFAQItem = FAQList.find(faq => faq.id === selectedFAQ);

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />

      {/* Drawer for listing questions */}
      <Drawer
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
            position: 'relative',
            overflowX: 'hidden'
          },
        }}
        variant="permanent"
        anchor="left"
      >
        <List>
          {FAQList.map(faq => (
            <ListItemButton
              key={faq.id}
              selected={faq.id === selectedFAQ}
              sx={{ pt: 1, pb: 1 }}
              onClick={() => navigate(`/udc-react/faq/${faq.id}`)}  // Navigate to the FAQ's dedicated path
            >
              <ListItemText
                primary={faq.question}
                primaryTypographyProps={{
                  fontWeight: (faq.id === selectedFAQ) ? 600 : 'normal',
                  color: (faq.id === selectedFAQ) ? 'primary' : 'text.primary'
                }}
              />
            </ListItemButton>
          ))}
        </List>
      </Drawer>

      {/* Main content area to render FAQ */}
      <Box
        component="main"
        sx={{ flexGrow: 1, width: `calc(100% - ${drawerWidth}px)` }}
      >
        {selectedFAQItem && (
          <FAQItem
            id={selectedFAQItem.id}
            question={selectedFAQItem.question}
            beforeTOC={selectedFAQItem.beforeTOC}
            markdown={selectedFAQItem.markdown}
            markdownPath={selectedFAQItem.markdownPath}
            component={selectedFAQItem.component}
          />
        )}
      </Box>
    </Box>
  );
};

export default FAQPage;
