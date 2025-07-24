import { Map, Radio, Target, TrendingUp } from 'lucide-react';
import React, { useMemo } from 'react';
import { DataSummaryCard } from './analysis/DataSummaryCard';
import { EventsLog } from './analysis/EventsLog';
import { PhaseProgressBar } from './analysis/PhaseProgressBar';
import { StatsCard } from './analysis/StatsCard';
import { TowerJumpsAlert } from './analysis/TowerJumpsAlert';
import type { AnalysisEvent } from './TowerJumpsAnalyzer';

interface AnalysisResultsProps {
  events: AnalysisEvent[];
  isAnalyzing: boolean;
}

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

// Analysis phases for progress tracking
enum AnalysisPhase {
  LOADING = 'loading',
  PROCESSING = 'processing',
  ANALYZING = 'analyzing',
  COMPLETED = 'completed',
  ERROR = 'error',
}

interface PhaseProgress {
  phase: AnalysisPhase;
  progress: number;
  description: string;
}

export const AnalysisResults = React.memo(function AnalysisResults({ events, isAnalyzing }: AnalysisResultsProps) {
  // Memoize event filtering to avoid repeated calculations
  const eventsByType = useMemo(() => {
    const byType: Record<string, AnalysisEvent[]> = {};
    for (const event of events) {
      if (!byType[event.type]) {
        byType[event.type] = [];
      }
      byType[event.type].push(event);
    }
    return byType;
  }, [events]);

  // Memoize status checks
  const analysisStatus = useMemo(() => ({
    hasError: Boolean(eventsByType[EventType.ERROR]?.length),
    hasCompletion: Boolean(eventsByType[EventType.COMPLETION]?.length),
    hasAnalysisProgress: Boolean(eventsByType[EventType.ANALYSIS_PROGRESS]?.length),
    hasWindowCreation: Boolean(eventsByType[EventType.WINDOW_CREATION]?.length),
    hasProcessing: Boolean(eventsByType[EventType.PROCESSING]?.length),
    hasDataLoading: Boolean(eventsByType[EventType.DATA_LOADING]?.length),
  }), [eventsByType]);

  // Calculate current phase and progress - now more efficient
  const phaseProgress = useMemo((): PhaseProgress => {
    if (!isAnalyzing && events.length === 0) {
      return { phase: AnalysisPhase.LOADING, progress: 0, description: 'Ready to start analysis' };
    }

    if (analysisStatus.hasError) {
      return { phase: AnalysisPhase.ERROR, progress: 0, description: 'Analysis failed' };
    }

    if (analysisStatus.hasCompletion) {
      return { phase: AnalysisPhase.COMPLETED, progress: 100, description: 'Analysis completed successfully' };
    }

    if (analysisStatus.hasAnalysisProgress) {
      const analysisEvents = eventsByType[EventType.ANALYSIS_PROGRESS] || [];
      const latestProgress = analysisEvents[analysisEvents.length - 1];
      const current = latestProgress?.data?.current_window || 0;
      const total = latestProgress?.data?.total_windows || 1;
      const progress = Math.round((current / total) * 100);
      return {
        phase: AnalysisPhase.ANALYZING,
        progress: 60 + (progress * 0.35), // 60-95% range for analysis
        description: `Analyzing window ${current}/${total}`
      };
    }

    if (analysisStatus.hasWindowCreation) {
      return { phase: AnalysisPhase.PROCESSING, progress: 60, description: 'Time windows created' };
    }

    if (analysisStatus.hasProcessing) {
      const processingEvents = eventsByType[EventType.PROCESSING] || [];
      const steps = ['dataframe_conversion', 'distance_calculation', 'anomaly_detection', 'window_creation'];
      const completedSteps = new Set(processingEvents.map(e => e.data?.step).filter(Boolean));
      const progress = (completedSteps.size / steps.length) * 40; // 0-40% range for processing
      return {
        phase: AnalysisPhase.PROCESSING,
        progress: 20 + progress,
        description: `Processing data (${completedSteps.size}/${steps.length} steps)`
      };
    }

    if (analysisStatus.hasDataLoading) {
      return { phase: AnalysisPhase.LOADING, progress: 20, description: 'Data loaded and validated' };
    }

    return { phase: AnalysisPhase.LOADING, progress: 5, description: 'Starting analysis...' };
  }, [events.length, isAnalyzing, analysisStatus, eventsByType]);

  // Memoize derived data for components
  const derivedData = useMemo(() => {
    const dataLoadingEvent = eventsByType[EventType.DATA_LOADING]?.find(e => e.data?.total_records);
    const intervalEvents = eventsByType[EventType.INTERVAL_COMPLETED] || [];
    const towerJumpIntervals = intervalEvents.filter(e => e.data?.is_tower_jump === true);
    const completionEvent = eventsByType[EventType.COMPLETION]?.[0];

    return {
      dataLoadingEvent,
      intervalEvents,
      towerJumpIntervals,
      completionEvent,
    };
  }, [eventsByType]);

  // Empty state
  if (!isAnalyzing && events.length === 0) {
    return (
      <div className="text-center py-12">
        <Radio className="w-16 h-16 text-gray-300 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Ready for Analysis</h3>
        <p className="text-sm text-gray-600 max-w-md mx-auto">
          Upload a CSV file and start analysis to see real-time results and insights here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Phase Progress */}
      <PhaseProgressBar phaseProgress={phaseProgress} isAnalyzing={isAnalyzing} />

      {/* Data Summary */}
      {derivedData.dataLoadingEvent?.data && (
        <DataSummaryCard
          totalRecords={derivedData.dataLoadingEvent.data.total_records}
          recordsWithLocation={derivedData.dataLoadingEvent.data.records_with_location}
        />
      )}

      {/* Tower Jumps Alert */}
      <TowerJumpsAlert
        jumpCount={derivedData.towerJumpIntervals.length}
        totalIntervals={derivedData.intervalEvents.length}
      />

      {/* Stats Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Live Progress Stats */}
        {derivedData.intervalEvents.length > 0 && (
          <StatsCard
            title="Progress Summary"
            icon={TrendingUp}
            stats={[
              { label: 'Intervals', value: derivedData.intervalEvents.length },
              { label: 'Tower Jumps', value: derivedData.towerJumpIntervals.length, color: 'red' },
              {
                label: 'Jump Rate',
                value: `${derivedData.intervalEvents.length > 0 ? ((derivedData.towerJumpIntervals.length / derivedData.intervalEvents.length) * 100).toFixed(1) : 0}%`,
                color: derivedData.towerJumpIntervals.length > 0 ? 'red' : 'green'
              },
            ]}
          />
        )}

        {/* Final Results */}
        {derivedData.completionEvent?.data && (
          <StatsCard
            title="Final Results"
            icon={Target}
            stats={[
              { label: 'Total Intervals', value: derivedData.completionEvent.data.total_intervals },
              {
                label: 'Tower Jumps',
                value: derivedData.completionEvent.data.tower_jumps_detected,
                subtext: `(${derivedData.completionEvent.data.tower_jump_percentage?.toFixed(1)}%)`,
                color: 'red'
              },
              ...(derivedData.completionEvent.data.summary?.most_common_state ? [{
                label: 'Most Common State',
                value: derivedData.completionEvent.data.summary.most_common_state,
                color: 'blue' as const
              }] : []),
              ...(derivedData.completionEvent.data.summary?.average_confidence ? [{
                label: 'Avg Confidence',
                value: `${(derivedData.completionEvent.data.summary.average_confidence * 100).toFixed(1)}%`,
                color: 'default' as const
              }] : [])
            ]}
          />
        )}

        {/* States Observed (if available) */}
        {derivedData.completionEvent?.data?.summary?.states_observed && (
          <div className="md:col-span-2">
            <StatsCard
              title="States Observed"
              icon={Map}
              stats={[
                {
                  label: 'Locations',
                  value: derivedData.completionEvent.data.summary.states_observed.join(', '),
                  color: 'purple'
                }
              ]}
            />
          </div>
        )}
      </div>

      {/* Events Log */}
      <EventsLog events={events} isAnalyzing={isAnalyzing} />
    </div>
  );
});
