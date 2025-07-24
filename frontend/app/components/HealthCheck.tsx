import { CheckCircle, Loader2, XCircle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { config, endpoints } from '../lib/config';
import { Badge } from './ui/badge';

export function HealthCheck() {
  const [status, setStatus] = useState<'checking' | 'healthy' | 'error'>('checking');
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const checkHealth = async () => {
    try {
      setStatus('checking');
      const response = await fetch(endpoints.health, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        if (data.status === 'healthy') {
          setStatus('healthy');
        } else {
          setStatus('error');
        }
      } else {
        setStatus('error');
      }
    } catch (error) {
      console.warn('Health check failed:', error);
      setStatus('error');
    } finally {
      setLastChecked(new Date());
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, config.healthCheckInterval);
    return () => clearInterval(interval);
  }, []);

  const getStatusBadge = () => {
    switch (status) {
      case 'checking':
        return (
          <Badge variant="outline" className="animate-pulse">
            <Loader2 className="w-3 h-3 mr-1 animate-spin" />
            Checking...
          </Badge>
        );
      case 'healthy':
        return (
          <Badge variant="default" className="bg-green-100 text-green-800 border-green-300">
            <CheckCircle className="w-3 h-3 mr-1" />
            API Healthy
          </Badge>
        );
      case 'error':
        return (
          <Badge variant="destructive">
            <XCircle className="w-3 h-3 mr-1" />
            API Offline
          </Badge>
        );
      default:
        return null;
    }
  };

  return (
    <div className="flex items-center gap-2">
      {getStatusBadge()}
      {lastChecked && (
        <span className="text-xs text-gray-500">
          Last checked: {lastChecked.toLocaleTimeString()}
        </span>
      )}
      {status === 'error' && (
        <button
          onClick={checkHealth}
          className="text-xs text-blue-600 hover:text-blue-800 underline"
        >
          Retry
        </button>
      )}
    </div>
  );
}
