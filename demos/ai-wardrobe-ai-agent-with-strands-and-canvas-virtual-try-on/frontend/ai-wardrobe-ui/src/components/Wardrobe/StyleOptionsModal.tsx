import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Shirt, ArrowUp, ArrowDown } from 'lucide-react';
import { WardrobeItem } from '../../types';

interface StyleOptionsModalProps {
  item: WardrobeItem;
  onClose: () => void;
  onConfirm: (options: StyleOptions) => void;
  isLoading: boolean;
}

export interface StyleOptions {
  sleeveStyle: 'default' | 'SLEEVE_DOWN' | 'SLEEVE_UP';
  tuckingStyle: 'default' | 'TUCKED' | 'UNTUCKED';
  outerLayerStyle: 'default' | 'OPEN' | 'CLOSED';
}

export const StyleOptionsModal: React.FC<StyleOptionsModalProps> = ({
  item,
  onClose,
  onConfirm,
  isLoading
}) => {
  const [options, setOptions] = useState<StyleOptions>({
    sleeveStyle: 'default',
    tuckingStyle: 'default',
    outerLayerStyle: 'default'
  });

  const isUpperBody = ['top', 'shirt', 'blouse', 'sweater', 'jacket', 'coat'].includes(
    item.category.toLowerCase()
  );

  const handleConfirm = () => {
    onConfirm(options);
  };

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
        className="wardrobe-door rounded-xl w-full max-w-md overflow-hidden"
      >
        <div className="wood-panel p-4">
          <div className="flex justify-between items-center">
            <h3 className="text-xl font-bold text-white flex items-center">
              <Shirt className="w-6 h-6 mr-2" />
              Style Options
            </h3>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/20 rounded-full transition-colors"
            >
              <X className="w-5 h-5 text-white" />
            </button>
          </div>
        </div>

        <div className="bg-white/95 p-6 space-y-6">
          {/* Item Preview */}
          <div className="text-center">
            <div className="w-24 h-32 mx-auto mb-3 rounded-lg overflow-hidden shadow-lg">
              <img
                src={item.presignedUrl || '/api/placeholder/200/250'}
                alt={item.attributes.description || 'Clothing item'}
                className="w-full h-full object-cover"
              />
            </div>
            <p className="text-sm text-gray-600 capitalize">
              {item.category} • {item.attributes.color} • {item.attributes.style}
            </p>
          </div>

          {/* Style Options - Only show for upper body items */}
          {isUpperBody && (
            <div className="space-y-4">
              <h4 className="font-semibold text-gray-800">Styling Options</h4>
              
              {/* Sleeve Style - Only for items that can have sleeves */}
              {!['tank', 'vest', 'sleeveless'].some(keyword => 
                item.attributes.description?.toLowerCase().includes(keyword) ||
                item.attributes.style?.toLowerCase().includes(keyword)
              ) && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Sleeve Style
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { value: 'default', label: 'Default', icon: '👕' },
                      { value: 'SLEEVE_DOWN', label: 'Down', icon: '👔' },
                      { value: 'SLEEVE_UP', label: 'Rolled Up', icon: '🎽' }
                    ].map((option) => (
                      <button
                        key={option.value}
                        onClick={() => setOptions(prev => ({ ...prev, sleeveStyle: option.value as any }))}
                        className={`p-3 rounded-lg border-2 text-center transition-all ${
                          options.sleeveStyle === option.value
                            ? 'border-amber-600 bg-amber-50'
                            : 'border-gray-200 hover:border-amber-400'
                        }`}
                      >
                        <div className="text-lg mb-1">{option.icon}</div>
                        <div className="text-xs font-medium">{option.label}</div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Tucking Style */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Tucking Style
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { value: 'default', label: 'Default', icon: '👕' },
                    { value: 'TUCKED', label: 'Tucked In', icon: <ArrowDown className="w-4 h-4" /> },
                    { value: 'UNTUCKED', label: 'Untucked', icon: <ArrowUp className="w-4 h-4" /> }
                  ].map((option) => (
                    <button
                      key={option.value}
                      onClick={() => setOptions(prev => ({ ...prev, tuckingStyle: option.value as any }))}
                      className={`p-3 rounded-lg border-2 text-center transition-all ${
                        options.tuckingStyle === option.value
                          ? 'border-amber-600 bg-amber-50'
                          : 'border-gray-200 hover:border-amber-400'
                      }`}
                    >
                      <div className="text-lg mb-1 flex justify-center">
                        {typeof option.icon === 'string' ? option.icon : option.icon}
                      </div>
                      <div className="text-xs font-medium">{option.label}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Outer Layer Style - Only for jackets/coats */}
              {['jacket', 'coat', 'blazer'].includes(item.category.toLowerCase()) && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Layer Style
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {[
                      { value: 'default', label: 'Default', icon: '🧥' },
                      { value: 'CLOSED', label: 'Closed', icon: '🔒' },
                      { value: 'OPEN', label: 'Open', icon: '🔓' }
                    ].map((option) => (
                      <button
                        key={option.value}
                        onClick={() => setOptions(prev => ({ ...prev, outerLayerStyle: option.value as any }))}
                        className={`p-3 rounded-lg border-2 text-center transition-all ${
                          options.outerLayerStyle === option.value
                            ? 'border-amber-600 bg-amber-50'
                            : 'border-gray-200 hover:border-amber-400'
                        }`}
                      >
                        <div className="text-lg mb-1">{option.icon}</div>
                        <div className="text-xs font-medium">{option.label}</div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {!isUpperBody && (
            <div className="text-center py-8">
              <p className="text-gray-500">
                Style options are available for tops, shirts, and jackets.
              </p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex space-x-3 pt-4">
            <button
              onClick={onClose}
              className="flex-1 py-3 px-4 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              onClick={handleConfirm}
              disabled={isLoading}
              className="flex-1 py-3 px-4 text-white rounded-lg shadow-lg hover:shadow-xl transition-all disabled:opacity-50"
              style={{
                background: 'linear-gradient(135deg, var(--wardrobe-brass) 0%, #996515 100%)',
                boxShadow: 'inset 0 1px 2px rgba(255,255,255,0.3), 0 2px 4px rgba(0,0,0,0.3)'
              }}
            >
              {isLoading ? (
                <div className="flex items-center justify-center">
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                  Creating...
                </div>
              ) : (
                'Try On'
              )}
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};