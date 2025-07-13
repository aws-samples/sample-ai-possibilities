import React, { useState, useEffect } from 'react';
import { Toaster } from 'react-hot-toast';
import toast from 'react-hot-toast';
import { motion, AnimatePresence } from 'framer-motion';
import './App.css';
import './styles/wardrobe-theme.css';
import './styles/modern-fashion-theme.css';
import { User, WardrobeItem } from './types';
import { UserProfile } from './components/Profile/UserProfile';
import { ModernUserProfile } from './components/Profile/ModernUserProfile';
import { AdaptivePortrait } from './components/Profile/AdaptivePortrait';
import { Wardrobe } from './components/Wardrobe/Wardrobe';
import { ModernWardrobe } from './components/Wardrobe/ModernWardrobe';
import { Chat } from './components/Chat/Chat';
import { SimpleChat } from './components/Chat/SimpleChat';
import { OutfitGallery } from './components/Outfits/OutfitGallery';
import { ModernOutfitGallery } from './components/Outfits/ModernOutfitGallery';
import { OutfitBuilder } from './components/Wardrobe/OutfitBuilder';
import { ModernOutfitBuilder } from './components/Wardrobe/ModernOutfitBuilder';
import { ModernHeader } from './components/UI/ModernHeader';
import { registerUser, saveOutfit, createVirtualTryOnWithStyle } from './services/api';

function App() {
  // User authentication and profile state
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [needsPhoto, setNeedsPhoto] = useState(false);
  const [pendingUserName, setPendingUserName] = useState<string>('');
  
  // Virtual try-on state management
  const [currentTryOnImage, setCurrentTryOnImage] = useState<string | null>(null);
  const [currentOutfitData, setCurrentOutfitData] = useState<any>(null);
  const [outfitGalleryKey, setOutfitGalleryKey] = useState(0);
  const [shouldExpandArchive, setShouldExpandArchive] = useState(false);
  const [newOutfitId, setNewOutfitId] = useState<string | null>(null);
  
  // Outfit builder state
  const [outfitBuilder, setOutfitBuilder] = useState<{
    top?: { itemId: string; name: string; imageUrl: string };
    bottom?: { itemId: string; name: string; imageUrl: string };
    dress?: { itemId: string; name: string; imageUrl: string };
    outerwear?: { itemId: string; name: string; imageUrl: string };
    shoes?: { itemId: string; name: string; imageUrl: string };
    accessory?: { itemId: string; name: string; imageUrl: string };
  }>({});
  const [isBuilderMode, setIsBuilderMode] = useState(false);
  const [isApplyingOutfit, setIsApplyingOutfit] = useState(false);
  const [isPortraitMinimized, setIsPortraitMinimized] = useState(false);

  // Check if user exists in localStorage
  useEffect(() => {
    let savedUser = localStorage.getItem('ai-unicorn-wardrobe-user');
    
    // Fallback: check old key if new key doesn't exist
    if (!savedUser) {
      savedUser = localStorage.getItem('ai-wardrobe-user');
      if (savedUser) {
        console.log('DEBUG - Found user in old localStorage, migrating...');
        // Migrate to new key
        localStorage.setItem('ai-unicorn-wardrobe-user', savedUser);
        localStorage.removeItem('ai-wardrobe-user');
      }
    }
    
    console.log('DEBUG - localStorage check on load:');
    console.log('  savedUser exists:', !!savedUser);
    console.log('  savedUser content:', savedUser);
    
    if (savedUser) {
      try {
        const parsedUser = JSON.parse(savedUser);
        console.log('  parsed user:', parsedUser);
        console.log('  parsed user has photo?:', !!parsedUser.profilePhoto);
        console.log('  parsed user photo length:', parsedUser.profilePhoto?.length);
        setUser(parsedUser);
      } catch (error) {
        console.error('  Failed to parse saved user:', error);
        localStorage.removeItem('ai-unicorn-wardrobe-user'); // Clean up corrupted data
      }
    }
  }, []);

  // Verify if a user already exists in the system and handle profile setup
  const checkUserExistence = async (userName: string) => {
    setIsLoading(true);
    try {
      // Check if user exists by calling the API without a photo
      const response = await registerUser(userName);
      const responseMessage = response.message || '';
      const userData = response.user;
      
      console.log('User check response:', { response, userData, responseMessage });
      
      // Check if user exists and has a photo
      const isExistingUser = userData && (
        response.status === 'existing' ||
        responseMessage.includes('existing') || 
        responseMessage.includes('Welcome back') || 
        responseMessage.includes('Found existing')
      );
      
      const hasExistingPhoto = userData?.profilePhotoBase64 || userData?.profilePhotoUrl;
      
      console.log('User existence check:', { isExistingUser, hasExistingPhoto });
      
      if (isExistingUser && hasExistingPhoto) {
        // User exists with photo - log them in directly
        const newUser: User = {
          userId: userData.userId,
          userName,
          createdAt: userData?.createdAt || new Date().toISOString(),
          wardrobeItems: userData?.wardrobeItems || [],
          profilePhoto: userData?.profilePhotoBase64,
        };
        
        console.log('Logging in existing user with photo:', newUser);
        setUser(newUser);
        localStorage.setItem('ai-unicorn-wardrobe-user', JSON.stringify(newUser));
        toast.success(`👋 Welcome back, ${userName}! Your profile has been loaded.`, {
          duration: 5000,
        });
        setIsLoading(false);
        return;
      } else if (isExistingUser && !hasExistingPhoto) {
        // User exists but needs photo
        console.log('Existing user needs photo');
        setNeedsPhoto(true);
        setPendingUserName(userName);
        setIsLoading(false);
        toast.success(`👋 Welcome back, ${userName}! Please add a profile photo for virtual try-ons.`, {
          duration: 5000,
        });
        return;
      } else {
        // New user - needs photo
        console.log('New user detected, needs photo');
        setNeedsPhoto(true);
        setPendingUserName(userName);
        setIsLoading(false);
        return;
      }
    } catch (error) {
      console.error('Error checking user existence:', error);
      // Assume new user if check fails
      setNeedsPhoto(true);
      setPendingUserName(userName);
      setIsLoading(false);
    }
  };

  const handleUserRegistration = async (userName: string, userPhoto?: string) => {
    console.log('=== handleUserRegistration called ===', { userName, hasPhoto: !!userPhoto });
    setIsLoading(true);
    try {
      console.log('Making registration request with:', { userName, hasPhoto: !!userPhoto });
      const response = await registerUser(userName, userPhoto);
      console.log('Registration response:', response);
      console.log('Response type:', typeof response);
      console.log('Response success:', response?.success);
      
      // Check for validation errors in the response
      const responseMessage = response.message || '';
      
      if (responseMessage.includes('validation_error') || responseMessage.includes('errors')) {
        // Handle validation errors with helpful guidance
        toast.error('📸 Profile photo needs improvement! Please retake following the guidelines: upper body visible, good lighting, plain background.', {
          duration: 7000,
        });
        setIsLoading(false);
        return;
      }
      
      // Debug: Log the actual response to see what we're getting
      console.log('Registration response message:', responseMessage);
      console.log('Full response object:', response);
      console.log('DEBUG - Response user data:', response.user);
      console.log('DEBUG - User has profilePhotoBase64?:', !!response.user?.profilePhotoBase64);
      
      // Check if the response indicates success
      if (response.success) {
        // Try to extract user data from response
        let userData = null;
        let userId = null;
        
        // First try to get user data from response.user if available
        if (response.user) {
          userData = response.user;
          userId = userData.userId;
        } else {
          // Fallback: try to extract user ID from message
          const userIdMatch1 = responseMessage.match(/User ID: ([a-fA-F0-9-]+)/);
          if (userIdMatch1) {
            userId = userIdMatch1[1];
          } else {
            const userIdMatch2 = responseMessage.match(/([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})/);
            if (userIdMatch2) {
              userId = userIdMatch2[1];
            }
          }
        }
        
        if (userId) {
          // Check if user exists (simplified since we now handle this in checkUserExistence)
          const isExistingUser = userData && (
            response.status === 'existing' ||
            responseMessage.includes('existing') || 
            responseMessage.includes('Welcome back') || 
            responseMessage.includes('Found existing')
          );
          
          const newUser: User = {
            userId: userId,
            userName,
            createdAt: userData?.createdAt || new Date().toISOString(),
            wardrobeItems: userData?.wardrobeItems || [],
            // Use existing profile photo from backend if available, otherwise use uploaded photo
            profilePhoto: userData?.profilePhotoBase64 || userPhoto,
          };
          
          console.log('DEBUG - Final user object:');
          console.log('  newUser.profilePhoto exists:', !!newUser.profilePhoto);
          console.log('  newUser.profilePhoto length:', newUser.profilePhoto?.length);
          console.log('  newUser:', newUser);
          
          setUser(newUser);
          setNeedsPhoto(false);
          localStorage.setItem('ai-unicorn-wardrobe-user', JSON.stringify(newUser));
          
          // Debug logging for UI issue investigation
          console.log('DEBUG - Photo and user data:');
          console.log('  userData exists:', !!userData);
          console.log('  userData:', userData);
          console.log('  userData.profilePhotoBase64 exists:', !!userData?.profilePhotoBase64);
          console.log('  userData.profilePhotoBase64 length:', userData?.profilePhotoBase64?.length);
          console.log('  userPhoto (uploaded):', !!userPhoto);
          console.log('  responseMessage:', responseMessage);
          console.log('  isExistingUser:', isExistingUser);
          
          if (isExistingUser) {
            toast.success(`👋 Welcome back, ${userName}! Your profile has been loaded.`, {
              duration: 5000,
            });
          } else if (responseMessage.includes('warnings') || responseMessage.includes('recommendations')) {
            toast.success(`🎉 Welcome ${userName}! Your photo works, but could be better for virtual try-ons. See guidelines for tips!`, {
              duration: 6000,
            });
          } else {
            toast.success(`🌟 Perfect! Welcome ${userName}! Your photo is ideal for virtual try-ons.`, {
              duration: 5000,
            });
          }
        } else {
          console.error('Could not extract user ID from response:', response);
          toast.error('Registration completed but there was an issue setting up your profile. Please try again.');
        }
      } else {
        console.error('API response indicates failure:', response);
        toast.error('Registration failed. Please try again.');
      }
    } catch (error) {
      console.error('Registration error:', error);
      
      // Check if it's a validation error
      const errorMessage = error instanceof Error ? error.message : String(error);
      if (errorMessage.includes('validation') || errorMessage.includes('format') || errorMessage.includes('size')) {
        toast.error('📸 Profile photo issue! Please use JPEG/PNG format, good lighting, and show your upper body clearly.', {
          duration: 7000,
        });
      } else {
        toast.error('❌ Connection error. Make sure the API server is running and try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('ai-unicorn-wardrobe-user');
  };

  const handleTryOnResult = (tryOnImageUrl: string, outfitData: any, source?: string) => {
    console.log('=== App.tsx handleTryOnResult called ===');
    console.log('  tryOnImageUrl:', tryOnImageUrl);
    console.log('  outfitData:', outfitData);
    console.log('  source:', source);
    console.log('  outfitData items length:', outfitData?.items?.length);
    
    setCurrentTryOnImage(tryOnImageUrl);
    setCurrentOutfitData(outfitData);
    
    // If this is from a chat-triggered multi-item outfit, prepare to expand archive
    if (source === 'chat' && outfitData?.items?.length > 1) {
      console.log('  Setting shouldExpandArchive to true (chat multi-item)');
      setShouldExpandArchive(true);
    } else {
      console.log('  NOT expanding archive - source:', source, 'items length:', outfitData?.items?.length);
    }
    console.log('=== End App.tsx handleTryOnResult ===');
  };

  const handleSaveOutfit = async () => {
    if (!currentOutfitData || !user) {
      toast.error('No outfit to save');
      return;
    }

    try {
      console.log('Saving outfit:', currentOutfitData);
      
      const response = await saveOutfit({
        userId: user.userId,
        items: currentOutfitData.items,
        occasion: currentOutfitData.occasion || 'virtual_try_on',
        notes: 'Saved from virtual try-on'
      });

      // Extract outfit ID from response if available
      const savedOutfitId = response?.outfitId || response?.data?.outfitId;
      
      setCurrentTryOnImage(null);
      setCurrentOutfitData(null);
      setOutfitGalleryKey(prev => prev + 1); // Trigger OutfitGallery refresh
      
      // Auto-expand archive and highlight new outfit
      setShouldExpandArchive(true);
      setNewOutfitId(savedOutfitId);
      
      // Show enhanced success message with archive reference
      const isMultiItem = currentOutfitData.items?.length > 1;
      if (isMultiItem) {
        toast.success('✨ Multi-item outfit saved! Check your Outfit Archive below.', {
          duration: 6000,
        });
      } else {
        toast.success('✨ Outfit saved to your archive!');
      }
    } catch (error) {
      console.error('Error saving outfit:', error);
      toast.error('Failed to save outfit. Please try again.');
    }
  };

  const handleCancelTryOn = () => {
    setCurrentTryOnImage(null);
    setCurrentOutfitData(null);
  };

  // Outfit builder handlers
  const handleAddToOutfit = (item: WardrobeItem) => {
    console.log('handleAddToOutfit called with:', item);
    const category = item.category as keyof typeof outfitBuilder;
    
    // Check for dress/separates conflict
    if (category === 'dress' && (outfitBuilder.top || outfitBuilder.bottom)) {
      toast.error('Remove top/bottom pieces before adding a dress');
      return;
    }
    if ((category === 'top' || category === 'bottom') && outfitBuilder.dress) {
      toast.error('Remove dress before adding separate pieces');
      return;
    }
    
    setOutfitBuilder(prev => ({
      ...prev,
      [category]: {
        itemId: item.itemId,
        name: item.attributes?.description || `${category} item`,
        imageUrl: item.presignedUrl || '',
      }
    }));
    
    toast.success(`Added ${category} to outfit`);
  };

  const handleRemoveFromOutfit = (category: string) => {
    setOutfitBuilder(prev => {
      const newOutfit = { ...prev };
      delete newOutfit[category as keyof typeof outfitBuilder];
      return newOutfit;
    });
  };

  const handleClearOutfit = () => {
    setOutfitBuilder({});
    toast.success('Outfit cleared');
  };

  const handleToggleBuilderMode = () => {
    setIsBuilderMode(!isBuilderMode);
    if (!isBuilderMode) {
      toast.success('Outfit builder activated! Click items to add them.');
    }
  };

  // Convert image URLs to base64 for chaining multiple virtual try-ons
  const urlToBase64 = async (url: string): Promise<string> => {
    try {
      const response = await fetch(url);
      const blob = await response.blob();
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const base64 = reader.result as string;
          // Extract just the base64 data without the prefix
          const base64Data = base64.split(',')[1];
          resolve(base64Data);
        };
        reader.onerror = reject;
        reader.readAsDataURL(blob);
      });
    } catch (error) {
      console.error('Error converting URL to base64:', error);
      throw error;
    }
  };

  const handleApplyOutfit = async () => {
    if (!user || Object.keys(outfitBuilder).length === 0) return;
    
    setIsApplyingOutfit(true);
    const loadingToast = toast.loading('Applying outfit pieces...');
    
    try {
      // Define the order in which to apply items
      const applicationOrder = ['dress', 'top', 'bottom', 'outerwear', 'shoes', 'accessory'];
      const itemsToApply = applicationOrder
        .filter(category => outfitBuilder[category as keyof typeof outfitBuilder])
        .map(category => ({
          category,
          item: outfitBuilder[category as keyof typeof outfitBuilder]!
        }));
      
      if (itemsToApply.length === 0) {
        toast.dismiss(loadingToast);
        toast.error('No items to apply');
        return;
      }
      
      let currentImageBase64: string | null = null; // Start with null to use profile photo
      let currentImageUrl: string | null = null; // Track final URL for display
      let allItemIds: string[] = [];
      
      // Apply items sequentially
      for (let i = 0; i < itemsToApply.length; i++) {
        const { category, item } = itemsToApply[i];
        allItemIds.push(item.itemId);
        
        toast.dismiss(loadingToast);
        toast.loading(`Applying ${category} (${i + 1}/${itemsToApply.length})...`, { id: loadingToast });
        
        console.log(`=== Frontend calling try-on API (${i + 1}/${itemsToApply.length}) ===`);
        console.log(`  category: ${category}`);
        console.log(`  item.itemId: ${item.itemId}`);
        console.log(`  currentImageBase64 length: ${currentImageBase64?.length || 0}`);
        console.log(`  using profile photo: ${!currentImageBase64}`);
        
        const response: any = await createVirtualTryOnWithStyle(
          user.userId,
          currentImageBase64 || '', // Use base64 from previous try-on or empty string for profile photo
          item.itemId,
          category,
          {
            sleeveStyle: 'default',
            tuckingStyle: 'default',
            outerLayerStyle: category === 'outerwear' ? 'open' : 'default'
          }
        );
        
        if (response.data?.tryOnImageUrl) {
          currentImageUrl = response.data.tryOnImageUrl;
          
          // Convert URL to base64 for next iteration (if not the last item)
          if (i < itemsToApply.length - 1) {
            try {
              console.log(`=== Converting URL to base64 for next item ===`);
              console.log(`  URL: ${response.data.tryOnImageUrl}`);
              currentImageBase64 = await urlToBase64(response.data.tryOnImageUrl);
              console.log(`  Converted base64 length: ${currentImageBase64.length}`);
            } catch (conversionError) {
              console.warn('Failed to convert image for chaining, will use profile photo for next item:', conversionError);
              currentImageBase64 = null; // Fallback to profile photo
            }
          }
        } else {
          throw new Error(`Failed to apply ${category}`);
        }
      }
      
      toast.dismiss(loadingToast);
      
      if (currentImageUrl) {
        // Update the display with the final result
        const outfitData = {
          items: allItemIds,
          occasion: 'custom_outfit',
          categories: itemsToApply.map(i => i.category)
        };
        
        setCurrentTryOnImage(currentImageUrl);
        setCurrentOutfitData(outfitData);
        
        // Mark this as a builder-created multi-item outfit for archive expansion
        setShouldExpandArchive(true);
        
        toast.success('✨ Complete outfit applied!');
      }
      
    } catch (error) {
      console.error('Error applying outfit:', error);
      toast.dismiss(loadingToast);
      toast.error('Failed to apply outfit. Please try again.');
    } finally {
      setIsApplyingOutfit(false);
    }
  };

  return (
    <div className="App min-h-screen fashion-background">
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'var(--fashion-primary)',
            color: '#fff',
            border: '1px solid var(--fashion-secondary)',
            borderRadius: 'var(--fashion-radius-md)',
            fontFamily: 'var(--fashion-font-body)',
          },
        }}
      />
      
      <AnimatePresence mode="wait">
        {!user ? (
          <motion.div
            key="login"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="min-h-screen fashion-background flex items-center justify-center p-4"
          >
            {(() => {
              console.log('Rendering UserProfile with props:', {
                needsPhoto,
                pendingUserName,
                isLoading,
                hasCheckUser: !!checkUserExistence
              });
              return null;
            })()}
            <ModernUserProfile 
              onRegister={handleUserRegistration} 
              onCheckUser={checkUserExistence}
              isLoading={isLoading} 
              needsPhoto={needsPhoto}
              userName={pendingUserName}
            />
          </motion.div>
        ) : (
          <motion.div
            key="app"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="min-h-screen"
          >
            <ModernHeader user={user} onLogout={handleLogout} />

            {/* Floating Sticky Portrait - Outside Grid */}
            {user.profilePhoto && (
              <>
                {/* Portrait Container */}
                <div className={`floating-portrait-container ${isPortraitMinimized ? 'minimized' : ''}`}>
                  <div className="virtual-tryon-preview">
                    {!isPortraitMinimized && (
                      <AdaptivePortrait
                        src={currentTryOnImage || `data:image/jpeg;base64,${user.profilePhoto}`}
                        alt={currentTryOnImage ? `${user.userName}'s virtual try-on` : `${user.userName}'s portrait`}
                        userName={user.userName}
                        showTryOnLabel={!!currentTryOnImage}
                      />
                    )}
                    
                    {/* Modern Try-on controls */}
                    {currentTryOnImage && !isPortraitMinimized && (
                      <div className="virtual-tryon-controls">
                        <button
                          onClick={handleSaveOutfit}
                          className="btn-fashion-primary"
                        >
                          Save Look
                        </button>
                        <button
                          onClick={handleCancelTryOn}
                          className="btn-fashion-secondary"
                        >
                          Try Again
                        </button>
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Toggle Button - Independent positioning */}
                <button
                  onClick={() => setIsPortraitMinimized(!isPortraitMinimized)}
                  className={`portrait-toggle-btn ${isPortraitMinimized ? 'minimized' : ''}`}
                  title={isPortraitMinimized ? 'Expand profile photo' : 'Minimize profile photo'}
                >
                </button>
              </>
            )}

            <main className="w-full max-w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 overflow-x-hidden">
              <div className={`fashion-grid fashion-grid-main fashion-grid-no-portrait ${isPortraitMinimized ? 'portrait-minimized' : ''}`}>
                {/* Wardrobe & Outfit Builder Section */}
                <div className="space-y-6">
                  <ModernOutfitBuilder
                    outfit={outfitBuilder}
                    isBuilderMode={isBuilderMode}
                    onRemoveItem={handleRemoveFromOutfit}
                    onApplyOutfit={handleApplyOutfit}
                    onClearOutfit={handleClearOutfit}
                    onToggleMode={handleToggleBuilderMode}
                    isApplying={isApplyingOutfit}
                  />
                  <ModernWardrobe 
                    user={user} 
                    onTryOnResult={handleTryOnResult}
                    isBuilderMode={isBuilderMode}
                    onAddToOutfit={handleAddToOutfit}
                  />
                </div>
                {/* AI Chat Assistant */}
                <div>
                  <SimpleChat user={user} onTryOnResult={handleTryOnResult} />
                </div>
              </div>

              {/* Bottom Row: Outfit Archive */}
              <div className="mt-8">
                <ModernOutfitGallery 
                  key={outfitGalleryKey} 
                  user={user} 
                  shouldExpand={shouldExpandArchive}
                  newOutfitId={newOutfitId}
                  onExpanded={() => {
                    setShouldExpandArchive(false);
                    setNewOutfitId(null);
                  }}
                />
              </div>
            </main>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
