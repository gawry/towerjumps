import {
  BarChart3,
  CheckCircle,
  Clock,
  FileText,
  Flag,
  Radio,
  Search,
  Settings,
  XCircle
} from 'lucide-react';
import React from 'react';
import type { AnalysisEvent } from '../TowerJumpsAnalyzer';
import { Badge } from '../ui/badge';

// Event types matching the Python CLI
enum EventType {
  DATA_LOADING = 'data_loading',
  PROCESSING = 'processing',
  WINDOW_CREATION = 'window_creation',
  ANALYSIS_PROGRESS = 'analysis_progress',
  INTERVAL_COMPLETED = 'interval_completed',
  COMPLETION = 'completion',
  ERROR = 'error',
  TOWER_JUMP_DETECTED = 'tower_jump_detected',
}

interface EventItemProps {
  event: AnalysisEvent;
  index: number;
}

export const EventItem = React.memo(function EventItem({ event, index }: EventItemProps) {
  const getEventIcon = (eventType: string) => {
    const iconProps = { className: "w-4 h-4" };
    switch (eventType) {
      case EventType.DATA_LOADING:
        return <BarChart3 {...iconProps} />;
      case EventType.PROCESSING:
        return <Settings {...iconProps} />;
      case EventType.WINDOW_CREATION:
        return <Clock {...iconProps} />;
      case EventType.ANALYSIS_PROGRESS:
        return <Search {...iconProps} />;
      case EventType.INTERVAL_COMPLETED:
        return <CheckCircle {...iconProps} />;
      case EventType.COMPLETION:
        return <Flag {...iconProps} />;
      case EventType.ERROR:
        return <XCircle {...iconProps} />;
      case EventType.TOWER_JUMP_DETECTED:
        return <Radio {...iconProps} />;
      default:
        return <FileText {...iconProps} />;
    }
  };

  const getEventBadgeVariant = (eventType: string) => {
    switch (eventType) {
      case EventType.ERROR:
      case EventType.TOWER_JUMP_DETECTED:
        return 'destructive';
      case EventType.COMPLETION:
        return 'default';
      case EventType.DATA_LOADING:
      case EventType.PROCESSING:
      case EventType.WINDOW_CREATION:
        return 'secondary';
      default:
        return 'outline';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString();
    } catch {
      return timestamp;
    }
  };

  const formatDateTime = (dateTimeString: string) => {
    try {
      const date = new Date(dateTimeString);
      return date.toLocaleString();
    } catch {
      return dateTimeString;
    }
  };

  return (
    <div className="group flex items-start gap-3 p-3 rounded-lg border border-gray-100 hover:border-gray-200 hover:bg-gray-50/50 transition-all duration-150">
      <div className="flex-shrink-0 text-gray-600 mt-0.5">
        {getEventIcon(event.type)}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <Badge variant={getEventBadgeVariant(event.type)} className="text-xs font-medium">
            {event.type.replace('_', ' ')}
          </Badge>
          <span className="text-xs text-gray-500 font-mono">
            {formatTimestamp(event.timestamp)}
          </span>
        </div>

        <p className="text-sm text-gray-700 mb-2 leading-relaxed">
          {event.message}
        </p>

        {/* Event-specific data display */}
        {event.data && (
          <div className="text-xs bg-gray-50 border border-gray-100 rounded-md p-2 space-y-1">
            {/* Tower Jump Details */}
            {event.type === EventType.TOWER_JUMP_DETECTED && (
              <div className="space-y-1">
                {event.data.device_id && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Device:</span>
                    <span className="font-medium">{event.data.device_id}</span>
                  </div>
                )}
                {event.data.from_location && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">From:</span>
                    <span className="font-medium">{event.data.from_location}</span>
                  </div>
                )}
                {event.data.to_location && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">To:</span>
                    <span className="font-medium">{event.data.to_location}</span>
                  </div>
                )}
                {event.data.confidence && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Confidence:</span>
                    <span className="font-medium text-red-600">{(event.data.confidence * 100).toFixed(1)}%</span>
                  </div>
                )}
              </div>
            )}

            {/* Interval Completed Details */}
            {event.type === EventType.INTERVAL_COMPLETED && (
              <div className="space-y-1">
                {event.data.estimated_state && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">State:</span>
                    <span className="font-medium">{event.data.estimated_state}</span>
                  </div>
                )}
                {event.data.confidence && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Confidence:</span>
                    <span className="font-medium">{event.data.confidence}%</span>
                  </div>
                )}
                {event.data.is_tower_jump !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Status:</span>
                    <span className={`font-medium ${event.data.is_tower_jump ? 'text-red-600' : 'text-green-600'}`}>
                      {event.data.is_tower_jump ? 'Tower Jump' : 'Normal'}
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Processing Step Details */}
            {event.type === EventType.PROCESSING && event.data.step && (
              <div className="flex justify-between">
                <span className="text-gray-600">Step:</span>
                <span className="font-medium">
                  {event.data.step.replace('_', ' ')}
                  {event.data.progress && ` (${event.data.progress}%)`}
                </span>
              </div>
            )}

            {/* Window Creation Details */}
            {event.type === EventType.WINDOW_CREATION && (
              <div className="space-y-1">
                {event.data.window_count && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Windows:</span>
                    <span className="font-medium">{event.data.window_count.toLocaleString()}</span>
                  </div>
                )}
                {event.data.window_size_minutes && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Size:</span>
                    <span className="font-medium">{event.data.window_size_minutes} min</span>
                  </div>
                )}
              </div>
            )}

            {/* Analysis Progress Details */}
            {event.type === EventType.ANALYSIS_PROGRESS && (
              <div className="space-y-1">
                {event.data.current_window && event.data.total_windows && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Progress:</span>
                    <span className="font-medium">
                      {event.data.current_window} / {event.data.total_windows}
                      {event.data.progress_percentage && ` (${event.data.progress_percentage.toFixed(1)}%)`}
                    </span>
                  </div>
                )}
                {event.data.estimated_state && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">State:</span>
                    <span className="font-medium">{event.data.estimated_state}</span>
                  </div>
                )}
              </div>
            )}

            {/* Data Loading Details */}
            {event.type === EventType.DATA_LOADING && (
              <div className="space-y-1">
                {event.data.total_records && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Total:</span>
                    <span className="font-medium">{event.data.total_records.toLocaleString()}</span>
                  </div>
                )}
                {event.data.records_with_location && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">With Location:</span>
                    <span className="font-medium text-green-600">{event.data.records_with_location.toLocaleString()}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
});
