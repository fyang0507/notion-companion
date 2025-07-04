'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ExternalLink, FileText, File, Copy } from 'lucide-react';
import { Citation } from '@/types/chat';
import { cn } from '@/lib/utils';

interface MessageCitationsProps {
  citations: Citation[];
}

export function MessageCitations({ citations }: MessageCitationsProps) {
  if (!citations.length) return null;

  const handleCopyText = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      console.error('Failed to copy text:', err);
    }
  };

  const getSourceIcon = (type: string) => {
    return type === 'chunk' ? File : FileText;
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.9) return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
    if (score >= 0.7) return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
    return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200';
  };

  return (
    <div className="space-y-2 w-full">
      <p className="text-xs text-muted-foreground font-medium">Sources:</p>
      <div className="grid gap-2">
        {citations.map((citation) => {
          const SourceIcon = getSourceIcon(citation.type || 'default');
          const isNotionUrl = citation.url?.startsWith('notion://');
          
          return (
            <Card 
              key={citation.id} 
              className="citation-hover border-l-4 border-l-primary/30 hover:border-l-primary transition-all"
            >
              <CardContent className="p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-2 flex-1 min-w-0">
                    <SourceIcon className="h-4 w-4 mt-0.5 flex-shrink-0 text-muted-foreground" />
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <p className="font-medium text-sm truncate">{citation.title}</p>
                        {citation.score && (
                          <Badge 
                            variant="secondary" 
                            className={cn("text-xs", getScoreColor(citation.score))}
                          >
                            {Math.round(citation.score * 100)}%
                          </Badge>
                        )}
                        {citation.type && (
                          <Badge variant="outline" className="text-xs">
                            {citation.type}
                          </Badge>
                        )}
                        {citation.type === 'chunk' && citation.metadata?.chunk_index !== undefined && (
                          <Badge variant="outline" className="text-xs">
                            #{citation.metadata.chunk_index + 1}
                          </Badge>
                        )}
                      </div>
                      
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {citation.preview || citation.snippet}
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-1 flex-shrink-0">
                    <Button 
                      variant="ghost" 
                      size="icon"
                      className="h-6 w-6"
                      onClick={() => handleCopyText(`${citation.title}\n${citation.preview || citation.snippet || ''}`)}
                      title="Copy text"
                    >
                      <Copy className="h-3 w-3" />
                    </Button>
                    
                    {!isNotionUrl ? (
                      <Button 
                        variant="ghost" 
                        size="icon"
                        className="h-6 w-6"
                        asChild
                      >
                        <a 
                          href={citation.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          title="Open in Notion"
                        >
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </Button>
                    ) : (
                      <Button 
                        variant="ghost" 
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => handleCopyText(citation.url || '')}
                        title="Copy Notion URL"
                      >
                        <ExternalLink className="h-3 w-3 opacity-50" />
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}