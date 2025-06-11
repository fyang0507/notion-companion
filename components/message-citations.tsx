'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ExternalLink, FileText } from 'lucide-react';
import { Citation } from '@/types/chat';

interface MessageCitationsProps {
  citations: Citation[];
}

export function MessageCitations({ citations }: MessageCitationsProps) {
  if (!citations.length) return null;

  return (
    <div className="space-y-2 w-full">
      <p className="text-xs text-muted-foreground font-medium">Sources:</p>
      <div className="grid gap-2">
        {citations.map((citation) => (
          <Card 
            key={citation.id} 
            className="citation-hover border-l-4 border-l-primary/30 hover:border-l-primary transition-all cursor-pointer"
          >
            <CardContent className="p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-2 flex-1 min-w-0">
                  <FileText className="h-4 w-4 mt-0.5 flex-shrink-0 text-muted-foreground" />
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="font-medium text-sm truncate">{citation.title}</p>
                      <Badge variant="secondary" className="text-xs">
                        {Math.round(citation.score * 100)}%
                      </Badge>
                    </div>
                    
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {citation.preview}
                    </p>
                  </div>
                </div>

                <Button 
                  variant="ghost" 
                  size="icon"
                  className="h-6 w-6 flex-shrink-0"
                  asChild
                >
                  <a 
                    href={citation.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}