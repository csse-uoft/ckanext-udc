import { Typography } from "@mui/material"
import React from "react"
import ReactMarkdown from "react-markdown"

export const Markdown: React.FC<{ children: string }> = (props) => {
  return (
    <ReactMarkdown components={{
      h1: ({ children }) => <Typography variant="h3" sx={{ fontSize: "2.4rem", mb: 2 }}>{children}</Typography>,
      h2: ({ children }) => <Typography variant="h4" sx={{ mb: 2 }}>{children}</Typography>,
      h3: ({ children }) => <Typography variant="h5" sx={{ mb: 1 }}>{children}</Typography>,
      h4: ({ children }) => <Typography variant='h6' sx={{ mb: 1 }}>{children}</Typography>,
      h5: ({ children }) => <Typography variant='h6' sx={{ fontSize: "1.05rem", mb: 0.5 }}>{children}</Typography>,
    }}>
      {props.children}
    </ReactMarkdown>
  )
}