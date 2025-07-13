import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { User, Sparkles, Camera, Upload, ArrowRight, Check, X } from 'lucide-react';
import { useDropzone } from 'react-dropzone';

interface UserProfileProps {
  onRegister: (userName: string, userPhoto?: string) => void;
  onCheckUser?: (userName: string) => void;
  isLoading: boolean;
  needsPhoto?: boolean;
  userName?: string;
}

type RegistrationStep = 'name' | 'photo' | 'creating';

export const UserProfile: React.FC<UserProfileProps> = ({ onRegister, onCheckUser, isLoading, needsPhoto, userName: initialUserName }) => {
  const [userName, setUserName] = useState(initialUserName || '');
  const [userPhoto, setUserPhoto] = useState<string | null>(null);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [step, setStep] = useState<RegistrationStep>(needsPhoto ? 'photo' : 'name');
  
  console.log('UserProfile render:', { needsPhoto, hasCheckUser: !!onCheckUser, step, initialUserName });

  // Update step if needsPhoto changes
  React.useEffect(() => {
    if (needsPhoto) {
      setStep('photo');
      if (initialUserName) {
        setUserName(initialUserName);
      }
    }
  }, [needsPhoto, initialUserName]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      setPhotoFile(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        setUserPhoto(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.webp']
    },
    maxSize: 10 * 1024 * 1024, // 10MB
    multiple: false,
  });

  const handleNameSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (userName.trim()) {
      setStep('creating');
      console.log('UserProfile handleNameSubmit:', { 
        hasCheckUser: !!onCheckUser, 
        needsPhoto, 
        willCallCheckUser: onCheckUser && !needsPhoto 
      });
      // If we have a checkUser function and we're not in photo mode, check user first
      if (onCheckUser && !needsPhoto) {
        console.log('Calling onCheckUser');
        onCheckUser(userName.trim());
      } else {
        console.log('Calling onRegister');
        // Otherwise use the regular registration flow
        onRegister(userName.trim());
      }
    }
  };

  const handlePhotoSubmit = async () => {
    setStep('creating');
    // Convert photo to base64 if available
    let photoBase64: string | undefined;
    if (photoFile) {
      const reader = new FileReader();
      photoBase64 = await new Promise((resolve) => {
        reader.onload = (e) => {
          const base64 = e.target?.result as string;
          resolve(base64.split(',')[1]); // Remove data:image/...;base64, prefix
        };
        reader.readAsDataURL(photoFile);
      });
    }
    onRegister(userName.trim(), photoBase64);
  };


  return (
    <motion.div
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="wardrobe-door rounded-2xl shadow-2xl p-8 w-full max-w-md"
    >
      <AnimatePresence mode="wait">
        {(step === 'name' || step === 'creating') && (
          <motion.div
            key="name-step"
            initial={{ opacity: 0, x: 0 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
          >
            <div className="text-center mb-8">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
                className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-amber-600 to-amber-800 rounded-full mb-4 shadow-lg" style={{
                  boxShadow: 'inset 0 2px 4px rgba(255,255,255,0.3), 0 4px 8px rgba(0,0,0,0.3)'
                }}
              >
                <Sparkles className="w-10 h-10 text-white" />
              </motion.div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">AI Wardrobe</h1>
              <p className="text-gray-600">
                {step === 'creating' ? 'Setting up your wardrobe...' : 'Your personal AI fashion assistant'}
              </p>
            </div>

            {step === 'name' && (
              <form onSubmit={handleNameSubmit} className="space-y-6">
                <div>
                  <label htmlFor="userName" className="block text-sm font-medium text-gray-700 mb-2">
                    What's your name?
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <User className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      type="text"
                      id="userName"
                      value={userName}
                      onChange={(e) => setUserName(e.target.value)}
                      className="block w-full pl-10 pr-3 py-3 border border-amber-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent transition-all bg-white/90"
                      placeholder="Enter your name"
                      required
                      disabled={isLoading}
                    />
                  </div>
                </div>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  type="submit"
                  disabled={!userName.trim()}
                  className="w-full py-3 px-4 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                  style={{
                    background: 'linear-gradient(135deg, var(--wardrobe-brass) 0%, #996515 100%)',
                    boxShadow: 'inset 0 1px 2px rgba(255,255,255,0.3), 0 2px 4px rgba(0,0,0,0.3)'
                  }}
                >
                  Next
                  <ArrowRight className="w-5 h-5 ml-2" />
                </motion.button>
              </form>
            )}

            {step === 'creating' && (
              <div className="text-center py-8">
                <div className="flex justify-center mb-4">
                  <div className="animate-spin rounded-full h-16 w-16 border-4 border-purple-500 border-t-transparent"></div>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Building your AI Wardrobe...
                </h3>
                <p className="text-gray-600">
                  This will just take a moment
                </p>
              </div>
            )}

            <p className="text-center text-sm text-gray-500 mt-6">
              Build your virtual wardrobe and get AI-powered outfit recommendations
            </p>
          </motion.div>
        )}

        {step === 'photo' && (
          <motion.div
            key="photo-step"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
          >
            <div className="text-center mb-6">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 200 }}
                className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-amber-600 to-amber-800 rounded-full mb-4 shadow-lg" style={{
                  boxShadow: 'inset 0 2px 4px rgba(255,255,255,0.3), 0 4px 8px rgba(0,0,0,0.3)'
                }}
              >
                <Camera className="w-8 h-8 text-white" />
              </motion.div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Upload Your Photo</h2>
              <p className="text-gray-600 text-sm mb-3">
                Your photo is used for virtual try-ons - the better the photo, the better the results!
              </p>
              
              {/* Enhanced Photo Guidelines */}
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-4 mb-4">
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                      <span className="text-blue-600 text-lg">📸</span>
                    </div>
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-blue-900 mb-2">Perfect Virtual Try-On Photo:</h3>
                    <div className="grid grid-cols-1 gap-2 text-sm">
                      <div className="flex items-center space-x-2">
                        <span className="text-green-500">✓</span>
                        <span className="text-blue-700"><strong>Show upper body:</strong> From waist up, arms visible</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="text-green-500">✓</span>
                        <span className="text-blue-700"><strong>Face the camera:</strong> Look straight ahead</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="text-green-500">✓</span>
                        <span className="text-blue-700"><strong>Portrait orientation:</strong> Taller than wide (vertical photo)</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="text-green-500">✓</span>
                        <span className="text-blue-700"><strong>Good lighting:</strong> Bright, even light (no shadows)</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="text-green-500">✓</span>
                        <span className="text-blue-700"><strong>Plain background:</strong> White wall or simple backdrop</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="text-green-500">✓</span>
                        <span className="text-blue-700"><strong>Fitted clothing:</strong> Shows your body shape clearly</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* What to Avoid */}
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
                <h4 className="font-medium text-red-800 mb-1 flex items-center">
                  <span className="mr-2">⚠️</span>
                  Avoid these for best results:
                </h4>
                <div className="text-xs text-red-600 space-y-1">
                  <div>• Dark or poorly lit photos</div>
                  <div>• Busy backgrounds or patterns</div>
                  <div>• Loose, baggy clothing that hides your shape</div>
                  <div>• Angled or tilted poses</div>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              {!userPhoto ? (
                <div
                  {...getRootProps()}
                  className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                    isDragActive
                      ? 'border-purple-500 bg-purple-50'
                      : 'border-gray-300 hover:border-purple-400 hover:bg-gray-50'
                  }`}
                >
                  <input {...getInputProps()} />
                  <Upload className="w-10 h-10 text-gray-400 mx-auto mb-3" />
                  <p className="text-sm font-medium text-gray-700">
                    {isDragActive ? '📱 Drop your photo here!' : '📱 Click or drag to upload your photo'}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    JPEG or PNG • Max 20MB • Auto-validated for virtual try-on
                  </p>
                  <p className="text-xs text-green-600 mt-1 font-medium">
                    💡 Tip: Take a new selfie following the guidelines above for best results!
                  </p>
                </div>
              ) : (
                <div className="relative mx-auto w-fit">
                  <div className="relative p-3 bg-gradient-to-br from-amber-100 to-amber-200 rounded-xl shadow-lg">
                    <div className="absolute inset-0 bg-gradient-to-br from-yellow-400/20 to-amber-600/20 rounded-xl"></div>
                    <img
                      src={userPhoto}
                      alt="Your photo"
                      className="relative w-32 h-32 object-cover rounded-lg shadow-md border-2 border-amber-300"
                    />
                    <div className="absolute -top-1 -right-1 w-6 h-6 bg-amber-500 rounded-full shadow-md transform rotate-12"></div>
                    <div className="absolute -bottom-1 -left-1 w-4 h-4 bg-amber-600 rounded-full shadow-md"></div>
                  </div>
                  <button
                    onClick={() => {
                      setUserPhoto(null);
                      setPhotoFile(null);
                    }}
                    className="absolute -top-2 -right-2 bg-red-500 text-white p-1.5 rounded-full hover:bg-red-600 transition-colors shadow-lg"
                  >
                    <X className="w-4 h-4" />
                  </button>
                  <p className="text-center text-sm text-amber-700 mt-2 font-medium">Perfect for virtual try-ons!</p>
                </div>
              )}

              <div className="space-y-3">
                {userPhoto && (
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handlePhotoSubmit}
                    className="w-full py-3 px-4 text-white font-semibold rounded-lg shadow-md hover:shadow-lg transition-all flex items-center justify-center"
                    style={{
                      background: 'linear-gradient(135deg, var(--wardrobe-brass) 0%, #996515 100%)',
                      boxShadow: 'inset 0 1px 2px rgba(255,255,255,0.3), 0 2px 4px rgba(0,0,0,0.3)'
                    }}
                  >
                    <Check className="w-5 h-5 mr-2" />
                    Continue with this photo
                  </motion.button>
                )}
                
                {/* Photo is mandatory - no skip option */}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};