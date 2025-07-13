import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Shirt, Users } from 'lucide-react';
import { User, WardrobeItem } from '../../types';
import { getWardrobe, createMultiItemTryOn } from '../../services/api';
import { ClothingCarousel } from './ClothingCarousel';
import { UploadModal } from '../Upload/UploadModal';
import { MultiItemTryOnModal } from './MultiItemTryOnModal';
import toast from 'react-hot-toast';

interface WardrobeProps {
  user: User;
  onTryOnResult?: (tryOnImageUrl: string, outfitData: any) => void;
  isBuilderMode?: boolean;
  onAddToOutfit?: (item: WardrobeItem) => void;
}

const categories = [
  { id: 'all', name: 'All', icon: '👔' },
  { id: 'top', name: 'Tops', icon: '👕' },
  { id: 'bottom', name: 'Bottoms', icon: '👖' },
  { id: 'dress', name: 'Dresses', icon: '👗' },
  { id: 'outerwear', name: 'Outerwear', icon: '🧥' },
  { id: 'shoes', name: 'Shoes', icon: '👟' },
  { id: 'accessory', name: 'Accessories', icon: '👜' },
];

export const Wardrobe: React.FC<WardrobeProps> = ({ user, onTryOnResult, isBuilderMode, onAddToOutfit }) => {
  const [items, setItems] = useState<WardrobeItem[]>([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [isLoading, setIsLoading] = useState(true);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showMultiTryOnModal, setShowMultiTryOnModal] = useState(false);
  const [isCreatingOutfit, setIsCreatingOutfit] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [retryAttempts, setRetryAttempts] = useState(0);

  useEffect(() => {
    const loadWardrobe = async () => {
      try {
        setIsLoading(true);
        const response = await getWardrobe(
          user.userId,
          selectedCategory === 'all' ? undefined : selectedCategory
        );
        
        console.log('=== Wardrobe API Response ===');
        console.log('Response:', response);
        console.log('Response.data:', response.data);
        console.log('Response.data type:', typeof response.data);
        console.log('Response.data is array:', Array.isArray(response.data));
        
        // Parse the API response to extract wardrobe items
        if (Array.isArray(response.data)) {
          const fetchedItems = response.data;
          console.log(`Fetched ${fetchedItems.length} wardrobe items:`, fetchedItems);
          setItems(fetchedItems);
          
          // Check if any items are missing presigned URLs and retry if needed (only for new uploads)
          const itemsWithoutImages = fetchedItems.filter((item: WardrobeItem) => !item.presignedUrl);
          if (itemsWithoutImages.length > 0 && retryAttempts < 2) {
            console.log(`Found ${itemsWithoutImages.length} items without images, retrying in 3 seconds (attempt ${retryAttempts + 1}/2)`);
            setTimeout(() => {
              setRetryAttempts(prev => prev + 1);
              setRefreshTrigger(prev => prev + 1);
            }, 3000);
          } else {
            setRetryAttempts(0); // Reset retry attempts on successful load or max retries reached
            if (itemsWithoutImages.length > 0) {
              console.log(`${itemsWithoutImages.length} items still missing images after retries - they will show placeholders`);
            }
          }
        } else {
          // Fallback to empty array if response format is unexpected
          console.log('Response.data is not an array, setting empty items');
          setItems([]);
        }
      } catch (error) {
        console.error('Error loading wardrobe:', error);
        toast.error('Failed to load wardrobe');
      } finally {
        setIsLoading(false);
      }
    };

    loadWardrobe();
  }, [user.userId, selectedCategory, refreshTrigger, retryAttempts]);

  const filteredItems = selectedCategory === 'all' 
    ? items 
    : items.filter(item => item.category === selectedCategory);

  const handleMultiItemTryOn = async (selectedItemIds: string[]) => {
    setIsCreatingOutfit(true);
    setShowMultiTryOnModal(false);
    
    try {
      const response = await createMultiItemTryOn(user.userId, selectedItemIds);
      toast.success('Complete outfit try-on created! Check your outfits.');
    } catch (error) {
      console.error('Multi-item try-on error:', error);
      toast.error('Failed to create outfit try-on. Make sure you have a profile photo.');
    } finally {
      setIsCreatingOutfit(false);
    }
  };

  return (
    <div className="wardrobe-door rounded-xl overflow-hidden">
      <div className="wood-panel p-6">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center">
              <div className="hanger-hook scale-75 mr-3"></div>
              My Wardrobe
            </h2>
            <p className="text-gray-300 mt-1">
              {items.length} items in your collection
            </p>
          </div>
          <div className="flex space-x-3">
            {items.length >= 2 && (
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setShowMultiTryOnModal(true)}
                disabled={isCreatingOutfit}
                className="text-white p-3 rounded-full shadow-lg hover:shadow-xl transition-all disabled:opacity-50"
                style={{
                  background: 'linear-gradient(135deg, var(--wardrobe-brass) 0%, #996515 100%)',
                  boxShadow: 'inset 0 1px 2px rgba(255,255,255,0.3), 0 2px 4px rgba(0,0,0,0.3)'
                }}
                title="Try on multiple items"
              >
                {isCreatingOutfit ? (
                  <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <Users className="w-6 h-6" />
                )}
              </motion.button>
            )}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setShowUploadModal(true)}
              className="text-white p-3 rounded-full shadow-lg hover:shadow-xl transition-all"
              style={{
                background: 'linear-gradient(135deg, var(--wardrobe-brass) 0%, #996515 100%)',
                boxShadow: 'inset 0 1px 2px rgba(255,255,255,0.3), 0 2px 4px rgba(0,0,0,0.3)'
              }}
              title="Add new item"
            >
              <Plus className="w-6 h-6" />
            </motion.button>
          </div>
        </div>
      </div>

      {/* Category Tabs - Drawer Style */}
      <div className="wardrobe-drawer mx-4 -mt-3 relative z-10 px-6 py-3">
        <div className="flex space-x-4 overflow-x-auto pb-2 scrollbar-hide">
          {categories.map((category) => (
            <button
              key={category.id}
              onClick={() => setSelectedCategory(category.id)}
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg whitespace-nowrap transition-all ${
                selectedCategory === category.id
                  ? 'bg-gradient-to-br from-amber-600 to-amber-700 text-white shadow-md'
                  : 'bg-white/80 text-gray-700 hover:bg-white'
              }`}
              style={selectedCategory === category.id ? {
                background: 'linear-gradient(135deg, var(--wardrobe-brass) 0%, #996515 100%)'
              } : {}}
            >
              <span className="text-lg">{category.icon}</span>
              <span className="text-sm font-medium">{category.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Wardrobe Content - Closet Interior */}
      <div className="closet-interior p-6 min-h-[400px]">
        <div className="clothing-rack">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-yellow-600"></div>
            </div>
          ) : filteredItems.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-12"
          >
            <Shirt className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              {selectedCategory === 'all' 
                ? 'Your wardrobe is empty'
                : `No ${categories.find(c => c.id === selectedCategory)?.name.toLowerCase() || 'items'} yet`
              }
            </h3>
            <p className="text-gray-500 mb-4">
              Start building your virtual wardrobe by uploading your clothes
            </p>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 text-left max-w-md mx-auto">
              <p className="text-sm text-blue-700">
                <span className="font-semibold">💡 Photo tip:</span> Upload clear photos with good lighting - they make virtual try-ons look amazing!
              </p>
            </div>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setShowUploadModal(true)}
              className="inline-flex items-center px-6 py-3 text-white rounded-lg shadow-lg hover:shadow-xl transition-all"
              style={{
                background: 'linear-gradient(135deg, var(--wardrobe-brass) 0%, #996515 100%)',
                boxShadow: 'inset 0 1px 2px rgba(255,255,255,0.3), 0 2px 4px rgba(0,0,0,0.3)'
              }}
            >
              <Plus className="w-5 h-5 mr-2" />
              Add First Item
            </motion.button>
          </motion.div>
          ) : (
            <ClothingCarousel 
              items={filteredItems} 
              userId={user.userId} 
              onTryOnResult={onTryOnResult}
              isBuilderMode={isBuilderMode}
              onAddToOutfit={onAddToOutfit}
            />
          )}
        </div>
      </div>

      {/* Upload Modal */}
      <AnimatePresence>
        {showUploadModal && (
          <UploadModal
            user={user}
            onClose={() => setShowUploadModal(false)}
            onUploadComplete={() => {
              setShowUploadModal(false);
              // Reset retry attempts and trigger wardrobe refresh
              setRetryAttempts(0);
              setRefreshTrigger(prev => prev + 1);
            }}
          />
        )}
      </AnimatePresence>

      {/* Multi-Item Try-On Modal */}
      <AnimatePresence>
        {showMultiTryOnModal && (
          <MultiItemTryOnModal
            items={items}
            onClose={() => setShowMultiTryOnModal(false)}
            onConfirm={handleMultiItemTryOn}
            isLoading={isCreatingOutfit}
          />
        )}
      </AnimatePresence>
    </div>
  );
};