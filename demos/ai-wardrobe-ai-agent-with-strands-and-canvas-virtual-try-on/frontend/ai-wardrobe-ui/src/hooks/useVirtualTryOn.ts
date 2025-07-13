import { useCallback, useRef } from 'react';
import toast from 'react-hot-toast';

interface VirtualTryOnResult {
  tryOnImageUrl: string;
  outfitData: any;
}

interface UseVirtualTryOnProps {
  onTryOnResult?: (tryOnImageUrl: string, outfitData: any, source: string) => void;
}

export function useVirtualTryOn({ onTryOnResult }: UseVirtualTryOnProps) {
  const loadingToastRef = useRef<string | null>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const startLoading = useCallback(() => {
    // Clear any existing loading state
    if (loadingToastRef.current) {
      toast.dismiss(loadingToastRef.current);
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    console.log('🦄 Starting virtual try-on loading...');
    loadingToastRef.current = toast.loading('🦄 Creating magical virtual try-on...', {
      duration: 0, // Don't auto-dismiss
    });

    // Safety timeout: auto-dismiss after 2 minutes
    timeoutRef.current = setTimeout(() => {
      console.log('⏰ Virtual try-on loading timeout - auto-dismissing');
      stopLoading();
      toast.error('Virtual try-on took too long. Please try again.');
    }, 120000); // 2 minutes

    return loadingToastRef.current;
  }, []);

  const stopLoading = useCallback((showSuccess = false) => {
    console.log('✅ Stopping virtual try-on loading...', { showSuccess });
    
    if (loadingToastRef.current) {
      toast.dismiss(loadingToastRef.current);
      loadingToastRef.current = null;
    }
    
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }

    if (showSuccess) {
      toast.success('✨ Virtual try-on complete!', { duration: 3000 });
    }
  }, []);

  const handleTryOnResult = useCallback((result: VirtualTryOnResult) => {
    console.log('🎯 Virtual try-on result received:', result);
    
    // Always stop loading first
    stopLoading(true);
    
    // Call the parent handler
    if (onTryOnResult && result.tryOnImageUrl) {
      console.log('📤 Calling onTryOnResult with chat source');
      onTryOnResult(result.tryOnImageUrl, result.outfitData || {}, 'chat');
    }
  }, [onTryOnResult, stopLoading]);

  const handleError = useCallback((error: string) => {
    console.error('❌ Virtual try-on error:', error);
    stopLoading();
    toast.error(`Virtual try-on failed: ${error}`);
  }, [stopLoading]);

  const cleanup = useCallback(() => {
    if (loadingToastRef.current) {
      toast.dismiss(loadingToastRef.current);
      loadingToastRef.current = null;
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  return {
    startLoading,
    stopLoading,
    handleTryOnResult,
    handleError,
    cleanup,
    isLoading: () => loadingToastRef.current !== null
  };
}