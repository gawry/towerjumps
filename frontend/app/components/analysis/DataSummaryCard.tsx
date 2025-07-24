import { BarChart3 } from 'lucide-react';

interface DataSummaryCardProps {
  totalRecords: number;
  recordsWithLocation: number;
}

export function DataSummaryCard({ totalRecords, recordsWithLocation }: DataSummaryCardProps) {
  const completionRate = ((recordsWithLocation / totalRecords) * 100).toFixed(1);

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-3">
        <BarChart3 className="w-4 h-4 text-blue-600" />
        <h3 className="text-sm font-semibold text-gray-900">Data Summary</h3>
      </div>

      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600">Total Records</span>
          <span className="text-sm font-mono font-medium text-gray-900">
            {totalRecords.toLocaleString()}
          </span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600">With Location</span>
          <div className="flex items-center gap-2">
            <span className="text-sm font-mono font-medium text-green-600">
              {recordsWithLocation.toLocaleString()}
            </span>
            <span className="text-xs text-gray-500">
              ({completionRate}%)
            </span>
          </div>
        </div>

        <div className="pt-2 border-t border-gray-100">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">Missing Location</span>
            <span className="text-sm font-mono font-medium text-gray-500">
              {(totalRecords - recordsWithLocation).toLocaleString()}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
