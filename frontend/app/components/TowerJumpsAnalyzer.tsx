import { useAnalysis } from '../hooks/useAnalysis';
import { AnalysisResults } from './AnalysisResults';
import { HealthCheck } from './HealthCheck';
import { Alert, AlertDescription } from './ui/alert';
import { Badge } from './ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { UploadForm } from './UploadForm';

export interface AnalysisConfig {
  time_window_minutes: number;
  max_speed_mph: number;
  confidence_threshold: number;
}

export interface AnalysisEvent {
  type: string;
  timestamp: string;
  message: string;
  data?: any;
}

export function TowerJumpsAnalyzer() {
  const { isAnalyzing, events, error, startAnalysis, resetAnalysis } = useAnalysis();

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="container mx-auto max-w-6xl">
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            🗼 Tower Jumps Analysis
          </h1>
          <p className="text-lg text-gray-600">
            Analyze mobile carrier data to detect tower jumps with real-time streaming
          </p>
          <div className="mt-4">
            <HealthCheck />
          </div>
        </div>

        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <Card>
              <CardHeader>
                <CardTitle>Upload & Configure</CardTitle>
                <CardDescription>
                  Upload a CSV file containing carrier data and configure analysis parameters
                </CardDescription>
              </CardHeader>
              <CardContent>
                <UploadForm
                  onAnalyze={startAnalysis}
                  isAnalyzing={isAnalyzing}
                  onReset={resetAnalysis}
                />
              </CardContent>
            </Card>
          </div>

          <div>
            <Card className="h-fit">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  Analysis Results
                  {isAnalyzing && (
                    <Badge variant="secondary" className="animate-pulse">
                      Processing...
                    </Badge>
                  )}
                </CardTitle>
                <CardDescription>
                  Real-time analysis progress and results
                </CardDescription>
              </CardHeader>
              <CardContent>
                <AnalysisResults
                  events={events}
                  isAnalyzing={isAnalyzing}
                />
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
