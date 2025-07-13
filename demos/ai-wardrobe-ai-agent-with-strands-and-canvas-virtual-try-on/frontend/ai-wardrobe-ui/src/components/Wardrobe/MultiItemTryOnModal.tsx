import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Shirt, Check, Users } from 'lucide-react';
import { WardrobeItem } from '../../types';

interface MultiItemTryOnModalProps {
  items: WardrobeItem[];
  onClose: () => void;
  onConfirm: (selectedItems: string[]) => void;
  isLoading: boolean;
}

export const MultiItemTryOnModal: React.FC<MultiItemTryOnModalProps> = ({
  items,
  onClose,
  onConfirm,
  isLoading
}) => {
  const [selectedItems, setSelectedItems] = useState<string[]>([]);

  const toggleItem = (itemId: string) => {
    setSelectedItems(prev => 
      prev.includes(itemId) 
        ? prev.filter(id => id !== itemId)
        : [...prev, itemId]
    );
  };

  const handleConfirm = () => {
    if (selectedItems.length > 0) {
      onConfirm(selectedItems);
    }
  };

  // Group items by category for better organization
  const groupedItems = items.reduce((acc, item) => {
    const category = item.category;
    if (!acc[category]) acc[category] = [];
    acc[category].push(item);
    return acc;
  }, {} as Record<string, WardrobeItem[]>);

  const categoryOrder = ['top', 'bottom', 'dress', 'outerwear', 'shoes', 'accessory'];
  const sortedCategories = categoryOrder.filter(cat => groupedItems[cat]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        onClick={(e) => e.stopPropagation()}
        className="wardrobe-door rounded-xl w-full max-w-4xl max-h-[90vh] overflow-hidden"
      >
        <div className="wood-panel p-4">
          <div className="flex justify-between items-center">
            <h3 className="text-xl font-bold text-white flex items-center">
              <Users className="w-6 h-6 mr-2" />
              Complete Outfit Try-On
            </h3>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/20 rounded-full transition-colors"
            >
              <X className="w-5 h-5 text-white" />
            </button>
          </div>
          <p className="text-gray-300 text-sm mt-2">
            Select multiple items to create a complete outfit
          </p>
        </div>

        <div className="bg-white/95 p-6 max-h-[calc(90vh-140px)] overflow-y-auto">
          {/* Selected Items Summary */}
          {selectedItems.length > 0 && (
            <div className="mb-6 p-4 bg-amber-50 rounded-lg border border-amber-200">
              <h4 className="font-semibold text-amber-800 mb-2">
                Selected Items ({selectedItems.length})
              </h4>
              <div className="flex flex-wrap gap-2">
                {selectedItems.map(itemId => {
                  const item = items.find(i => i.itemId === itemId);
                  return item ? (
                    <span
                      key={itemId}
                      className="px-3 py-1 bg-amber-200 text-amber-800 text-sm rounded-full"
                    >
                      {item.category} • {item.attributes.color}
                    </span>
                  ) : null;
                })}
              </div>
            </div>
          )}

          {/* Items by Category */}
          <div className="space-y-6">
            {sortedCategories.map(category => (
              <div key={category}>
                <h4 className="font-semibold text-gray-800 mb-3 capitalize flex items-center">
                  <span className="text-lg mr-2">
                    {category === 'top' && '👕'}
                    {category === 'bottom' && '👖'}
                    {category === 'dress' && '👗'}
                    {category === 'outerwear' && '🧥'}
                    {category === 'shoes' && '👟'}
                    {category === 'accessory' && '👜'}
                  </span>
                  {category === 'accessory' ? 'Accessories' : `${category}s`}
                </h4>
                
                <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                  {groupedItems[category].map(item => (
                    <div
                      key={item.itemId}
                      className={`relative cursor-pointer rounded-lg overflow-hidden transition-all ${
                        selectedItems.includes(item.itemId)
                          ? 'ring-3 ring-amber-500 ring-offset-2'
                          : 'hover:shadow-lg'
                      }`}
                      onClick={() => toggleItem(item.itemId)}
                    >
                      <div className="aspect-w-3 aspect-h-4">
                        <img
                          src={item.presignedUrl || '/api/placeholder/150/200'}
                          alt={item.attributes.description || 'Clothing item'}
                          className="w-full h-32 object-cover"
                        />
                      </div>
                      
                      {/* Selection Indicator */}
                      {selectedItems.includes(item.itemId) && (
                        <div className="absolute top-2 right-2 bg-amber-500 text-white rounded-full p-1">
                          <Check className="w-4 h-4" />
                        </div>
                      )}
                      
                      {/* Item Info */}
                      <div className="p-2 bg-white">
                        <p className="text-xs text-gray-600 truncate">
                          {item.attributes.color}
                        </p>
                        <p className="text-xs text-gray-500 capitalize">
                          {item.attributes.style}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {items.length === 0 && (
            <div className="text-center py-12">
              <Shirt className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No items in wardrobe
              </h3>
              <p className="text-gray-500">
                Add some clothes to your wardrobe first
              </p>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="bg-white/95 px-6 py-4 border-t border-gray-200">
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              className="flex-1 py-3 px-4 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              onClick={handleConfirm}
              disabled={isLoading || selectedItems.length === 0}
              className="flex-1 py-3 px-4 text-white rounded-lg shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                background: selectedItems.length > 0 
                  ? 'linear-gradient(135deg, var(--wardrobe-brass) 0%, #996515 100%)'
                  : '#d1d5db',
                boxShadow: selectedItems.length > 0 
                  ? 'inset 0 1px 2px rgba(255,255,255,0.3), 0 2px 4px rgba(0,0,0,0.3)'
                  : 'none'
              }}
            >
              {isLoading ? (
                <div className="flex items-center justify-center">
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                  Creating Outfit...
                </div>
              ) : (
                `Try On ${selectedItems.length} Item${selectedItems.length !== 1 ? 's' : ''}`
              )}
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};