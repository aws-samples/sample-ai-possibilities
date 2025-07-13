import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useDropzone } from 'react-dropzone';
import { X, Upload, Check } from 'lucide-react';
import { User } from '../../types';
import { uploadClothingItem, imageToBase64 } from '../../services/api';
import toast from 'react-hot-toast';

interface UploadModalProps {
  user: User;
  onClose: () => void;
  onUploadComplete: () => void;
}

const categories = [
  { 
    id: 'top', 
    name: 'Top', 
    icon: '', 
    description: 'Shirts, blouses, sweaters',
    photoTips: [
      'Lay flat or hang straight - show full shape',
      'Sleeves spread out so cut and style are visible', 
      'Include neckline, collar, and any unique details',
      'White/light background makes colors pop',
      'Even lighting - avoid harsh shadows'
    ],
    example: 'Like a product photo - imagine it\'s for an online store'
  },
  { 
    id: 'bottom', 
    name: 'Bottom', 
    icon: '', 
    description: 'Pants, jeans, skirts',
    photoTips: [
      'Full length shot from waistband to hem',
      'Lay flat or fold neatly to show true shape',
      'Include waistband, pockets, and style details',
      'Straight-on angle - not tilted or angled',
      'Good lighting to show fabric texture'
    ],
    example: 'Think catalog style - show how they would actually fit'
  },
  { 
    id: 'dress', 
    name: 'Dress', 
    icon: '', 
    description: 'Dresses, gowns',
    photoTips: [
      'Complete dress from neckline to bottom hem',
      'Hanger or dress form shows best shape',
      'Display the silhouette and flow clearly',
      'Show fabric pattern, texture, and details',
      'Bright, even lighting for best colors'
    ],
    example: 'Like a fashion website - show the full garment beautifully'
  },
  { 
    id: 'outerwear', 
    name: 'Outerwear', 
    icon: '', 
    description: 'Jackets, coats',
    photoTips: [
      'Show both open and closed if it has closures',
      'Include buttons, zippers, hood details clearly',
      'Full length and cut - cropped or full jacket?',
      'Collar and lapel details visible',
      'Good angle to show the fit and style'
    ],
    example: 'Show it like you\'re selling it - all the important details'
  },
  { 
    id: 'shoes', 
    name: 'Shoes', 
    icon: '', 
    description: 'Sneakers, heels, boots',
    photoTips: [
      'Side profile shows shape and height best',
      'Top-down view for unique patterns/details',
      'Clean background so shoes stand out',
      'Both upper and sole should be visible',
      'Good lighting to show material and texture'
    ],
    example: 'Like sneaker photos online - clean and detailed'
  },
  { 
    id: 'accessory', 
    name: 'Accessory', 
    icon: '', 
    description: 'Bags, jewelry, belts',
    photoTips: [
      'Clean, simple background (white works great)',
      'Close enough to see details and texture',
      'Multiple angles if it helps show the item',
      'Good lighting to show true colors',
      'Show size reference if helpful'
    ],
    example: 'Product photography style - clean and professional'
  },
];

// Removed seasons and styles - Claude AI will analyze these automatically

export const UploadModal: React.FC<UploadModalProps> = ({ user, onClose, onUploadComplete }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [category, setCategory] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStep, setUploadStep] = useState<'select' | 'details' | 'uploading' | 'success'>('select');

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      setSelectedFile(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        setPreview(e.target?.result as string);
        setUploadStep('details');
      };
      reader.readAsDataURL(file);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png']  // Only JPEG and PNG for Nova Canvas compatibility
    },
    maxSize: 20 * 1024 * 1024, // 20MB to match backend validation
    multiple: false,
  });

  const handleUpload = async () => {
    if (!selectedFile || !category) return;

    setIsUploading(true);
    setUploadStep('uploading');

    try {
      const imageBase64 = await imageToBase64(selectedFile);
      
      console.log('=== Starting clothing item upload ===');
      console.log('User ID:', user.userId);
      console.log('Category:', category);
      console.log('Image size:', imageBase64.length);
      
      // Let Claude analyze the item - no need for manual attributes
      const result = await uploadClothingItem(user.userId, imageBase64, category);

      console.log('=== Upload result ===');
      console.log('Result:', result);
      console.log('Result type:', typeof result);
      console.log('Result success:', result?.success);
      console.log('Result message:', result?.message);

      // Check for validation errors in the response
      const responseText = result.message || '';
      
      if (responseText.includes('validation_error') || responseText.includes('errors')) {
        // Handle validation errors with helpful guidance
        const categoryName = categories.find(c => c.id === category)?.name || 'item';
        toast.error(`Photo needs improvement! Please retake following the ${categoryName} guidelines above.`, {
          duration: 6000,
        });
        setUploadStep('details');
        setIsUploading(false);
        return;
      }

      setUploadStep('success');
      
      // Show appropriate success message based on validation feedback
      if (responseText.includes('warnings') || responseText.includes('recommendations')) {
        toast.success('Item added! Photo could be better - see guidelines for perfect virtual try-ons.', {
          duration: 5000,
        });
      } else {
        toast.success('Perfect! Item added with great photo quality!', {
          duration: 4000,
        });
      }
      
      setTimeout(() => {
        onUploadComplete();
        onClose();
      }, 2500);
    } catch (error) {
      console.error('Upload error:', error);
      
      // Check if it's a validation error
      const errorMessage = error instanceof Error ? error.message : String(error);
      if (errorMessage.includes('validation') || errorMessage.includes('format') || errorMessage.includes('size')) {
        toast.error('Photo issue detected! Please check: JPEG/PNG format, good lighting, clear view of garment.', {
          duration: 6000,
        });
      } else {
        toast.error('Upload failed. Check your connection and try again.');
      }
      
      setUploadStep('details');
    } finally {
      setIsUploading(false);
    }
  };

  const resetForm = () => {
    setSelectedFile(null);
    setPreview(null);
    setCategory('');
    setUploadStep('select');
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
        className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden"
      >
        <div className="bg-gray-800 p-6 text-white">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-2xl font-bold">Add to Wardrobe</h2>
              <p className="text-gray-200 text-sm mt-1">
                Upload clear photos for the best virtual try-on experience
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/20 rounded-full transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(90vh-100px)]">
          <AnimatePresence mode="wait">
            {uploadStep === 'select' && (
              <motion.div
                key="select"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
              >
                <div
                  {...getRootProps()}
                  className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                    isDragActive
                      ? 'border-indigo-500 bg-indigo-50'
                      : 'border-gray-300 hover:border-indigo-400 hover:bg-gray-50'
                  }`}
                >
                  <input {...getInputProps()} />
                  <div className="flex flex-col items-center space-y-4">
                    <div className="p-4 bg-indigo-100 rounded-full">
                      <Upload className="w-12 h-12 text-indigo-600" />
                    </div>
                    <div>
                      <p className="text-lg font-semibold text-gray-900">
                        {isDragActive ? 'Drop your clothing photo here!' : 'Upload Clothing Photo'}
                      </p>
                      <p className="text-gray-500 mt-1">
                        Drag & drop or click to browse
                      </p>
                    </div>
                    <div className="space-y-2">
                      <p className="text-sm text-gray-600 font-medium">
                        Best photos show the full garment clearly
                      </p>
                      <p className="text-xs text-gray-400">
                        JPEG or PNG • Max 20MB • Auto-validated for virtual try-on
                      </p>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            {uploadStep === 'details' && (
              <motion.div
                key="details"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-6"
              >
                {/* Image Preview */}
                <div className="flex justify-center">
                  <div className="relative">
                    <img
                      src={preview || ''}
                      alt="Preview"
                      className="w-32 h-40 object-cover rounded-lg shadow-lg"
                    />
                    <button
                      onClick={resetForm}
                      className="absolute -top-2 -right-2 bg-red-500 text-white p-1 rounded-full hover:bg-red-600 transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Category Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    Category *
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    {categories.map((cat) => (
                      <button
                        key={cat.id}
                        onClick={() => setCategory(cat.id)}
                        className={`p-3 rounded-lg border-2 text-left transition-all ${
                          category === cat.id
                            ? 'border-indigo-500 bg-indigo-50'
                            : 'border-gray-200 hover:border-indigo-300'
                        }`}
                      >
                        <div className="flex items-center space-x-3">
                          <span className="text-2xl">{cat.icon}</span>
                          <div>
                            <p className="font-medium">{cat.name}</p>
                            <p className="text-xs text-gray-500">{cat.description}</p>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Enhanced Photo Tips for Selected Category */}
                {category && (
                  <div className="bg-gradient-to-br from-green-50 to-blue-50 border border-green-200 rounded-xl p-5">
                    <div className="flex items-center space-x-2 mb-3">
                      <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                        <span className="text-green-600 text-lg">+</span>
                      </div>
                      <div>
                        <h4 className="font-bold text-green-900">
                          Perfect {categories.find(c => c.id === category)?.name} Photos
                        </h4>
                        <p className="text-xs text-green-600 italic">
                          {categories.find(c => c.id === category)?.example}
                        </p>
                      </div>
                    </div>
                    
                    <div className="space-y-2">
                      {categories.find(c => c.id === category)?.photoTips.map((tip, index) => (
                        <div key={index} className="flex items-start space-x-2">
                          <span className="text-green-500 mt-0.5 flex-shrink-0">✓</span>
                          <span className="text-sm text-green-800">{tip}</span>
                        </div>
                      ))}
                    </div>
                    
                    <div className="mt-4 p-3 bg-white/50 rounded-lg border border-green-200">
                      <p className="text-xs text-green-700">
                        <span className="font-semibold">Pro tip:</span> Great photos = better AI analysis = more accurate virtual try-ons!
                      </p>
                    </div>
                  </div>
                )}

                {/* AI Analysis Notice */}
                <div className="bg-gradient-to-br from-indigo-50 to-blue-50 border border-indigo-200 rounded-xl p-5">
                  <div className="flex items-center space-x-3 mb-3">
                    <div className="w-10 h-10 bg-gradient-to-r from-indigo-600 to-blue-600 rounded-full flex items-center justify-center">
                      <span className="text-white text-xl">AI</span>
                    </div>
                    <div>
                      <h4 className="font-bold text-indigo-900">
                        AI-Powered Analysis
                      </h4>
                      <p className="text-sm text-indigo-600">
                        Our AI will automatically detect colors, style, season, and more!
                      </p>
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <span className="text-indigo-500">•</span>
                      <span className="text-sm text-indigo-800">Analyzes colors and patterns</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-indigo-500">•</span>
                      <span className="text-sm text-indigo-800">Identifies style and formality level</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-indigo-500">•</span>
                      <span className="text-sm text-indigo-800">Determines seasonal appropriateness</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-indigo-500">•</span>
                      <span className="text-sm text-indigo-800">Suggests outfit combinations</span>
                    </div>
                  </div>
                  
                  <div className="mt-4 p-3 bg-white/50 rounded-lg border border-indigo-200">
                    <p className="text-xs text-indigo-700">
                      <span className="font-semibold">Just select the category and upload!</span> Our AI handles the rest for perfect wardrobe organization.
                    </p>
                  </div>
                </div>

                <div className="flex space-x-3">
                  <button
                    onClick={resetForm}
                    className="flex-1 py-3 px-4 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                  >
                    Change Image
                  </button>
                  <button
                    onClick={handleUpload}
                    disabled={!category || isUploading}
                    className="flex-1 py-3 px-4 bg-gradient-to-r from-indigo-600 to-indigo-700 text-white rounded-lg hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Add to Wardrobe
                  </button>
                </div>
              </motion.div>
            )}

            {uploadStep === 'uploading' && (
              <motion.div
                key="uploading"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="text-center py-8"
              >
                <div className="flex justify-center mb-4">
                  <div className="animate-spin rounded-full h-16 w-16 border-4 border-indigo-500 border-t-transparent"></div>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Uploading your item...
                </h3>
                <p className="text-gray-600">
                  Claude is analyzing your clothing item
                </p>
              </motion.div>
            )}

            {uploadStep === 'success' && (
              <motion.div
                key="success"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="text-center py-8"
              >
                <div className="flex justify-center mb-4">
                  <div className="p-4 bg-green-100 rounded-full">
                    <Check className="w-12 h-12 text-green-500" />
                  </div>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Item added successfully!
                </h3>
                <p className="text-gray-600">
                  Your wardrobe has been updated
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </motion.div>
  );
};