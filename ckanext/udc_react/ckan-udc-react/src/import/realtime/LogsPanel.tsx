import { Card, CardContent, Typography, Box } from '@mui/material';
import { List, AutoSizer } from 'react-virtualized';
import React, { useEffect, useRef, useState } from 'react';
import { ImportLog } from './types';
import { debounce } from 'lodash';

interface LogsPanelProps {
  importLogs: ImportLog[]; // Logs passed in from parent
  autoScroll: boolean; // Whether auto-scrolling is enabled
}

export const LogsPanel: React.FC<LogsPanelProps> = ({ importLogs, autoScroll }) => {
  const [renderedLogs, setRenderedLogs] = useState<ImportLog[]>([]); // Logs to be rendered on the screen
  const logQueueRef = useRef<ImportLog[]>([]); // Queue for incoming logs
  const listRef = useRef<List>(null); // Reference to the List component

  useEffect(() => {
    logQueueRef.current.push(...importLogs); // Add new logs to the queue
    if (logQueueRef.current.length === 1) {
      // Start flushing the queue if it's the first log
      flushLogQueue();
    }
  }, [importLogs]);

  // Debounce function to render logs
  const flushLogQueue = debounce(() => {
    if (logQueueRef.current.length > 0) {
      setRenderedLogs((prevLogs) => {
        const list = listRef.current;
        const newLogs = [...prevLogs, ...logQueueRef.current];
        logQueueRef.current = []; // Clear the queue after rendering

        const isAtBottom = list
          ? list.scrollHeight - list.scrollTop === list.clientHeight
          : false;

        if (list && autoScroll && isAtBottom) {
          setTimeout(() => list.scrollToRow(newLogs.length - 1), 0); // Auto-scroll to the bottom
        }

        return newLogs;
      });
    }
  }, 300); // Adjust debounce delay as needed

  // Render each log item
  const renderLogRow = ({ index, key, style }: any) => {
    const log = renderedLogs[index];
    return (
      <div key={key} style={style}>
        <Typography variant="body2" color="textSecondary">
          {log.level}: {log.message}
        </Typography>
      </div>
    );
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6">Logs</Typography>
        <Box height={300} border={1} borderColor="grey.300">
          <AutoSizer>
            {({ height, width }) => (
              <List
                ref={listRef}
                width={width}
                height={height}
                rowCount={renderedLogs.length}
                rowHeight={(idx) =>
                  renderedLogs[idx]
                    ? renderedLogs[idx].message.split('\n').length * 20
                    : 20
                }
                rowRenderer={renderLogRow}
              />
            )}
          </AutoSizer>
        </Box>
      </CardContent>
    </Card>
  );
};
