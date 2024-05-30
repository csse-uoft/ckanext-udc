import * as React from 'react';
import { styled } from '@mui/material/styles';
import ArrowForwardIosSharpIcon from '@mui/icons-material/ArrowForwardIosSharp';
import MuiAccordion, { AccordionProps } from '@mui/material/Accordion';
import MuiAccordionSummary, { AccordionSummaryProps } from '@mui/material/AccordionSummary';
import MuiAccordionDetails from '@mui/material/AccordionDetails';
import Typography from '@mui/material/Typography';
import { Detail } from './maturityLevels';
import { highlightText } from './utils';

const Accordion = styled((props: AccordionProps) => (
  <MuiAccordion disableGutters elevation={0} square {...props} />
))(({ theme }) => ({
  border: `1px solid ${theme.palette.divider}`,
  '&:not(:last-child)': {
    borderBottom: 0,
  },
  '&::before': {
    display: 'none',
  },
}));

const AccordionSummary = styled((props: AccordionSummaryProps) => (
  <MuiAccordionSummary
    expandIcon={<ArrowForwardIosSharpIcon sx={{ fontSize: '0.9rem' }} />}
    {...props}
  />
))(({ theme }) => ({
  backgroundColor: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, .05)' : 'rgba(0, 0, 0, .03)',
  flexDirection: 'row-reverse',
  '& .MuiAccordionSummary-expandIconWrapper.Mui-expanded': {
    transform: 'rotate(90deg)',
  },
  '& .MuiAccordionSummary-content': {
    marginLeft: theme.spacing(1),
  },
}));

const AccordionDetails = styled(MuiAccordionDetails)(({ theme }) => ({
  padding: theme.spacing(2),
  borderTop: '1px solid rgba(0, 0, 0, .125)',
}));

interface AccordionComponentProps {
  detail: Detail;
  expanded: boolean;
  onChange: (event: React.SyntheticEvent, isExpanded: boolean) => void;
  query: string;
}

const AccordionComponent: React.FC<AccordionComponentProps> = ({ detail, expanded, onChange, query }) => {
  return (
    <Accordion expanded={expanded} onChange={onChange}>
      <AccordionSummary>
        <Typography variant="subtitle1">{highlightText(detail.label, query)}</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Typography variant="body2" sx={{ whiteSpace: "pre-line" }}>
          <strong>Category:</strong> {highlightText(detail.category, query)}
        </Typography>
        <Typography variant="body2" sx={{ whiteSpace: "pre-line" }}>
          <strong>Short Description:</strong> {highlightText(detail.shortDescription, query)}
        </Typography>
        <Typography variant="body2" sx={{ whiteSpace: "pre-line" }}>
          <strong>Long Description:</strong> {highlightText(detail.longDescription, query)}
        </Typography>
      </AccordionDetails>
    </Accordion>
  );
};

export default AccordionComponent;
