import React, { useEffect, useState } from "react";
import { Box, Grid, Typography, Link } from "@mui/material";
import { Markdown } from "./Markdown";

interface Heading {
  id: string;
  text: string;
  level: number;
}

interface MarkdownWithTOCProps {
  markdown: string;
  beforeTOC?: React.ReactNode;
}

export const MarkdownWithTOC: React.FC<MarkdownWithTOCProps> = ({ markdown, beforeTOC }) => {
  const [headings, setHeadings] = useState<Heading[]>([]);

  // Extract headings from markdown content
  useEffect(() => {
    const parsedHeadings: Heading[] = [];
    const markdownContent = document.getElementById("markdown-content");
    if (markdownContent) {
      const headingElements = markdownContent.querySelectorAll("h1, h2, h3");
      headingElements.forEach((heading) => {
        const id = heading.innerText.toLowerCase().replace(/ /g, "-").replace(/[^\w-]+/g, "");
        parsedHeadings.push({
          id,
          text: heading.innerText,
          level: parseInt(heading.tagName.substring(1)), // Extract number from h1, h2, etc.
        });
        heading.id = id; // Assign the ID for the heading so it can be linked
      });
      setHeadings(parsedHeadings);
    }
  }, [markdown]);

  // Function to scroll smoothly to the heading
  const handleLinkClick = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      window.scrollTo({
        top: element.offsetTop - 10, // Offset for a little space above
        behavior: "smooth", // Smooth scrolling
      });
    }
  };

  return (
    <Grid container spacing={2}>
      {/* Left Column: Markdown Content */}
      <Grid item xs={8}>
        <Box id="markdown-content">
          <Markdown>{markdown}</Markdown>
        </Box>
      </Grid>

      {/* Right Column: Table of Contents */}
      <Grid item xs={4}>
        <Box sx={{ position: "sticky", top: "20px", paddingLeft: 2 }}>
          {beforeTOC}
          <Typography variant="h6" sx={{ mb: 2 }}>Table of Contents</Typography>
          {headings.map((heading, index) => (
            <Link
              key={index}
              onClick={(e) => {
                e.preventDefault(); // Prevent the default jump to behavior
                handleLinkClick(heading.id); // Smooth scroll to heading
              }}
              href={`#${heading.id}`}
              sx={{
                fontSize: `${1 - (heading.level - 1) * 0.05}rem`, // Font size decreases with level
                display: "block",
                marginLeft: `${(heading.level - 1) * 16}px`, // Indentation for different levels
                cursor: "pointer",
              }}
            >
              {heading.text}
            </Link>
          ))}
        </Box>
      </Grid>
    </Grid>
  );
};
