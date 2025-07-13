import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Eye, Save, Calendar, Shirt, Users, ChevronDown, ChevronUp } from 'lucide-react';
import { User, Outfit } from '../../types';
import { getOutfits } from '../../services/api';
import toast from 'react-hot-toast';

interface OutfitGalleryProps {
  user: User;
}

export const OutfitGallery: React.FC<OutfitGalleryProps> = ({ user }) => {
  const [outfits, setOutfits] = useState<Outfit[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedOutfit, setSelectedOutfit] = useState<Outfit | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    const loadOutfits = async () => {
      try {
        setIsLoading(true);
        const response = await getOutfits(user.userId);
        
        if (response.success && Array.isArray(response.data)) {
          setOutfits(response.data);
        } else {
          setOutfits([]);
        }
      } catch (error) {
        console.error('Error loading outfits:', error);
        toast.error('Failed to load outfits');
      } finally {
        setIsLoading(false);
      }
    };

    loadOutfits();
  }, [user.userId]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
  };

  const updateUserPhoto = async (outfitImageUrl: string) => {
    try {
      // This would update the user's current photo to this try-on result
      // For now, we'll just show a toast indicating the feature
      toast.success('🌟 This feature will update your current photo! Currently showing the try-on result.', {
        duration: 4000,
      });
    } catch (error) {
      toast.error('Failed to update photo');
    }
  };

  if (isLoading) {
    return (
      <div className="wardrobe-door rounded-xl overflow-hidden">
        <div className="wood-panel p-6">
          <h2 className="text-xl font-bold text-white flex items-center">
            <div className="hanger-hook scale-75 mr-3"></div>
            Outfit Archive
          </h2>
        </div>
        <div className="closet-interior p-6 min-h-[300px] flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-yellow-600"></div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="wardrobe-door rounded-xl overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full wood-panel p-6 hover:bg-opacity-90 transition-all text-left"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <div className="hanger-hook scale-75 mr-3"></div>
            <div>
              <h2 className="text-xl font-bold text-white">
                Outfit Archive
              </h2>
              <p className="text-gray-300 mt-1">
                {outfits.length} saved {outfits.length === 1 ? 'outfit' : 'outfits'}
              </p>
            </div>
          </div>
          <motion.div
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.3 }}
            className="text-white"
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
            <div className="closet-interior p-6 min-h-[300px]">
        {outfits.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-12"
          >
            <Shirt className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No outfits saved yet
            </h3>
            <p className="text-gray-500 mb-4">
              Start trying on clothes to build your outfit archive
            </p>
          </motion.div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <AnimatePresence>
              {outfits.map((outfit, index) => (
                <motion.div
                  key={outfit.outfitId}
                  initial={{ opacity: 0, scale: 0.8, y: 20 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.8, y: -20 }}
                  transition={{ delay: index * 0.1 }}
                  className="relative group bg-white rounded-lg shadow-lg overflow-hidden hover:shadow-xl transition-all duration-300"
                >
                  {/* Try-on Image */}
                  <div className="aspect-w-3 aspect-h-4 relative">
                    {outfit.tryOnPresignedUrl ? (
                      <img
                        src={outfit.tryOnPresignedUrl}
                        alt={`Outfit from ${formatDate(outfit.createdAt)}`}
                        className="w-full h-48 object-cover"
                      />
                    ) : (
                      <div className="w-full h-48 bg-gray-200 flex items-center justify-center">
                        <Users className="w-12 h-12 text-gray-400" />
                      </div>
                    )}
                    
                    {/* Overlay on Hover */}
                    <motion.div
                      initial={{ opacity: 0 }}
                      whileHover={{ opacity: 1 }}
                      className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent flex flex-col justify-end p-3"
                    >
                      <div className="flex space-x-2">
                        <motion.button
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.9 }}
                          onClick={() => setSelectedOutfit(outfit)}
                          className="bg-white/20 backdrop-blur-sm p-2 rounded-full hover:bg-white/30 transition-colors"
                          title="View Details"
                        >
                          <Eye className="w-4 h-4 text-white" />
                        </motion.button>
                        {outfit.tryOnPresignedUrl && (
                          <motion.button
                            whileHover={{ scale: 1.1 }}
                            whileTap={{ scale: 0.9 }}
                            onClick={() => updateUserPhoto(outfit.tryOnPresignedUrl!)}
                            className="bg-gradient-to-r from-purple-500/30 to-pink-500/30 backdrop-blur-sm p-2 rounded-full hover:from-purple-500/50 hover:to-pink-500/50 transition-all"
                            title="Use as Current Photo"
                          >
                            <Save className="w-4 h-4 text-white" />
                          </motion.button>
                        )}
                      </div>
                    </motion.div>
                  </div>

                  {/* Outfit Details */}
                  <div className="p-3">
                    <div className="flex items-center text-xs text-gray-500 mb-1">
                      <Calendar className="w-3 h-3 mr-1" />
                      {formatDate(outfit.createdAt)}
                    </div>
                    <p className="text-sm font-medium text-gray-800 capitalize">
                      {outfit.occasion || 'Virtual Try-On'}
                    </p>
                    <p className="text-xs text-gray-600 mt-1">
                      {outfit.items.length} item{outfit.items.length !== 1 ? 's' : ''}
                    </p>
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
      </div>

      {/* Outfit Detail Modal */}
      <AnimatePresence>
        {selectedOutfit && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
            onClick={() => setSelectedOutfit(null)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden"
            >
              <div className="bg-gradient-to-r from-purple-500 to-pink-500 p-6 text-white">
                <h3 className="text-xl font-bold">Outfit Details</h3>
                <p className="text-purple-100 text-sm">
                  Created {formatDate(selectedOutfit.createdAt)}
                </p>
              </div>
              
              <div className="p-6">
                {selectedOutfit.tryOnPresignedUrl && (
                  <div className="text-center mb-6">
                    <img
                      src={selectedOutfit.tryOnPresignedUrl}
                      alt="Outfit try-on"
                      className="w-48 h-64 object-cover mx-auto rounded-lg shadow-lg"
                    />
                  </div>
                )}
                
                <div className="space-y-4">
                  <div>
                    <h4 className="font-semibold text-gray-800 mb-2">Occasion</h4>
                    <p className="text-gray-600 capitalize">
                      {selectedOutfit.occasion || 'Virtual Try-On'}
                    </p>
                  </div>
                  
                  <div>
                    <h4 className="font-semibold text-gray-800 mb-2">Items</h4>
                    <p className="text-gray-600">
                      {selectedOutfit.items.length} clothing item{selectedOutfit.items.length !== 1 ? 's' : ''}
                    </p>
                  </div>
                  
                  {selectedOutfit.notes && (
                    <div>
                      <h4 className="font-semibold text-gray-800 mb-2">Notes</h4>
                      <p className="text-gray-600">{selectedOutfit.notes}</p>
                    </div>
                  )}
                </div>
                
                <div className="flex space-x-3 mt-6">
                  <button
                    onClick={() => setSelectedOutfit(null)}
                    className="flex-1 py-3 px-4 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                  >
                    Close
                  </button>
                  {selectedOutfit.tryOnPresignedUrl && (
                    <button
                      onClick={() => {
                        updateUserPhoto(selectedOutfit.tryOnPresignedUrl!);
                        setSelectedOutfit(null);
                      }}
                      className="flex-1 py-3 px-4 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg hover:shadow-lg transition-all"
                    >
                      Use as Current Photo
                    </button>
                  )}
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};