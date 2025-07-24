import { zodResolver } from '@hookform/resolvers/zod';
import React, { useEffect, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import type { AnalysisConfig } from './TowerJumpsAnalyzer';
import { Alert, AlertDescription } from './ui/alert';
import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from './ui/form';
import { Input } from './ui/input';

const analysisConfigSchema = z.object({
  time_window_minutes: z
    .number()
    .min(1, 'Time window must be at least 1 minute')
    .max(1440, 'Time window cannot exceed 1440 minutes (24 hours)'),
  max_speed_mph: z
    .number()
    .min(0, 'Speed must be non-negative')
    .max(200, 'Speed cannot exceed 200 mph'),
  confidence_threshold: z
    .number()
    .min(0, 'Confidence must be at least 0')
    .max(1, 'Confidence cannot exceed 1'),
});

type AnalysisConfigForm = z.infer<typeof analysisConfigSchema>;

interface UploadFormProps {
  onAnalyze: (file: File, config: AnalysisConfig) => void;
  isAnalyzing: boolean;
  onReset: () => void;
}

export function UploadForm({ onAnalyze, isAnalyzing, onReset }: UploadFormProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [isClient, setIsClient] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const form = useForm<AnalysisConfigForm>({
    resolver: zodResolver(analysisConfigSchema),
    defaultValues: {
      time_window_minutes: 15,
      max_speed_mph: 80.0,
      confidence_threshold: 0.5,
    },
  });

  useEffect(() => {
    setIsClient(true);
  }, []);

  const handleFileSelect = (file: File) => {
    setFileError(null);

    // Validate file type
    if (file.type !== 'text/csv' && !file.name.endsWith('.csv')) {
      setFileError('Please select a CSV file');
      return;
    }

    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
      setFileError('File size must be less than 50MB');
      return;
    }

    setSelectedFile(file);
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const onSubmit = (data: AnalysisConfigForm) => {
    if (!selectedFile) {
      setFileError('Please select a CSV file');
      return;
    }
    onAnalyze(selectedFile, data);
  };

  const handleReset = () => {
    setSelectedFile(null);
    setFileError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    form.reset();
    onReset();
  };

  const isButtonDisabled = !isClient || !selectedFile || isAnalyzing || !!fileError;

  return (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          CSV File Upload
        </label>
        <div
          className={`relative border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
            dragActive
              ? 'border-blue-400 bg-blue-50'
              : fileError
              ? 'border-red-400 bg-red-50'
              : 'border-gray-300 hover:border-gray-400'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleFileInputChange}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            disabled={isAnalyzing}
          />
          <div className="space-y-2">
            <div className="text-gray-600">
              {selectedFile ? (
                <div className="text-green-600">
                  <strong>Selected:</strong> {selectedFile.name}
                  <br />
                  <span className="text-sm text-gray-500">
                    Size: {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </span>
                </div>
              ) : (
                <>
                  <p>Drag and drop your CSV file here, or click to browse</p>
                  <p className="text-sm text-gray-500">
                    File must contain carrier data with location and time information
                  </p>
                </>
              )}
            </div>
          </div>
        </div>

        {fileError && (
          <Alert variant="destructive" className="mt-2">
            <AlertDescription>{fileError}</AlertDescription>
          </Alert>
        )}
      </div>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Analysis Configuration</CardTitle>
              <CardDescription>
                Adjust parameters for tower jump detection
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <FormField
                control={form.control}
                name="time_window_minutes"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Time Window (minutes)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        placeholder="60"
                        {...field}
                        onChange={(e) => field.onChange(parseInt(e.target.value) || 60)}
                        disabled={isAnalyzing}
                      />
                    </FormControl>
                    <FormDescription>
                      Time window for analyzing location changes (1-1440 minutes)
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="max_speed_mph"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Maximum Speed (mph)</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        step="0.1"
                        placeholder="70.0"
                        {...field}
                        onChange={(e) => field.onChange(parseFloat(e.target.value) || 70.0)}
                        disabled={isAnalyzing}
                      />
                    </FormControl>
                    <FormDescription>
                      Maximum reasonable travel speed (0-200 mph)
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="confidence_threshold"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Confidence Threshold</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        step="0.01"
                        placeholder="0.5"
                        {...field}
                        onChange={(e) => field.onChange(parseFloat(e.target.value) || 0.5)}
                        disabled={isAnalyzing}
                      />
                    </FormControl>
                    <FormDescription>
                      Minimum confidence for tower jump detection (0.0-1.0)
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <div className="flex gap-4">
            <Button
              type="submit"
              disabled={isButtonDisabled}
              className="flex-1"
            >
              {isAnalyzing ? 'Analyzing...' : 'Start Analysis'}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={handleReset}
              disabled={isAnalyzing}
            >
              Reset
            </Button>
          </div>
        </form>
      </Form>

      {selectedFile && isClient && !fileError && (
        <Alert>
          <AlertDescription>
            Ready to analyze <strong>{selectedFile.name}</strong> with the configured parameters.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
