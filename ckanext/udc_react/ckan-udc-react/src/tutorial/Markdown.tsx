import { Link, Typography } from "@mui/material";
import React from "react";
import ReactMarkdown from "react-markdown";
import { useNavigate } from "react-router-dom";
import rehypeRaw from 'rehype-raw';
import { REACT_PATH } from "../constants";

export const Markdown: React.FC<{ children: string }> = (props) => {
  const navigate = useNavigate();

  // Function to generate id from text
  const generateId = (text: string) => {
    return text.toLowerCase().replace(/ /g, "-").replace(/[^\w-]+/g, "");
  };


  return (
    <ReactMarkdown
      rehypePlugins={[rehypeRaw]}
      components={{
        h1: ({ children }) => {
          if (children) {
            const id = generateId(children.toString());
            return (
              <>
                <Typography variant="h1" id={id} sx={{
                  fontSize: "2rem", pb: "0.3em", borderBottom: "1px solid rgba(0, 0, 0, 0.12)",
                  lineHeight: "1.25", mt: '1.5rem', mb: "1rem"
                }}>
                  {children}
                </Typography>
              </>
            );
          }
        },
        h2: ({ children }) => {
          if (children) {
            const id = generateId(children.toString());
            return (
              <Typography variant="h2" id={id} sx={{
                fontSize: "1.5rem", pb: "0.3em", borderBottom: "1px solid rgba(0, 0, 0, 0.12)",
                lineHeight: "1.25", mt: '1.5rem', mb: "1rem"
              }}>
                {children}
              </Typography>
            );
          }
        },
        h3: ({ children }) => {
          if (children) {
            const id = generateId(children.toString());
            return (
              <Typography variant="h3" id={id} sx={{ fontSize: "1.25rem", mt: '1.5rem', mb: "1rem" }}>
                {children}
              </Typography>
            );
          }
        },
        h4: ({ children }) => {
          if (children) {
            const id = generateId(children.toString());
            return (
              <Typography variant="h4" id={id} sx={{ fontSize: "1rem", mt: '1.5rem', mb: "1rem" }}>
                {children}
              </Typography>
            );
          }
        },
        h5: ({ children }) => {
          if (children) {
            const id = generateId(children.toString());
            return (
              <Typography variant="h5" id={id} sx={{ fontSize: "0.875rem", mt: '1.5rem', mb: "1rem" }}>
                {children}
              </Typography>
            );
          }
        },
        h6: ({ children }) => {
          if (children) {
            const id = generateId(children.toString());
            return (
              <Typography variant="h6" id={id} sx={{ fontSize: "0.85rem", mt: '1.5rem', mb: "1rem", color: "#59636e" }}>
                {children}
              </Typography>
            );
          }
        },
        p: ({ children }) => {
          return (
            <Typography variant="body2" sx={{ fontSize: "16px", mt: '1.5rem', mb: "1rem", }}>
              {children}
            </Typography>
          );
        },
        img: ({ src, alt }) => {
          return (
            <img src={`/${REACT_PATH}/` + src} alt={alt} style={{ maxWidth: "100%", paddingTop: "4px" }} />
          );
        },
        a: ({ children, href, target, rel }) => {
          if (href?.startsWith(`/${REACT_PATH}`)) {
            return <Link sx={{cursor: 'pointer'}} onClick={() => navigate(href)}>{children}</Link>;
          }
          return (
            <Link href={href} target={target || '_blank'} rel={rel}>{children}</Link>
          );
        },
      }}
    >
      {props.children}
    </ReactMarkdown>
  );
};
