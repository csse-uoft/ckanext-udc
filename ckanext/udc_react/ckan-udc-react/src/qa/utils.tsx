import React from 'react';
import Ajv from 'ajv';
// @ts-ignore
import { parse } from 'json-source-map';
import { configSchema } from './maturityLevels';

export const highlightText = (text: string, query: string): React.ReactNode => {
  if (!query) return text;

  const parts = text.split(new RegExp(`(${query})`, 'gi'));
  return (
    <>
      {parts.map((part, index) =>
        part.toLowerCase() === query.toLowerCase() ? (
          <span key={index} style={{ backgroundColor: 'yellow' }}>{part}</span>
        ) : (
          part
        )
      )}
    </>
  );
};



export const validateConfig = (configString: string): { valid: boolean, message?: string, position?: { line: number, column: number } } => {
  
  const ajv = new Ajv();
  let parsedResult;
  try {
    parsedResult = parse(configString);
  } catch (error) {
    return { valid: false, message: 'Invalid JSON format' };
  }

  const { data: config, pointers } = parsedResult;

  const validate = ajv.compile(configSchema);
  const valid = validate(config);
  if (!valid && validate.errors) {
    const error = validate.errors[0];
    const errorPointer = pointers[error.instancePath];

    if (errorPointer) {
      return {
        valid: false,
        message: `Validation error at ${error.instancePath}: ${error.message}`,
        position: {
          line: errorPointer.value.line + 1,
          column: errorPointer.value.column + 1,
        },
      };
    } else {
      return {
        valid: false,
        message: `Validation error: ${error.message}`,
      };
    }
  }

  return { valid: true };
};