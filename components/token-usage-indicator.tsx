'use client';

import { useState, useEffect } from 'react';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Zap, TrendingUp, DollarSign, Clock } from 'lucide-react';
import Link from 'next/link';

interface UsageData {
  currentTokens: number;
  monthlyLimit: number;
  costThisMonth: number;
  requestsToday: number;
  avgResponseTime: number;
}

export function TokenUsageIndicator() {
  const [usage, setUsage] = useState<UsageData>({
    currentTokens: 45780,
    monthlyLimit: 100000,
    costThisMonth: 12.45,
    requestsToday: 28,
    avgResponseTime: 1.2
  });

  const usagePercentage = (usage.currentTokens / usage.monthlyLimit) * 100;
  const getUsageColor = () => {
    if (usagePercentage < 50) return 'text-green-500';
    if (usagePercentage < 80) return 'text-yellow-500';
    return 'text-red-500';
  };

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" className="flex items-center gap-2 h-8 px-2">
          <Zap className={`h-4 w-4 ${getUsageColor()}`} />
          <div className="hidden sm:flex items-center gap-1">
            <span className="text-sm font-medium">{Math.round(usagePercentage)}%</span>
            <div className="w-8 h-1.5 bg-muted rounded-full overflow-hidden">
              <div 
                className={`h-full transition-all duration-300 ${
                  usagePercentage < 50 ? 'bg-green-500' :
                  usagePercentage < 80 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${usagePercentage}%` }}
              />
            </div>
          </div>
        </Button>
      </PopoverTrigger>
      
      <PopoverContent className="w-80" align="end">
        <div className="space-y-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="font-medium">Token Usage</h4>
              <Badge variant="outline" className="text-xs">
                Pro Plan
              </Badge>
            </div>
            
            <div className="space-y-1">
              <div className="flex justify-between text-sm">
                <span>This month</span>
                <span className="font-mono">
                  {usage.currentTokens.toLocaleString()} / {usage.monthlyLimit.toLocaleString()}
                </span>
              </div>
              <Progress value={usagePercentage} className="h-2" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Card>
              <CardContent className="p-3">
                <div className="flex items-center gap-2">
                  <DollarSign className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-xs text-muted-foreground">Cost</p>
                    <p className="font-medium text-sm">${usage.costThisMonth}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-3">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-xs text-muted-foreground">Today</p>
                    <p className="font-medium text-sm">{usage.requestsToday} requests</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">Avg response time:</span>
              <span className="font-medium">{usage.avgResponseTime}s</span>
            </div>
          </div>

          <div className="pt-2 border-t">
            <Link href="/analytics">
              <Button variant="outline" size="sm" className="w-full">
                View detailed usage
              </Button>
            </Link>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}