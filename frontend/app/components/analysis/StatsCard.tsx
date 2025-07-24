import type { LucideIcon } from 'lucide-react';
import React, { useMemo } from 'react';

interface Stat {
  label: string;
  value: string | number;
  subtext?: string;
  color?: 'default' | 'green' | 'red' | 'blue' | 'purple';
}

interface StatsCardProps {
  title: string;
  icon: LucideIcon;
  stats: Stat[];
  className?: string;
}

export const StatsCard = React.memo(function StatsCard({ title, icon: Icon, stats, className = '' }: StatsCardProps) {
  const getValueColor = useMemo(() => (color?: string) => {
    switch (color) {
      case 'green':
        return 'text-green-600';
      case 'red':
        return 'text-red-600';
      case 'blue':
        return 'text-blue-600';
      case 'purple':
        return 'text-purple-600';
      default:
        return 'text-gray-900';
    }
  }, []);

  return (
    <div className={`bg-white rounded-lg border border-gray-200 p-4 ${className}`}>
      <div className="flex items-center gap-2 mb-3">
        <Icon className="w-4 h-4 text-blue-600" />
        <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
      </div>

      <div className="space-y-3">
        {stats.map((stat, index) => (
          <div key={index} className="flex justify-between items-center">
            <span className="text-sm text-gray-600">{stat.label}</span>
            <div className="flex items-center gap-2">
              <span className={`text-sm font-mono font-medium ${getValueColor(stat.color)}`}>
                {typeof stat.value === 'number' ? stat.value.toLocaleString() : stat.value}
              </span>
              {stat.subtext && (
                <span className="text-xs text-gray-500">
                  {stat.subtext}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
});
