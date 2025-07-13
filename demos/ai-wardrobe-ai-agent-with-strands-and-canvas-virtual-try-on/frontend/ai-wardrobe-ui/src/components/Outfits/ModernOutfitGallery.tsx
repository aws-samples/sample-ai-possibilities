import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, Archive, Calendar, Eye, Heart, Trash2 } from 'lucide-react';
import { User, Outfit } from '../../types';
import { getOutfits, deleteOutfit } from '../../services/api';
import toast from 'react-hot-toast';

interface ModernOutfitGalleryProps {
  user: User;
  shouldExpand?: boolean;
  newOutfitId?: string | null;
  onExpanded?: () => void;
}

export const ModernOutfitGallery: React.FC<ModernOutfitGalleryProps> = ({ 
  user, 
  shouldExpand = false, 
  newOutfitId = null, 
  onExpanded 
}) => {
  const [outfits, setOutfits] = useState<Outfit[]>([]);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [highlightedOutfitId, setHighlightedOutfitId] = useState<string | null>(null);
  const archiveRef = useRef<HTMLDivElement>(null);

  const loadOutfits = async () => {
    setIsLoading(true);
    try {
      const response = await getOutfits(user.userId);
      console.log('Outfits API response:', response);
      if (response.success && response.data) {
        console.log('Loaded outfits:', response.data);
        setOutfits(response.data);
      }
    } catch (error) {
      console.error('Error loading outfits:', error);
      toast.error('Failed to load outfit archive');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteOutfit = async (outfitId: string, event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent any parent click handlers
    
    // Show confirmation
    if (!window.confirm('Are you sure you want to delete this outfit? This action cannot be undone.')) {
      return;
    }

    try {
      const response = await deleteOutfit(user.userId, outfitId);
      if (response.success) {
        toast.success('Outfit deleted successfully');
        // Remove from local state
        setOutfits(prev => prev.filter(outfit => outfit.outfitId !== outfitId));
      } else {
        toast.error('Failed to delete outfit');
      }
    } catch (error) {
      console.error('Error deleting outfit:', error);
      toast.error('Failed to delete outfit');
    }
  };

  useEffect(() => {
    if (isExpanded) {
      loadOutfits();
    }
  }, [isExpanded, user.userId]);

  // Handle auto-expansion from parent
  useEffect(() => {
    if (shouldExpand && !isExpanded) {
      console.log('Auto-expanding Outfit Archive due to new multi-item outfit');
      setIsExpanded(true);
      
      // Scroll to archive section with a slight delay
      setTimeout(() => {
        archiveRef.current?.scrollIntoView({ 
          behavior: 'smooth', 
          block: 'start' 
        });
      }, 300);
      
      // Notify parent that expansion is complete
      setTimeout(() => {
        onExpanded?.();
      }, 600);
    }
  }, [shouldExpand, isExpanded, onExpanded]);

  // Handle highlighting new outfit
  useEffect(() => {
    if (newOutfitId && isExpanded) {
      console.log('Highlighting new outfit:', newOutfitId);
      setHighlightedOutfitId(newOutfitId);
      
      // Remove highlight after 3 seconds
      setTimeout(() => {
        setHighlightedOutfitId(null);
      }, 3000);
    }
  }, [newOutfitId, isExpanded]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <motion.div
      ref={archiveRef}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="fashion-card overflow-hidden"
    >
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-6 hover:bg-fashion-light-gray transition-colors"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="fashion-icon-container">
              <Archive className="w-6 h-6 text-white" />
            </div>
            <div className="text-left">
              <h2 className="fashion-section-title">Outfit Archive</h2>
              <p className="fashion-section-subtitle">
                {outfits.length} saved looks • Your fashion history
              </p>
            </div>
          </div>
          <motion.div
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.3 }}
            className="text-fashion-secondary"
          >
            <ChevronDown className="w-6 h-6" />
          </motion.div>
        </div>
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="p-6 pt-0">
              {isLoading ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <div className="w-8 h-8 border-4 border-fashion-secondary border-t-transparent rounded-full animate-spin mb-4"></div>
                  <p className="text-fashion-medium-gray">Loading your outfits...</p>
                </div>
              ) : outfits.length === 0 ? (
                <div className="text-center py-12">
                  <Archive className="w-16 h-16 text-fashion-light-gray mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-fashion-dark-gray mb-2">
                    No saved outfits yet
                  </h3>
                  <p className="text-fashion-medium-gray">
                    Try on some clothes and save your favorite looks!
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <AnimatePresence>
                    {outfits.map((outfit, index) => (
                      <motion.div
                        key={outfit.outfitId}
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ 
                          opacity: 1, 
                          scale: highlightedOutfitId === outfit.outfitId ? 1.05 : 1,
                        }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        transition={{ 
                          delay: index * 0.05,
                          scale: { duration: 0.3 }
                        }}
                        className={`group relative bg-fashion-white rounded-lg overflow-hidden shadow-sm hover:shadow-lg transition-all duration-300 border ${
                          highlightedOutfitId === outfit.outfitId 
                            ? 'border-fashion-secondary shadow-lg ring-2 ring-fashion-secondary/20' 
                            : 'border-fashion-gray'
                        }`}
                      >
                        {/* Outfit Image */}
                        <div className="relative aspect-[3/4] overflow-hidden bg-fashion-light-gray">
                          {(() => {
                            console.log('Outfit image URLs:', { tryOnImageUrl: outfit.tryOnImageUrl, tryOnPresignedUrl: outfit.tryOnPresignedUrl });
                            return (outfit.tryOnPresignedUrl || outfit.tryOnImageUrl) ? (
                              <img
                                src={outfit.tryOnPresignedUrl || outfit.tryOnImageUrl}
                                alt={`Outfit ${index + 1}`}
                                className="w-full h-full object-cover transition-transform group-hover:scale-105"
                                onError={(e) => {
                                  console.log('Image failed to load:', e.currentTarget.src);
                                  e.currentTarget.style.display = 'none';
                                  e.currentTarget.nextElementSibling?.classList.remove('hidden');
                                }}
                              />
                            ) : (
                              <div className="absolute inset-0 flex items-center justify-center bg-fashion-light-gray">
                                <div className="text-center">
                                  <Archive className="w-12 h-12 text-fashion-medium-gray mx-auto mb-2" />
                                  <p className="text-sm text-fashion-medium-gray">Image Unavailable</p>
                                </div>
                              </div>
                            );
                          })()}
                          
                          {/* Overlay on hover */}
                          <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                            <button className="bg-fashion-white/20 backdrop-blur-sm text-white p-2 rounded-full hover:bg-fashion-white/30 transition-colors">
                              <Eye className="w-5 h-5" />
                            </button>
                            <button className="bg-fashion-white/20 backdrop-blur-sm text-white p-2 rounded-full hover:bg-fashion-white/30 transition-colors">
                              <Heart className="w-5 h-5" />
                            </button>
                            <button 
                              onClick={(e) => handleDeleteOutfit(outfit.outfitId, e)}
                              className="bg-fashion-accent/80 backdrop-blur-sm text-white p-2 rounded-full hover:bg-fashion-accent transition-colors"
                              title="Delete outfit"
                            >
                              <Trash2 className="w-5 h-5" />
                            </button>
                          </div>

                          {/* Item count badge */}
                          <div className={`absolute top-3 left-3 backdrop-blur-sm text-white px-2 py-1 rounded-full text-xs font-medium ${
                            highlightedOutfitId === outfit.outfitId
                              ? 'bg-fashion-secondary/90 animate-pulse'
                              : 'bg-fashion-primary/80'
                          }`}>
                            {outfit.items?.length || 1} item{(outfit.items?.length || 1) !== 1 ? 's' : ''}
                          </div>
                          
                          {/* New outfit indicator */}
                          {highlightedOutfitId === outfit.outfitId && (
                            <motion.div
                              initial={{ scale: 0, opacity: 0 }}
                              animate={{ scale: 1, opacity: 1 }}
                              exit={{ scale: 0, opacity: 0 }}
                              className="absolute top-3 right-3 bg-green-500 text-white px-2 py-1 rounded-full text-xs font-bold"
                            >
                              NEW!
                            </motion.div>
                          )}
                        </div>

                        {/* Outfit Info */}
                        <div className="p-4">
                          <div className="flex items-center justify-between mb-2">
                            <h3 className="font-medium text-fashion-charcoal truncate">
                              {outfit.occasion === 'virtual_try_on' 
                                ? 'Virtual Try-On Look'
                                : outfit.occasion === 'custom_outfit'
                                ? 'Custom Outfit'
                                : outfit.occasion || 'Saved Look'
                              }
                            </h3>
                            <span className="text-xs text-fashion-medium-gray">
                              #{index + 1}
                            </span>
                          </div>
                          
                          <div className="flex items-center gap-1 text-xs text-fashion-medium-gray mb-3">
                            <Calendar className="w-3 h-3" />
                            <span>{formatDate(outfit.createdAt || '')}</span>
                          </div>

                          {/* Outfit tags */}
                          <div className="flex flex-wrap gap-1">
                            <span className="px-2 py-1 text-xs bg-fashion-light-gray text-fashion-dark-gray rounded-full">
                              {outfit.occasion}
                            </span>
                            {outfit.notes && (
                              <span className="px-2 py-1 text-xs bg-fashion-secondary/10 text-fashion-secondary rounded-full">
                                Notes
                              </span>
                            )}
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </AnimatePresence>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};