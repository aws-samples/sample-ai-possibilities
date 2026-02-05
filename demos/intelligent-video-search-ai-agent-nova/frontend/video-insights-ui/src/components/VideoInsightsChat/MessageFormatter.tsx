import React from 'react';
import { MessageFormatterProps } from '../../types';

// Helper function to parse inline markdown
const parseInlineMarkdown = (text: string): React.ReactNode[] => {
  // Simple approach - convert markdown patterns one by one
  let result = text;
  let keyCounter = 0;
  const parts: React.ReactNode[] = [];
  
  // Process bold text
  result = result.replace(/\*\*(.*?)\*\*/g, (match, content) => {
    const key = `bold-${keyCounter++}`;
    return `<BOLD:${key}:${content}>`;
  });
  
  // Process italic text  
  result = result.replace(/\*(.*?)\*/g, (match, content) => {
    const key = `italic-${keyCounter++}`;
    return `<ITALIC:${key}:${content}>`;
  });
  
  // Process code text
  result = result.replace(/`(.*?)`/g, (match, content) => {
    const key = `code-${keyCounter++}`;
    return `<CODE:${key}:${content}>`;
  });
  
  // Process links
  result = result.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, text, url) => {
    const key = `link-${keyCounter++}`;
    return `<LINK:${key}:${text}:${url}>`;
  });
  
  // Split by our custom markers and convert back to React elements
  const segments = result.split(/(<[A-Z]+:[^>]+>)/);
  
  segments.forEach((segment, index) => {
    if (segment.startsWith('<BOLD:')) {
      const [, , content] = segment.slice(1, -1).split(':');
      parts.push(<strong key={`bold-${index}`}>{content}</strong>);
    } else if (segment.startsWith('<ITALIC:')) {
      const [, , content] = segment.slice(1, -1).split(':');
      parts.push(<em key={`italic-${index}`}>{content}</em>);
    } else if (segment.startsWith('<CODE:')) {
      const [, , content] = segment.slice(1, -1).split(':');
      parts.push(<code key={`code-${index}`} className="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono">{content}</code>);
    } else if (segment.startsWith('<LINK:')) {
      const parts_arr = segment.slice(1, -1).split(':');
      const content = parts_arr[2];
      const url = parts_arr[3];
      parts.push(<a key={`link-${index}`} href={url} className="text-blue-600 hover:text-blue-800 underline" target="_blank" rel="noopener noreferrer">{content}</a>);
    } else if (segment.trim()) {
      parts.push(segment);
    }
  });
  
  return parts;
};

const MessageFormatter: React.FC<MessageFormatterProps> = ({ content }) => {
  // Preprocess: strip markdown code blocks that the UI can't render
  const preprocessContent = (text: string): string => {
    // Remove code block markers like ```json, ```python, ``` etc.
    // This handles cases where the model outputs code blocks
    return text
      .replace(/```\w*\n?/g, '')  // Remove opening code block markers
      .replace(/```/g, '')         // Remove closing code block markers
      .trim();
  };

  const formatContent = (text: string): React.ReactNode[] => {
    const processedText = preprocessContent(text);
    const lines = processedText.split('\n');
    const result: React.ReactNode[] = [];
    let i = 0;
    
    while (i < lines.length) {
      const line = lines[i];
      
      // Headers
      if (line.startsWith('### ')) {
        result.push(<h3 key={i} className="text-lg font-bold mt-4 mb-2 text-gray-900 text-left">{parseInlineMarkdown(line.substring(4))}</h3>);
        i++;
      }
      else if (line.startsWith('## ')) {
        result.push(<h2 key={i} className="text-xl font-bold mt-4 mb-2 text-gray-900 text-left">{parseInlineMarkdown(line.substring(3))}</h2>);
        i++;
      }
      // Handle numbered lists by grouping consecutive numbered items
      else if (/^\d+\./.test(line.trim())) {
        const numberedItems: React.ReactNode[] = [];
        let listStartIndex = i;
        
        // Collect all consecutive numbered items
        while (i < lines.length && /^\d+\./.test(lines[i].trim())) {
          numberedItems.push(
            <li key={i} className="mb-1 text-gray-700 text-left">
              {parseInlineMarkdown(lines[i].trim().replace(/^\d+\.\s*/, ''))}
            </li>
          );
          i++;
        }
        
        // Wrap in ordered list
        result.push(
          <ol key={`ol-${listStartIndex}`} className="ml-6 mb-2 list-decimal space-y-1">
            {numberedItems}
          </ol>
        );
      }
      // Handle bullet lists by grouping consecutive bullet items
      else if (line.trim().startsWith('- ') || line.trim().startsWith('• ')) {
        const bulletItems: React.ReactNode[] = [];
        let listStartIndex = i;
        
        // Collect all consecutive bullet items
        while (i < lines.length && (lines[i].trim().startsWith('- ') || lines[i].trim().startsWith('• '))) {
          bulletItems.push(
            <li key={i} className="mb-1 text-gray-700 text-left text-base leading-relaxed">
              {parseInlineMarkdown(lines[i].trim().substring(2))}
            </li>
          );
          i++;
        }
        
        // Wrap in unordered list
        result.push(
          <ul key={`ul-${listStartIndex}`} className="ml-6 mb-2 list-disc space-y-1">
            {bulletItems}
          </ul>
        );
      }
      // Regular paragraphs
      else if (line.trim()) {
        result.push(<p key={i} className="mb-2 text-gray-700 text-left text-base leading-relaxed">{parseInlineMarkdown(line)}</p>);
        i++;
      }
      // Empty lines
      else {
        result.push(<br key={i} />);
        i++;
      }
    }
    
    return result;
  };

  return (
    <div className="prose prose-base max-w-none text-left">
      {formatContent(content)}
    </div>
  );
};

export default MessageFormatter;