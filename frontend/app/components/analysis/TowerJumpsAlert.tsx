import { Radio } from 'lucide-react';
import { Alert, AlertDescription } from '../ui/alert';

interface TowerJumpsAlertProps {
  jumpCount: number;
  totalIntervals?: number;
}

export function TowerJumpsAlert({ jumpCount, totalIntervals }: TowerJumpsAlertProps) {
  if (jumpCount === 0) return null;

  const percentage = totalIntervals ? ((jumpCount / totalIntervals) * 100).toFixed(1) : null;

  return (
    <Alert variant="destructive" className="border-red-200 bg-red-50">
      <AlertDescription>
        <div className="flex items-start gap-3">
          <Radio className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="font-semibold text-red-900">
              {jumpCount} Tower Jump{jumpCount !== 1 ? 's' : ''} Detected
            </div>
            <div className="text-sm text-red-700 mt-1">
              {percentage
                ? `${percentage}% of intervals show potential anomalous location changes`
                : 'Intervals with potential anomalous location changes found'
              }
            </div>
          </div>
        </div>
      </AlertDescription>
    </Alert>
  );
}
