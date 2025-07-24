import { CheckCircle, Clock, Search, Settings, XCircle } from 'lucide-react';
import React from 'react';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';

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

interface PhaseProgressBarProps {
  phaseProgress: PhaseProgress;
  isAnalyzing: boolean;
}

export const PhaseProgressBar = React.memo(function PhaseProgressBar({ phaseProgress, isAnalyzing }: PhaseProgressBarProps) {
  const getPhaseColor = (phase: AnalysisPhase) => {
    switch (phase) {
      case AnalysisPhase.LOADING:
        return 'text-blue-600';
      case AnalysisPhase.PROCESSING:
        return 'text-amber-600';
      case AnalysisPhase.ANALYZING:
        return 'text-purple-600';
      case AnalysisPhase.COMPLETED:
        return 'text-green-600';
      case AnalysisPhase.ERROR:
        return 'text-red-600';
      default:
        return 'text-gray-500';
    }
  };

  const getPhaseIcon = (phase: AnalysisPhase) => {
    const iconProps = { className: "w-4 h-4" };
    switch (phase) {
      case AnalysisPhase.LOADING:
        return <Clock {...iconProps} />;
      case AnalysisPhase.PROCESSING:
        return <Settings {...iconProps} />;
      case AnalysisPhase.ANALYZING:
        return <Search {...iconProps} />;
      case AnalysisPhase.COMPLETED:
        return <CheckCircle {...iconProps} />;
      case AnalysisPhase.ERROR:
        return <XCircle {...iconProps} />;
      default:
        return <Clock {...iconProps} />;
    }
  };

  const phases = [
    { key: AnalysisPhase.LOADING, label: 'Loading', range: '0-20%' },
    { key: AnalysisPhase.PROCESSING, label: 'Processing', range: '20-60%' },
    { key: AnalysisPhase.ANALYZING, label: 'Analyzing', range: '60-95%' },
    { key: AnalysisPhase.COMPLETED, label: 'Complete', range: '100%' },
  ];

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={getPhaseColor(phaseProgress.phase)}>
            {getPhaseIcon(phaseProgress.phase)}
          </span>
          <span className={`text-sm font-medium ${getPhaseColor(phaseProgress.phase)}`}>
            {phaseProgress.description}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {isAnalyzing && (
            <Badge variant="secondary" className="text-xs animate-pulse">
              Processing
            </Badge>
          )}
          <span className="text-xs text-gray-500 font-mono">
            {Math.round(phaseProgress.progress)}%
          </span>
        </div>
      </div>

      <Progress
        value={phaseProgress.progress}
        className="h-1.5 mb-3"
      />

      <div className="flex justify-between text-xs">
        {phases.map((phase) => (
          <div
            key={phase.key}
            className={`flex flex-col items-center gap-1 ${
              phaseProgress.phase === phase.key
                ? getPhaseColor(phaseProgress.phase)
                : 'text-gray-400'
            }`}
          >
            <span className="font-medium">{phase.label}</span>
            <span className="text-gray-400">{phase.range}</span>
          </div>
        ))}
      </div>
    </div>
  );
});
