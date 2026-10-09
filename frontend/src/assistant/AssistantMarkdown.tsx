import { memo } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

function normalizeAssistantMarkdown(text: string): string {
  // Some models use a visible bullet character instead of Markdown list syntax.
  let fenced = false;
  return text.split("\n").map((line) => {
    if (/^\s*(```|~~~)/.test(line)) fenced = !fenced;
    return fenced ? line : line.replace(/^(\s*)[\u2022\u00b7]\s+/, "$1- ");
  }).join("\n");
}

export const AssistantMarkdown = memo(function AssistantMarkdown({ text }: { text: string }) {
  return <div className="assistantMarkdown" data-no-translate="true" translate="no">
    <Markdown
      remarkPlugins={[remarkGfm]}
      skipHtml
      components={{
        table: ({ node: _node, children, ...props }) => <div className="assistantMarkdownTableScroll"><table {...props}>{children}</table></div>,
        a: ({ node: _node, children, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer">{children}</a>,
      }}
    >{normalizeAssistantMarkdown(text)}</Markdown>
  </div>;
});
