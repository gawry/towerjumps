import { createEventSource } from 'eventsource-client';
import { useCallback, useEffect, useRef, useState } from 'react';
import type { AnalysisConfig, AnalysisEvent } from '../components/TowerJumpsAnalyzer';
import { endpoints } from '../lib/config';

interface UseAnalysisReturn {
  isAnalyzing: boolean;
  events: AnalysisEvent[];
  error: string | null;
  startAnalysis: (file: File, config: AnalysisConfig) => Promise<void>;
  resetAnalysis: () => void;
}

export function useAnalysis(): UseAnalysisReturn {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [events, setEvents] = useState<AnalysisEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<ReturnType<typeof createEventSource> | null>(null);
  const isConnectingRef = useRef(false);

  // Event batching for better performance
  const pendingEventsRef = useRef<AnalysisEvent[]>([]);
  const batchTimeoutRef = useRef<number | null>(null);
  const rafRef = useRef<number | null>(null);

  // Batch events to reduce re-renders and improve performance
  const flushEvents = useCallback(() => {
    if (pendingEventsRef.current.length === 0) return;

    const newEvents = [...pendingEventsRef.current];
    pendingEventsRef.current = [];

    setEvents(prev => [...prev, ...newEvents]);

    // Clear any pending timeouts/rafs
    if (batchTimeoutRef.current) {
      clearTimeout(batchTimeoutRef.current);
      batchTimeoutRef.current = null;
    }
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
  }, []);

  // Schedule event flushing
  const scheduleBatchFlush = useCallback(() => {
    // For rapid updates, use requestAnimationFrame
    if (!rafRef.current) {
      rafRef.current = requestAnimationFrame(() => {
        rafRef.current = null;
        flushEvents();
      });
    }

    // Fallback timeout in case raf doesn't fire
    if (batchTimeoutRef.current) {
      clearTimeout(batchTimeoutRef.current);
    }
    batchTimeoutRef.current = window.setTimeout(() => {
      batchTimeoutRef.current = null;
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      flushEvents();
    }, 50); // Max 50ms delay
  }, [flushEvents]);

  // Add event to batch
  const addEvent = useCallback((event: AnalysisEvent) => {
    pendingEventsRef.current.push(event);
    scheduleBatchFlush();
  }, [scheduleBatchFlush]);

  // Cleanup function to properly close connections
  const cleanup = useCallback(() => {
    if (eventSourceRef.current) {
      try {
        eventSourceRef.current.close();
      } catch (e) {
        console.warn('Error closing EventSource:', e);
      }
      eventSourceRef.current = null;
    }
    isConnectingRef.current = false;

    // Clear any pending batches
    if (batchTimeoutRef.current) {
      clearTimeout(batchTimeoutRef.current);
      batchTimeoutRef.current = null;
    }
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }

    // Flush any remaining events
    flushEvents();
  }, [flushEvents]);

  // Reset analysis state
  const resetAnalysis = useCallback(() => {
    cleanup();
    pendingEventsRef.current = [];
    setEvents([]);
    setError(null);
    setIsAnalyzing(false);
  }, [cleanup]);

  // Cleanup on component unmount
  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  const startAnalysis = useCallback(async (file: File, analysisConfig: AnalysisConfig) => {
    // Prevent multiple simultaneous connections
    if (isConnectingRef.current || eventSourceRef.current) {
      console.warn('Analysis already in progress, ignoring duplicate request');
      return;
    }

    // Reset state
    pendingEventsRef.current = [];
    setEvents([]);
    setError(null);
    setIsAnalyzing(true);
    isConnectingRef.current = true;

    try {
      // Prepare form data
      const formData = new FormData();
      formData.append('file', file);
      formData.append('time_window_minutes', analysisConfig.time_window_minutes.toString());
      formData.append('max_speed_mph', analysisConfig.max_speed_mph.toString());
      formData.append('confidence_threshold', analysisConfig.confidence_threshold.toString());

      console.log('Starting EventSource connection to:', endpoints.analyze);

      // Create EventSource with POST request
      const eventSource = createEventSource({
        url: endpoints.analyze,
        method: 'POST',
        body: formData,
        onMessage: ({ data }) => {
          try {
            const eventData: AnalysisEvent = JSON.parse(data);
            console.log('Received SSE event:', eventData.type, eventData.message);

            // Use batched event adding instead of immediate setState
            addEvent(eventData);

            // Handle error events
            if (eventData.type === 'error') {
              setError(eventData.message);
              setIsAnalyzing(false);
              cleanup();
            }

            // Handle completion
            if (eventData.type === 'completion') {
              console.log('Analysis completed, closing connection');
              setIsAnalyzing(false);
              // Small delay to ensure final events are processed
              setTimeout(() => {
                cleanup();
              }, 500);
            }
          } catch (parseError) {
            console.warn('Failed to parse SSE data:', parseError);
            setError('Failed to parse server response');
          }
        },
      });

      // Store the EventSource reference
      eventSourceRef.current = eventSource;
      isConnectingRef.current = false;

      console.log('EventSource connection established');

    } catch (err) {
      console.error('Failed to start analysis:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to start analysis';
      setError(errorMessage);
      setIsAnalyzing(false);
      cleanup();
    }
  }, [cleanup, addEvent]);

  return {
    isAnalyzing,
    events,
    error,
    startAnalysis,
    resetAnalysis,
  };
}
