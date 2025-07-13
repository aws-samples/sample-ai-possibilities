import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Eye, Plus, Sparkles, Heart, Tag } from 'lucide-react';
import { WardrobeItem } from '../../types';
import { createVirtualTryOnWithStyle } from '../../services/api';
import toast from 'react-hot-toast';

interface ModernClothingItemProps {
  item: WardrobeItem;
  userId: string;
  onTryOnResult?: (tryOnImageUrl: string, outfitData: any) => void;
  viewMode: 'grid' | 'list';
  isBuilderMode?: boolean;
  onAddToOutfit?: (item: WardrobeItem) => void;
}

const categoryColors = {
  top: '#6366f1',
  bottom: '#8b5cf6',
  dress: '#ec4899',
  outerwear: '#f59e0b',
  shoes: '#10b981',
  accessory: '#3b82f6',
};

export const ModernClothingItem: React.FC<ModernClothingItemProps> = ({
  item,
  userId,
  onTryOnResult,
  viewMode,
  isBuilderMode = false,
  onAddToOutfit,
}) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleTryOn = async () => {
    console.log('handleTryOn called:', { isBuilderMode, hasOnAddToOutfit: !!onAddToOutfit, itemId: item.itemId });
    
    if (isBuilderMode && onAddToOutfit) {
      console.log('Adding item to outfit:', item);
      onAddToOutfit(item);
      return;
    }

    setIsLoading(true);
    try {
      const response = await createVirtualTryOnWithStyle(
        userId,
        '', // Use profile photo
        item.itemId,
        item.category.toUpperCase(),
        {
          sleeveStyle: 'default',
          tuckingStyle: 'default',
          outerLayerStyle: 'default',
        }
      );

      if (response.data?.tryOnImageUrl && onTryOnResult) {
        onTryOnResult(response.data.tryOnImageUrl, {
          items: [item.itemId],
          occasion: 'single_item_try_on',
        });
        toast.success('Virtual try-on complete!');
      }
    } catch (error) {
      console.error('Virtual try-on error:', error);
      toast.error('Failed to create virtual try-on');
    } finally {
      setIsLoading(false);
    }
  };

  const categoryColor = categoryColors[item.category as keyof typeof categoryColors] || '#6366f1';
  const attributes = item.attributes || {};

  if (viewMode === 'list') {
    return (
      <motion.div
        className="fashion-item-card p-4 hover:shadow-lg transition-all"
        whileHover={{ scale: 1.01 }}
      >
        <div className="flex items-center gap-4">
          <div className="w-20 h-20 rounded-lg overflow-hidden flex-shrink-0">
            <img
              src={item.presignedUrl || ''}
              alt={attributes.description || 'Clothing item'}
              className="w-full h-full object-cover"
            />
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span 
                className="px-2 py-1 text-xs font-medium text-white rounded-full"
                style={{ backgroundColor: categoryColor }}
              >
                {item.category}
              </span>
              {attributes.color && (
                <span className="flex items-center gap-1 text-xs text-fashion-medium-gray">
                  <Tag className="w-3 h-3" />
                  {attributes.color}
                </span>
              )}
            </div>
            
            <h3 className="font-medium text-fashion-charcoal truncate">
              {attributes.description || `${item.category} item`}
            </h3>
            
            <p className="text-sm text-fashion-medium-gray">
              {(attributes as any).material && `${(attributes as any).material} • `}
              {(attributes as any).formalityLevel || 'Casual'}
            </p>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={handleTryOn}
              disabled={isLoading}
              className={`btn-fashion-primary px-4 py-2 ${
                isBuilderMode ? 'bg-fashion-accent' : ''
              }`}
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : isBuilderMode ? (
                <>
                  <Plus className="w-4 h-4 mr-2" />
                  Add
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" />
                  Try On
                </>
              )}
            </button>
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      className="fashion-item-card overflow-hidden group cursor-pointer"
      whileHover={{ scale: 1.02 }}
      onClick={handleTryOn}
    >
      {/* Image Container */}
      <div className="relative aspect-square overflow-hidden">
        <img
          src={item.presignedUrl || ''}
          alt={attributes.description || 'Clothing item'}
          className="w-full h-full object-cover transition-transform group-hover:scale-105"
        />
        
        {/* Overlay */}
        <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleTryOn();
            }}
            disabled={isLoading}
            className={`btn-fashion-primary ${
              isBuilderMode ? 'bg-fashion-accent' : ''
            }`}
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : isBuilderMode ? (
              <>
                <Plus className="w-5 h-5 mr-2" />
                Add to Outfit
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5 mr-2" />
                Try On
              </>
            )}
          </button>
        </div>

        {/* Category Badge */}
        <div 
          className="absolute top-3 left-3 px-2 py-1 text-xs font-medium text-white rounded-full shadow-lg"
          style={{ backgroundColor: categoryColor }}
        >
          {item.category}
        </div>

        {/* AI Badge */}
        {(attributes as any).analysisVersion && (
          <div className="absolute top-3 right-3 ai-powered-badge text-xs">
            AI
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        <div className="flex items-start justify-between mb-2">
          <h3 className="font-medium text-fashion-charcoal line-clamp-2 flex-1">
            {attributes.description || `${item.category} item`}
          </h3>
        </div>
        
        <div className="space-y-2">
          {attributes.color && (
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full border"
                style={{ backgroundColor: attributes.color }}
              />
              <span className="text-sm text-fashion-medium-gray">
                {attributes.color}
              </span>
            </div>
          )}
          
          <div className="flex items-center justify-between text-xs text-fashion-medium-gray">
            <span>{(attributes as any).material || 'Material unknown'}</span>
            <span>{(attributes as any).formalityLevel || 'Casual'}</span>
          </div>
          
          {(attributes as any).versatility && (
            <div className="flex items-center gap-1">
              <span className="text-xs text-fashion-medium-gray">Versatility:</span>
              <div className="flex gap-1">
                {[1, 2, 3, 4, 5].map((level) => (
                  <div
                    key={level}
                    className={`w-2 h-2 rounded-full ${
                      level <= ((attributes as any).versatility === 'high' ? 5 : (attributes as any).versatility === 'medium' ? 3 : 1)
                        ? 'bg-fashion-secondary'
                        : 'bg-fashion-gray'
                    }`}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};