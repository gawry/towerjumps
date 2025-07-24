import { useVirtualizer } from '@tanstack/react-virtual';
import { ChevronDown, ClipboardList } from 'lucide-react';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import type { AnalysisEvent } from '../TowerJumpsAnalyzer';
import { Button } from '../ui/button';
import { EventItem } from './EventItem';

interface EventsLogProps {
  events: AnalysisEvent[];
  isAnalyzing: boolean;
}

export const EventsLog = React.memo(function EventsLog({ events, isAnalyzing }: EventsLogProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const parentRef = useRef<HTMLDivElement>(null);
  const eventSizes = useRef<number[]>([]);

  // Memoize latest event preview to avoid recalculation
  const latestEventPreview = useMemo(() => {
    if (events.length === 0) return null;
    const latest = events[events.length - 1];
    const message = latest.message;
    return {
      text: message.length > 50 ? `${message.substring(0, 50)}...` : message,
      needsTruncation: message.length > 50
    };
  }, [events]);

  // Initialize event sizes when events change
  useEffect(() => {
    // Ensure we have size entries for all events
    while (eventSizes.current.length < events.length) {
      eventSizes.current.push(160); // Default size for new events
    }
    // Trim if we have fewer events
    if (eventSizes.current.length > events.length) {
      eventSizes.current = eventSizes.current.slice(0, events.length);
    }
  }, [events.length]);

  // Set up virtualizer with size state management
  const virtualizer = useVirtualizer({
    count: events.length,
    getScrollElement: () => parentRef.current,
    estimateSize: (index) => eventSizes.current[index] || 120,
    overscan: 2, // Reduced overscan for better performance
    measureElement: (element) => {
      // Get the index from the data-index attribute
      const index = parseInt(element?.getAttribute('data-index') || '0');
      // Measure the actual height and store it
      const height = element?.getBoundingClientRect().height ?? 120;
      eventSizes.current[index] = height;
      return height;
    },
  });

  // Auto-scroll to bottom when new events arrive and list is expanded
  useEffect(() => {
    if (isExpanded && events.length > 0) {
      // Small delay to ensure the virtualizer has updated
      setTimeout(() => {
        if (parentRef.current) {
          virtualizer.scrollToIndex(events.length - 1, {
            align: 'end',
            behavior: 'smooth',
          });
        }
      }, 50);
    }
  }, [events.length, isExpanded, virtualizer]);

  const toggleExpanded = () => {
    setIsExpanded(!isExpanded);
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      <div className="px-4 py-3 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ClipboardList className="w-4 h-4 text-blue-600" />
            <h3 className="text-sm font-semibold text-gray-900">Analysis Log</h3>
            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
              {events.length} events
            </span>
            {isAnalyzing && (
              <div className="animate-pulse">
                <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                  Live
                </span>
              </div>
            )}
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={toggleExpanded}
            className="text-gray-500 hover:text-gray-700 h-6 px-2"
          >
            <ChevronDown
              className={`w-4 h-4 transition-transform duration-200 ${
                isExpanded ? 'rotate-180' : ''
              }`}
            />
          </Button>
        </div>
      </div>

      <div
        className={`overflow-hidden transition-all duration-300 ease-in-out ${
          isExpanded ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div
          ref={parentRef}
          className="overflow-auto p-2"
          style={{ height: isExpanded ? '24rem' : '0' }}
        >
          {events.length > 0 ? (
            <div
              style={{
                height: `${virtualizer.getTotalSize()}px`,
                width: '100%',
                position: 'relative',
              }}
            >
              {virtualizer.getVirtualItems().map((virtualItem) => {
                const event = events[virtualItem.index];
                return (
                  <div
                    key={virtualItem.key}
                    data-index={virtualItem.index}
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      height: `${virtualItem.size}px`,
                      transform: `translateY(${virtualItem.start}px)`,
                    }}
                    className="px-2 py-2"
                  >
                    <EventItem
                      event={event}
                      index={virtualItem.index}
                    />
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-8">
              {isAnalyzing ? (
                <div className="space-y-3">
                  <div className="animate-spin inline-block w-6 h-6 border-2 border-gray-300 border-t-blue-600 rounded-full"></div>
                  <p className="text-sm text-gray-500">Initializing analysis...</p>
                </div>
              ) : (
                <div className="space-y-2">
                  <ClipboardList className="w-8 h-8 text-gray-300 mx-auto" />
                  <p className="text-sm text-gray-500">No events yet</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Collapsed state preview */}
      {!isExpanded && latestEventPreview && (
        <div className="px-4 py-3 bg-gray-50 border-t border-gray-100">
          <div className="flex items-center justify-between text-xs text-gray-600">
            <span>
              Latest: {latestEventPreview.text}
            </span>
            <button
              onClick={toggleExpanded}
              className="text-blue-600 hover:text-blue-800 font-medium"
            >
              Show all
            </button>
          </div>
        </div>
      )}
    </div>
  );
});
