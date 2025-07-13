import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shirt, X, Sparkles, Save, RotateCcw } from 'lucide-react';
import toast from 'react-hot-toast';

interface OutfitItem {
  itemId: string;
  name: string;
  imageUrl: string;
}

interface OutfitBuilderProps {
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
  top: { name: 'Top', icon: '👕', order: 1 },
  bottom: { name: 'Bottom', icon: '👖', order: 2 },
  dress: { name: 'Dress', icon: '👗', order: 3 },
  outerwear: { name: 'Outerwear', icon: '🧥', order: 4 },
  shoes: { name: 'Shoes', icon: '👟', order: 5 },
  accessory: { name: 'Accessory', icon: '👜', order: 6 },
};

export const OutfitBuilder: React.FC<OutfitBuilderProps> = ({
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
    <div className="wardrobe-door rounded-xl overflow-hidden mb-6">
      <button
        onClick={onToggleMode}
        className="w-full wood-panel p-4 hover:bg-opacity-90 transition-all text-left"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <div className="hanger-hook scale-50 mr-2"></div>
            <div>
              <h3 className="text-lg font-bold text-white">
                Outfit Builder
              </h3>
              <p className="text-sm text-gray-300">
                {isBuilderMode 
                  ? `${outfitCount} item${outfitCount !== 1 ? 's' : ''} selected`
                  : 'Click to start building an outfit'
                }
              </p>
            </div>
          </div>
          <motion.div
            animate={{ rotate: isBuilderMode ? 180 : 0 }}
            transition={{ duration: 0.3 }}
            className="text-white"
          >
            <Sparkles className="w-5 h-5" />
          </motion.div>
        </div>
      </button>

      <AnimatePresence>
        {isBuilderMode && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="closet-interior p-4">
              {/* Action Buttons */}
              <div className="flex justify-between mb-4">
                <div className="flex gap-2">
                  <button
                    onClick={onApplyOutfit}
                    disabled={outfitCount === 0 || isApplying || hasConflict}
                    className="px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {isApplying ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Applying...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4" />
                        Try On Outfit
                      </>
                    )}
                  </button>
                  <button
                    onClick={onClearOutfit}
                    disabled={outfitCount === 0}
                    className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    <RotateCcw className="w-4 h-4" />
                    Clear All
                  </button>
                </div>
              </div>

              {/* Conflict Warning */}
              {hasConflict && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4"
                >
                  <p className="text-sm text-yellow-700">
                    ⚠️ You can't wear a dress with separate top/bottom pieces. Please remove conflicting items.
                  </p>
                </motion.div>
              )}

              {/* Outfit Slots */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {Object.entries(categoryConfig)
                  .sort(([, a], [, b]) => a.order - b.order)
                  .map(([category, config]) => {
                    const item = outfit[category as keyof typeof outfit];
                    const isConflicting = hasConflict && 
                      ((category === 'dress' && (outfit.top || outfit.bottom)) ||
                       ((category === 'top' || category === 'bottom') && outfit.dress));

                    return (
                      <motion.div
                        key={category}
                        initial={{ scale: 0.9, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        transition={{ delay: config.order * 0.05 }}
                        className={`relative bg-white rounded-lg shadow-md overflow-hidden ${
                          isConflicting ? 'ring-2 ring-red-400' : ''
                        }`}
                      >
                        <div className="p-3">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-sm font-medium text-gray-700">
                              {config.icon} {config.name}
                            </span>
                            {item && (
                              <button
                                onClick={() => onRemoveItem(category)}
                                className="text-red-500 hover:text-red-700 transition-colors"
                              >
                                <X className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                          
                          {item ? (
                            <div className="relative">
                              <img
                                src={item.imageUrl}
                                alt={item.name}
                                className="w-full h-20 object-cover rounded"
                              />
                              {isConflicting && (
                                <div className="absolute inset-0 bg-red-500 bg-opacity-20 rounded flex items-center justify-center">
                                  <span className="text-xs text-red-700 font-medium">Conflict</span>
                                </div>
                              )}
                            </div>
                          ) : (
                            <div className="w-full h-20 bg-gray-100 rounded flex items-center justify-center">
                              <Shirt className="w-8 h-8 text-gray-300" />
                            </div>
                          )}
                        </div>
                      </motion.div>
                    );
                  })}
              </div>

              {/* Instructions */}
              <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                <p className="text-xs text-blue-700">
                  💡 <span className="font-medium">Tip:</span> Click on items in your wardrobe to add them to your outfit. 
                  You can change any piece before trying on the complete look!
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};