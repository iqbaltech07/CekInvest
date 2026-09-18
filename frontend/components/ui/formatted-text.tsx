import React from "react";

function parseInlineStyles(text: string): React.ReactNode[] {
  if (!text) return [];
  const regex = /(\*\*.*?\*\*|\*.*?\*|`.*?`|_.*?_)/g;
  const parts = text.split(regex);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={index} className="font-bold text-foreground">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={index}
          className="px-1.5 py-0.5 rounded bg-black/5 dark:bg-white/10 font-mono text-[85%] font-semibold text-primary"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    if (
      (part.startsWith("*") && part.endsWith("*")) ||
      (part.startsWith("_") && part.endsWith("_"))
    ) {
      return (
        <em key={index} className="italic text-foreground/90">
          {part.slice(1, -1)}
        </em>
      );
    }
    return part;
  });
}

type Block =
  | { type: "p"; lines: string[] }
  | { type: "ul"; items: string[] }
  | { type: "ol"; items: string[] }
  | { type: "h"; level: number; text: string };

interface FormattedTextProps {
  text: string | null | undefined;
  className?: string;
}

function cleanLaymanText(raw: string): string {
  if (!raw) return "";
  return raw
    .replace(/\[cite:[^\]]*\]/gi, "")
    .replace(/\[\d+\]/g, "")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/\s+([,\.\?!])/g, "$1");
}

export function FormattedText({ text, className = "" }: FormattedTextProps) {
  if (!text) return null;

  const cleanedText = cleanLaymanText(text);
  const rawLines = cleanedText.split(/\r?\n/);
  const blocks: Block[] = [];
  let currentBlock: Block | null = null;

  for (const line of rawLines) {
    const trimmed = line.trim();

    if (!trimmed) {
      currentBlock = null;
      continue;
    }

    // Heading
    const headerMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
    if (headerMatch) {
      currentBlock = {
        type: "h",
        level: headerMatch[1].length,
        text: headerMatch[2],
      };
      blocks.push(currentBlock);
      currentBlock = null; // Headings are self-contained
      continue;
    }

    // Bullet list item
    const bulletMatch = trimmed.match(/^[-*+]\s+(.*)$/);
    if (bulletMatch) {
      if (currentBlock && currentBlock.type === "ul") {
        currentBlock.items.push(bulletMatch[1]);
      } else {
        currentBlock = { type: "ul", items: [bulletMatch[1]] };
        blocks.push(currentBlock);
      }
      continue;
    }

    // Numbered list item
    const numberMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);
    if (numberMatch) {
      if (currentBlock && currentBlock.type === "ol") {
        currentBlock.items.push(numberMatch[2]);
      } else {
        currentBlock = { type: "ol", items: [numberMatch[2]] };
        blocks.push(currentBlock);
      }
      continue;
    }

    // Regular line (paragraph)
    if (currentBlock && currentBlock.type === "p") {
      currentBlock.lines.push(trimmed);
    } else {
      currentBlock = { type: "p", lines: [trimmed] };
      blocks.push(currentBlock);
    }
  }

  return (
    <div className={`space-y-3 leading-relaxed ${className}`}>
      {blocks.map((block, bIdx) => {
        switch (block.type) {
          case "h": {
            const hText = parseInlineStyles(block.text);
            if (block.level === 1) {
              return (
                <h1 key={bIdx} className="text-lg font-bold text-foreground mt-4 mb-2">
                  {hText}
                </h1>
              );
            }
            if (block.level === 2) {
              return (
                <h2 key={bIdx} className="text-base font-semibold text-foreground mt-3 mb-1.5">
                  {hText}
                </h2>
              );
            }
            return (
              <h3 key={bIdx} className="text-sm font-semibold text-foreground mt-2 mb-1">
                {hText}
              </h3>
            );
          }
          case "ul": {
            return (
              <ul key={bIdx} className="list-disc pl-5 space-y-1.5 my-2">
                {block.items.map((item, iIdx) => (
                  <li key={iIdx} className="pl-1">
                    {parseInlineStyles(item)}
                  </li>
                ))}
              </ul>
            );
          }
          case "ol": {
            return (
              <ol key={bIdx} className="list-decimal pl-5 space-y-1.5 my-2">
                {block.items.map((item, iIdx) => (
                  <li key={iIdx} className="pl-1">
                    {parseInlineStyles(item)}
                  </li>
                ))}
              </ol>
            );
          }
          case "p": {
            return (
              <p key={bIdx}>
                {block.lines.map((line, lIdx) => (
                  <React.Fragment key={lIdx}>
                    {lIdx > 0 && " "}
                    {parseInlineStyles(line)}
                  </React.Fragment>
                ))}
              </p>
            );
          }
        }
      })}
    </div>
  );
}
