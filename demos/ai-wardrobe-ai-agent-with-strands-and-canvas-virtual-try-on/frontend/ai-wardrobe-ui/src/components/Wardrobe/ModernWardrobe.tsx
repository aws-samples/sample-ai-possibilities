import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Filter, Grid, List, Sparkles, ShoppingBag } from 'lucide-react';
import { User, WardrobeItem } from '../../types';
import { getWardrobe } from '../../services/api';
import { ModernClothingItem } from './ModernClothingItem';
import { UploadModal } from '../Upload/UploadModal';
import toast from 'react-hot-toast';

interface ModernWardrobeProps {
  user: User;
  onTryOnResult?: (tryOnImageUrl: string, outfitData: any) => void;
  isBuilderMode?: boolean;
  onAddToOutfit?: (item: WardrobeItem) => void;
}

const categories = [
  { id: 'all', name: 'All Items' },
  { id: 'top', name: 'Tops' },
  { id: 'bottom', name: 'Bottoms' },
  { id: 'dress', name: 'Dresses' },
  { id: 'outerwear', name: 'Outerwear' },
  { id: 'shoes', name: 'Shoes' },
  { id: 'accessory', name: 'Accessories' },
];

export const ModernWardrobe: React.FC<ModernWardrobeProps> = ({
  user,
  onTryOnResult,
  isBuilderMode = false,
  onAddToOutfit,
}) => {
  const [items, setItems] = useState<WardrobeItem[]>([]);
  const [filteredItems, setFilteredItems] = useState<WardrobeItem[]>([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const loadWardrobe = async () => {
    setIsLoading(true);
    try {
      const response = await getWardrobe(user.userId);
      if (response.success && response.data) {
        setItems(response.data);
        setFilteredItems(response.data);
      }
    } catch (error) {
      console.error('Error loading wardrobe:', error);
      toast.error('Failed to load wardrobe items');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadWardrobe();
  }, [user.userId]);

  useEffect(() => {
    if (selectedCategory === 'all') {
      setFilteredItems(items);
    } else {
      setFilteredItems(items.filter(item => item.category === selectedCategory));
    }
  }, [selectedCategory, items]);

  const handleUploadSuccess = () => {
    loadWardrobe();
    toast.success('Item added to your wardrobe!');
  };

  return (
    <div className="fashion-card p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="fashion-icon-container">
            <ShoppingBag className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="fashion-section-title">My Wardrobe</h2>
            <p className="fashion-section-subtitle">
              {items.length} items • {isBuilderMode ? 'Select items for outfit' : 'Click to try on'}
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {/* View Mode Toggle */}
          <div className="flex bg-fashion-light-gray rounded-lg p-1">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded ${
                viewMode === 'grid' 
                  ? 'bg-white shadow-sm text-fashion-secondary' 
                  : 'text-fashion-medium-gray'
              }`}
            >
              <Grid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 rounded ${
                viewMode === 'list' 
                  ? 'bg-white shadow-sm text-fashion-secondary' 
                  : 'text-fashion-medium-gray'
              }`}
            >
              <List className="w-4 h-4" />
            </button>
          </div>
          
          {/* Add Item Button */}
          <button
            onClick={() => setShowUploadModal(true)}
            className="btn-fashion-primary"
          >
            <Plus className="w-5 h-5 mr-2" />
            Add Item
          </button>
        </div>
      </div>

      {/* Category Filter */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
        {categories.map((category) => (
          <button
            key={category.id}
            onClick={() => setSelectedCategory(category.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-full whitespace-nowrap transition-all ${
              selectedCategory === category.id
                ? 'bg-indigo-600 text-white shadow-md border border-indigo-600'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-200'
            }`}
          >
            <span className="text-sm font-medium">{category.name}</span>
            {category.id !== 'all' && (
              <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full">
                {items.filter(item => item.category === category.id).length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Items Grid/List */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="w-12 h-12 border-4 border-fashion-secondary border-t-transparent rounded-full animate-spin mb-4"></div>
          <p className="text-fashion-medium-gray">Loading your wardrobe...</p>
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20">
          <ShoppingBag className="w-16 h-16 text-fashion-light-gray mb-4" />
          <h3 className="text-lg font-medium text-fashion-dark-gray mb-2">
            {selectedCategory === 'all' ? 'Your wardrobe is empty' : `No ${selectedCategory} items yet`}
          </h3>
          <p className="text-fashion-medium-gray mb-6">
            Start building your digital wardrobe by adding items
          </p>
          <button
            onClick={() => setShowUploadModal(true)}
            className="btn-fashion-primary"
          >
            <Plus className="w-5 h-5 mr-2" />
            Add Your First Item
          </button>
        </div>
      ) : (
        <>
          {console.log('Filtered items:', filteredItems.length, filteredItems)}
          <div className={
            viewMode === 'grid' 
              ? 'grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 min-h-[200px]'
              : 'space-y-3 min-h-[200px]'
          }>
          <AnimatePresence>
            {filteredItems.map((item, index) => (
              <motion.div
                key={item.itemId}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ delay: index * 0.05 }}
              >
                <ModernClothingItem
                  item={item}
                  userId={user.userId}
                  onTryOnResult={onTryOnResult}
                  viewMode={viewMode}
                  isBuilderMode={isBuilderMode}
                  onAddToOutfit={onAddToOutfit}
                />
              </motion.div>
            ))}
          </AnimatePresence>
          </div>
        </>
      )}

      {/* Upload Modal */}
      <AnimatePresence>
        {showUploadModal && (
          <UploadModal
            user={user}
            onClose={() => setShowUploadModal(false)}
            onUploadComplete={handleUploadSuccess}
          />
        )}
      </AnimatePresence>
    </div>
  );
};