import React, { useState, useEffect } from 'react';
import { Box, Typography, Button, Container, Collapse, TextField, CircularProgress } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import AccordionComponent from './AccordionComponent';
import { highlightText } from './utils';
import { getMaturityLevels } from '../api';
import { qaPageConfig, PageConfig, Detail, MaturityLevel } from './maturityLevels';


const QAPage: React.FC = () => {
  const [expandedPanels, setExpandedPanels] = useState<string[]>([]);
  const [visibleLevels, setVisibleLevels] = useState<{ [key: number]: boolean }>({});
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [pageConfig, setPageConfig] = useState<PageConfig | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchConfig = async () => {
      setLoading(true);
      let config;
      
      try {
        config = await getMaturityLevels();
      } catch (error) {
        console.error('Failed to fetch config, using fallback config', error);
      }
      if (!config) {
        config = qaPageConfig;
      }
      
      const initialVisibility = config.maturityLevels.reduce((acc: any, level: MaturityLevel) => {
        acc[level.level] = true;
        return acc;
      }, {});

      setPageConfig(config);
      setVisibleLevels(initialVisibility);
      setLoading(false);
    };

    fetchConfig();
  }, []);

  const handleExpandCollapseAllDetails = () => {
    if (expandedPanels.length > 0) {
      setExpandedPanels([]);
    } else {
      const allPanels = pageConfig?.maturityLevels.flatMap(level => level.details.map((_, index) => `panel${level.level}-${index}`)) || [];
      setExpandedPanels(allPanels);
    }
  };

  const handleExpandCollapseAllLevels = () => {
    const allVisible = Object.values(visibleLevels).every(v => v);
    const newVisibility = pageConfig?.maturityLevels.reduce((acc: any, level: MaturityLevel) => {
      acc[level.level] = !allVisible;
      return acc;
    }, {}) || {};
    setVisibleLevels(newVisibility);
  };

  const handleChange = (panel: string) => (event: React.SyntheticEvent, isExpanded: boolean) => {
    if (isExpanded) {
      setExpandedPanels(prev => [...prev, panel]);
    } else {
      setExpandedPanels(prev => prev.filter(item => item !== panel));
    }
  };

  const toggleLevelVisibility = (level: number) => {
    setVisibleLevels(prev => ({ ...prev, [level]: !prev[level] }));
  };

  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(event.target.value.toLowerCase());
  };

  if (loading) {
    return (
      <Container sx={{ padding: 4, textAlign: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  if (!pageConfig) {
    return (
      <Container sx={{ padding: 4, textAlign: 'center' }}>
        <Typography variant="h6">Failed to load configuration</Typography>
      </Container>
    );
  }

  const filteredMaturityLevels = pageConfig.maturityLevels.filter(level => {
    const levelMatches = level.title.toLowerCase().includes(searchQuery) || level.description.toLowerCase().includes(searchQuery);
    const detailsMatch = level.details.some(detail => 
      detail.label.toLowerCase().includes(searchQuery) || 
      detail.shortDescription.toLowerCase().includes(searchQuery) || 
      detail.longDescription.toLowerCase().includes(searchQuery) ||
      detail.category.toLowerCase().includes(searchQuery)
    );
    return levelMatches || detailsMatch;
  });

  return (
    <Container sx={{ padding: 4 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 2 }}>
        <Typography variant="h4">{pageConfig.title}</Typography>
      </Box>
      <Typography variant="body1" gutterBottom sx={{ whiteSpace: "pre-line" }}>
        {pageConfig.description}
      </Typography>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 2 }}>
        <Box>
          <Button
            variant="outlined"
            onClick={handleExpandCollapseAllLevels}
            sx={{ marginRight: 1, textTransform: 'none' }}
            startIcon={Object.values(visibleLevels).every(v => v) ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          >
            {Object.values(visibleLevels).every(v => v) ? 'Collapse All Levels' : 'Expand All Levels'}
          </Button>
          <Button
            variant="outlined"
            onClick={handleExpandCollapseAllDetails}
            sx={{ textTransform: 'none' }}
            startIcon={expandedPanels.length > 0 ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          >
            {expandedPanels.length > 0 ? 'Collapse All Details' : 'Expand All Details'}
          </Button>
        </Box>
      </Box>
      <TextField
        fullWidth
        label="Search"
        variant="outlined"
        value={searchQuery}
        onChange={handleSearchChange}
        sx={{ marginBottom: 2 }}
      />
      {filteredMaturityLevels.map((level: MaturityLevel) => {
        const levelMatches = level.title.toLowerCase().includes(searchQuery) || level.description.toLowerCase().includes(searchQuery);
        const filteredDetails = level.details.filter(detail => 
          detail.label.toLowerCase().includes(searchQuery) || 
          detail.shortDescription.toLowerCase().includes(searchQuery) || 
          detail.longDescription.toLowerCase().includes(searchQuery) ||
          detail.category.toLowerCase().includes(searchQuery)
        );

        return (
          <Box key={level.level} sx={{ marginBottom: 3 }}>
            <Box
              sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}
              onClick={() => toggleLevelVisibility(level.level)}
            >
              <Typography variant="h5" gutterBottom sx={{ whiteSpace: "pre-line" }}>
                {highlightText(level.title, searchQuery)}
              </Typography>
              <ExpandMoreIcon
                sx={{
                  transform: visibleLevels[level.level] ? 'rotate(180deg)' : 'rotate(0deg)',
                  transition: 'transform 0.3s',
                }}
              />
            </Box>
            <Typography variant="body1" gutterBottom sx={{ whiteSpace: "pre-line" }}>
              {highlightText(level.description, searchQuery)}
            </Typography>
            <Collapse in={visibleLevels[level.level]} timeout="auto" unmountOnExit>
              {levelMatches || filteredDetails.length > 0 ? (
                filteredDetails.map((detail: Detail, index: number) => (
                  <AccordionComponent
                    key={index}
                    detail={detail}
                    expanded={expandedPanels.includes(`panel${level.level}-${index}`)}
                    onChange={handleChange(`panel${level.level}-${index}`)}
                    query={searchQuery}
                  />
                ))
              ) : (
                <Typography variant="body2" sx={{ padding: 2 }}>No matching details found.</Typography>
              )}
            </Collapse>
          </Box>
        );
      })}
    </Container>
  );
};

export default QAPage;
