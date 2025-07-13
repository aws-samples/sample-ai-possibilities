import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, X, Sparkles, RotateCcw, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';

interface OutfitItem {
  itemId: string;
  name: string;
  imageUrl: string;
}

interface ModernOutfitBuilderProps {
  outfit: {
    top?: OutfitItem;
    bottom?: OutfitItem;
    dress?: OutfitItem;
    outerwear?: OutfitItem;
    shoes?: OutfitItem;
    accessory?: OutfitItem;
  };
  isBuilderMode: boolean;
  onRemoveItem: (category: string) => void;
  onApplyOutfit: () => void;
  onClearOutfit: () => void;
  onToggleMode: () => void;
  isApplying?: boolean;
}

const categoryConfig = {
  top: { name: 'Top', color: '#6366f1' },
  bottom: { name: 'Bottom', color: '#8b5cf6' },
  dress: { name: 'Dress', color: '#ec4899' },
  outerwear: { name: 'Outerwear', color: '#f59e0b' },
  shoes: { name: 'Shoes', color: '#10b981' },
  accessory: { name: 'Accessory', color: '#3b82f6' },
};

export const ModernOutfitBuilder: React.FC<ModernOutfitBuilderProps> = ({
  outfit,
  isBuilderMode,
  onRemoveItem,
  onApplyOutfit,
  onClearOutfit,
  onToggleMode,
  isApplying = false,
}) => {
  const outfitCount = Object.keys(outfit).length;
  const hasConflict = !!(outfit.dress && (outfit.top || outfit.bottom));

  return (
    <motion.div
      className="outfit-builder-modern"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      {/* Header */}
      <div 
        className="p-6 cursor-pointer hover:bg-blue-50 transition-all duration-300 border-b-2 border-transparent hover:border-blue-200"
        onClick={() => {
          console.log('Outfit Builder clicked, current isBuilderMode:', isBuilderMode);
          onToggleMode();
        }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="fashion-icon-container">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <h2 className="fashion-section-title text-2xl">
                  Outfit Builder
                </h2>
                <div className="px-3 py-1 bg-gradient-to-r from-indigo-500 to-purple-500 text-white text-xs font-bold rounded-full animate-pulse">
                  START HERE
                </div>
                {outfitCount > 0 && (
                  <span className="ml-2 text-sm font-normal text-green-600 bg-green-100 px-2 py-1 rounded-full">
                    {outfitCount} item{outfitCount !== 1 ? 's' : ''} selected
                  </span>
                )}
              </div>
              <p className="fashion-section-subtitle text-base font-medium">
                {isBuilderMode 
                  ? 'Perfect! Now click wardrobe items below to build your complete look'
                  : 'Click here to start building complete outfits • Try on multiple items together!'
                }
              </p>
            </div>
          </div>
          <motion.div
            animate={{ rotate: isBuilderMode ? 180 : 0 }}
            className="text-fashion-secondary"
          >
            <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M6 9l6 6 6-6" />
            </svg>
          </motion.div>
        </div>
      </div>

      <AnimatePresence>
        {isBuilderMode && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div className="p-6 pt-0">
              {/* Action Buttons */}
              <div className="flex gap-3 mb-6">
                <button
                  onClick={onApplyOutfit}
                  disabled={outfitCount === 0 || isApplying || hasConflict}
                  className="btn-fashion-primary flex-1 flex items-center justify-center gap-2"
                >
                  {isApplying ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Creating Your Look...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-5 h-5" />
                      <span>Try On Complete Outfit</span>
                    </>
                  )}
                </button>
                <button
                  onClick={onClearOutfit}
                  disabled={outfitCount === 0}
                  className="btn-fashion-secondary px-4"
                  title="Clear all items"
                >
                  <RotateCcw className="w-5 h-5" />
                </button>
              </div>

              {/* Conflict Warning */}
              {hasConflict && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6 flex items-start gap-3"
                >
                  <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-amber-800">
                    <p className="font-medium">Outfit Conflict Detected</p>
                    <p className="mt-1">You can't wear a dress with separate top/bottom pieces. Remove conflicting items to continue.</p>
                  </div>
                </motion.div>
              )}

              {/* Outfit Grid */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {Object.entries(categoryConfig).map(([category, config]) => {
                  const item = outfit[category as keyof typeof outfit];
                  const isConflicting = hasConflict && 
                    ((category === 'dress' && (outfit.top || outfit.bottom)) ||
                     ((category === 'top' || category === 'bottom') && outfit.dress));

                  return (
                    <motion.div
                      key={category}
                      initial={{ scale: 0.9, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      whileHover={{ scale: 1.02 }}
                      className={`fashion-card p-4 ${isConflicting ? 'ring-2 ring-red-400' : ''}`}
                    >
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <div 
                            className="w-4 h-4 rounded-full"
                            style={{ backgroundColor: config.color }}
                          ></div>
                          <span className="font-medium text-fashion-charcoal">
                            {config.name}
                          </span>
                        </div>
                        {item && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onRemoveItem(category);
                            }}
                            className="text-red-500 hover:bg-red-50 rounded-full p-1 transition-colors"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                      
                      {item ? (
                        <div className="relative group">
                          <img
                            src={item.imageUrl}
                            alt={item.name}
                            className="w-full h-32 object-cover rounded-lg"
                          />
                          {isConflicting && (
                            <div className="absolute inset-0 bg-red-500/20 rounded-lg flex items-center justify-center">
                              <span className="bg-red-500 text-white text-xs px-2 py-1 rounded">
                                Conflict
                              </span>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div 
                          className="w-full h-32 bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg flex flex-col items-center justify-center text-gray-400 border-2 border-dashed border-gray-200"
                          style={{ borderColor: config.color + '30' }}
                        >
                          <Plus className="w-8 h-8 mb-1" />
                          <span className="text-xs">Add {config.name}</span>
                        </div>
                      )}
                    </motion.div>
                  );
                })}
              </div>

              {/* Helper Text */}
              <div className="mt-6 p-4 bg-gradient-to-r from-fashion-secondary/10 to-fashion-accent/10 rounded-lg">
                <p className="text-sm text-fashion-charcoal flex items-start gap-2">
                  <Sparkles className="w-4 h-4 text-fashion-secondary flex-shrink-0 mt-0.5" />
                  <span>
                    <strong>Pro Tip:</strong> Our AI will style your complete outfit perfectly. 
                    Mix and match items to create your unique look!
                  </span>
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};