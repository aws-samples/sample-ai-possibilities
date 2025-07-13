import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronLeft, ChevronRight, Eye, Trash2, Shirt, RefreshCw, Plus } from 'lucide-react';
import { WardrobeItem } from '../../types';
import { createVirtualTryOn, createVirtualTryOnWithStyle } from '../../services/api';
import { StyleOptionsModal, StyleOptions } from './StyleOptionsModal';
import toast from 'react-hot-toast';

interface ClothingCarouselProps {
  items: WardrobeItem[];
  userId: string;
  onTryOnResult?: (tryOnImageUrl: string, outfitData: any) => void;
  isBuilderMode?: boolean;
  onAddToOutfit?: (item: WardrobeItem) => void;
}

export const ClothingCarousel: React.FC<ClothingCarouselProps> = ({ 
  items, 
  userId, 
  onTryOnResult, 
  isBuilderMode, 
  onAddToOutfit 
}) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);
  const [tryingOn, setTryingOn] = useState<string | null>(null);
  const [showStyleModal, setShowStyleModal] = useState<WardrobeItem | null>(null);
  const [failedImages, setFailedImages] = useState<Set<string>>(new Set());

  // Clear failed images when items change (e.g., when wardrobe refreshes)
  React.useEffect(() => {
    setFailedImages(new Set());
  }, [items.length]);

  const itemsPerPage = 3;
  const totalPages = Math.ceil(items.length / itemsPerPage);
  const currentPage = Math.floor(currentIndex / itemsPerPage);

  const nextPage = () => {
    if (currentPage < totalPages - 1) {
      setCurrentIndex((currentPage + 1) * itemsPerPage);
    }
  };

  const prevPage = () => {
    if (currentPage > 0) {
      setCurrentIndex((currentPage - 1) * itemsPerPage);
    }
  };

  const visibleItems = items.slice(
    currentPage * itemsPerPage,
    (currentPage + 1) * itemsPerPage
  );

  const handleVirtualTryOn = (item: WardrobeItem) => {
    setShowStyleModal(item);
  };

  const handleStyleConfirm = async (item: WardrobeItem, options: StyleOptions) => {
    setTryingOn(item.itemId);
    setShowStyleModal(null);
    
    try {
      const response = await createVirtualTryOnWithStyle(
        userId,
        '', // Use stored profile photo
        item.itemId,
        item.category.toUpperCase(),
        options
      );
      
      console.log('Virtual try-on response:', response);
      
      // Check if response contains try-on image URL
      if (response.success && response.data) {
        let tryOnImageUrl = null;
        let outfitData = null;
        
        // Handle different response formats
        if (typeof response.data === 'string') {
          // Response might be a JSON string
          try {
            const parsedData = JSON.parse(response.data);
            tryOnImageUrl = parsedData.tryOnImageUrl;
            outfitData = parsedData.outfit;
          } catch (e) {
            console.log('Response data is not JSON:', response.data);
          }
        } else if (response.data.tryOnImageUrl) {
          // Direct object response
          tryOnImageUrl = response.data.tryOnImageUrl;
          outfitData = response.data.outfit;
        }
        
        if (tryOnImageUrl && onTryOnResult) {
          onTryOnResult(tryOnImageUrl, outfitData);
          toast.success('✨ Virtual try-on complete! Your portrait has been updated.');
        } else {
          toast.success('Virtual try-on created! Check your outfits.');
        }
      } else {
        toast.success('Virtual try-on created! Check your outfits.');
      }
    } catch (error) {
      console.error('Virtual try-on error:', error);
      toast.error('Failed to create virtual try-on. Make sure you have a profile photo.');
    } finally {
      setTryingOn(null);
    }
  };

  return (
    <div className="relative">
      {/* Carousel Container */}
      <div className="flex items-center justify-between">
        <button
          onClick={prevPage}
          disabled={currentPage === 0}
          className={`p-2 rounded-full transition-all ${
            currentPage === 0
              ? 'opacity-50 cursor-not-allowed bg-gray-100'
              : 'shadow-md hover:shadow-lg hover:scale-110'
          }`}
          style={{
            background: currentPage === 0 ? '#e5e7eb' : 'linear-gradient(135deg, var(--wardrobe-brass) 0%, #996515 100%)',
            boxShadow: currentPage === 0 ? 'none' : 'inset 0 1px 2px rgba(255,255,255,0.3), 0 2px 4px rgba(0,0,0,0.3)'
          }}
        >
          <ChevronLeft className={`w-5 h-5 ${currentPage === 0 ? 'text-gray-700' : 'text-white'}`} />
        </button>

        <div className="flex-1 mx-4">
          <div className="grid grid-cols-3 gap-4">
            <AnimatePresence>
              {visibleItems.map((item, index) => (
                <motion.div
                  key={item.itemId}
                  initial={{ opacity: 0, scale: 0.8, y: 20 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.8, y: -20 }}
                  transition={{ delay: index * 0.1 }}
                  className="relative group clothing-item"
                  onMouseEnter={() => setHoveredItem(item.itemId)}
                  onMouseLeave={() => setHoveredItem(null)}
                >
                  {/* Closet Hanger Effect */}
                  <div className="absolute -top-6 left-1/2 transform -translate-x-1/2 z-20">
                    <div className="hanger-hook scale-50"></div>
                  </div>

                  {/* Clothing Item Card - Hanging Effect */}
                  <motion.div
                    whileHover={{ y: -5, rotateZ: 2 }}
                    className="bg-white rounded-lg shadow-xl overflow-hidden transform transition-all duration-300 fabric-texture"
                    style={{
                      transformOrigin: 'top center',
                      boxShadow: '0 10px 25px rgba(0,0,0,0.2), 0 6px 6px rgba(0,0,0,0.1)'
                    }}
                  >
                    <div className="aspect-w-3 aspect-h-4 relative">
                      {item.presignedUrl && !failedImages.has(item.itemId) ? (
                        <img
                          src={item.presignedUrl}
                          alt={item.attributes?.description || 'Clothing item'}
                          className="w-full h-64 object-cover"
                          onError={() => {
                            console.log('Image load failed for item:', item.itemId, '- marking as failed');
                            setFailedImages(prev => new Set(prev).add(item.itemId));
                          }}
                        />
                      ) : (
                        <div className="w-full h-64 bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center">
                          <div className="text-center text-gray-500">
                            <Shirt className="w-12 h-12 mx-auto mb-2 opacity-50" />
                            <p className="text-sm">
                              {item.presignedUrl ? 'Image unavailable' : 'Loading image...'}
                            </p>
                            {failedImages.has(item.itemId) && item.presignedUrl && (
                              <button
                                onClick={() => {
                                  setFailedImages(prev => {
                                    const newSet = new Set(prev);
                                    newSet.delete(item.itemId);
                                    return newSet;
                                  });
                                }}
                                className="mt-2 flex items-center justify-center mx-auto text-xs text-gray-400 hover:text-gray-600 transition-colors"
                              >
                                <RefreshCw className="w-3 h-3 mr-1" />
                                Retry
                              </button>
                            )}
                          </div>
                        </div>
                      )}
                      
                      {/* Overlay on Hover */}
                      <AnimatePresence>
                        {hoveredItem === item.itemId && (
                          <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent flex flex-col justify-end p-4"
                          >
                            <div className="text-white">
                              <p className="font-semibold capitalize">{item.category}</p>
                              <p className="text-sm opacity-90">
                                {item.attributes?.color || 'Unknown'} • {item.attributes?.style || 'Unknown'}
                              </p>
                            </div>
                            <div className="flex space-x-2 mt-3">
                              <motion.button
                                whileHover={{ scale: 1.1 }}
                                whileTap={{ scale: 0.9 }}
                                onClick={() => {
                                  if (isBuilderMode && onAddToOutfit) {
                                    onAddToOutfit(item);
                                  } else {
                                    handleVirtualTryOn(item);
                                  }
                                }}
                                disabled={tryingOn === item.itemId}
                                className="bg-gradient-to-r from-purple-500/30 to-pink-500/30 backdrop-blur-sm p-2 rounded-full hover:from-purple-500/50 hover:to-pink-500/50 transition-all disabled:opacity-50"
                                title={isBuilderMode ? "Add to Outfit" : "Virtual Try-On"}
                              >
                                {tryingOn === item.itemId ? (
                                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                ) : isBuilderMode ? (
                                  <Plus className="w-4 h-4 text-white" />
                                ) : (
                                  <Shirt className="w-4 h-4 text-white" />
                                )}
                              </motion.button>
                              <motion.button
                                whileHover={{ scale: 1.1 }}
                                whileTap={{ scale: 0.9 }}
                                className="bg-white/20 backdrop-blur-sm p-2 rounded-full hover:bg-white/30 transition-colors"
                                title="View Details"
                              >
                                <Eye className="w-4 h-4 text-white" />
                              </motion.button>
                              <motion.button
                                whileHover={{ scale: 1.1 }}
                                whileTap={{ scale: 0.9 }}
                                className="bg-red-500/20 backdrop-blur-sm p-2 rounded-full hover:bg-red-500/30 transition-colors"
                                title="Remove Item"
                              >
                                <Trash2 className="w-4 h-4 text-white" />
                              </motion.button>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>

                    {/* Item Details */}
                    <div className="p-3 bg-gradient-to-b from-gray-50 to-white">
                      <div className="flex items-center space-x-2">
                        <span className={`w-4 h-4 rounded-full border-2 border-gray-300`} 
                              style={{ backgroundColor: item.attributes?.color?.toLowerCase() || '#cccccc' }}></span>
                        <span className="text-sm text-gray-600 capitalize">
                          {item.attributes?.season || 'All'} Season
                        </span>
                      </div>
                    </div>
                  </motion.div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </div>

        <button
          onClick={nextPage}
          disabled={currentPage === totalPages - 1}
          className={`p-2 rounded-full transition-all ${
            currentPage === totalPages - 1
              ? 'opacity-50 cursor-not-allowed bg-gray-100'
              : 'shadow-md hover:shadow-lg hover:scale-110'
          }`}
          style={{
            background: currentPage === totalPages - 1 ? '#e5e7eb' : 'linear-gradient(135deg, var(--wardrobe-brass) 0%, #996515 100%)',
            boxShadow: currentPage === totalPages - 1 ? 'none' : 'inset 0 1px 2px rgba(255,255,255,0.3), 0 2px 4px rgba(0,0,0,0.3)'
          }}
        >
          <ChevronRight className={`w-5 h-5 ${currentPage === totalPages - 1 ? 'text-gray-700' : 'text-white'}`} />
        </button>
      </div>

      {/* Page Indicators */}
      {totalPages > 1 && (
        <div className="flex justify-center mt-6 space-x-2">
          {Array.from({ length: totalPages }).map((_, index) => (
            <button
              key={index}
              onClick={() => setCurrentIndex(index * itemsPerPage)}
              className={`w-2 h-2 rounded-full transition-all ${
                index === currentPage
                  ? 'w-8'
                  : 'hover:bg-amber-700'
              }`}
              style={{
                backgroundColor: index === currentPage ? 'var(--wardrobe-brass)' : '#d4d4d4'
              }}
            />
          ))}
        </div>
      )}

      {/* Style Options Modal */}
      <AnimatePresence>
        {showStyleModal && (
          <StyleOptionsModal
            item={showStyleModal}
            onClose={() => setShowStyleModal(null)}
            onConfirm={(options) => handleStyleConfirm(showStyleModal, options)}
            isLoading={tryingOn === showStyleModal.itemId}
          />
        )}
      </AnimatePresence>
    </div>
  );
};