import React from 'react';

/**
 * Parses a string containing template variables like {{selected_program}} or {{hospital_type}}
 * and renders them as styled variable chips.
 *
 * @param {string} text - The input text containing {{template}} variables
 * @returns {React.ReactNode}
 */
export function FormattedText({ text }) {
  if (!text || typeof text !== 'string') {
    return text || null;
  }

  // Regex to split by {{variable}}
  const parts = text.split(/(\{\{[^}]+\}\})/g);

  return (
    <>
      {parts.map((part, index) => {
        if (part.startsWith('{{') && part.endsWith('}}')) {
          const varName = part.slice(2, -2).trim();
          return (
            <span
              key={index}
              className="template-var-chip"
              title={`Dynamic Variable: ${varName}`}
            >
              &#123;&#123;{varName}&#125;&#125;
            </span>
          );
        }
        return part;
      })}
    </>
  );
}

export default FormattedText;
