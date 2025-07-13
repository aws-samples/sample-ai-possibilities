import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Camera, Upload, ArrowRight, Check, X, User as UserIcon } from 'lucide-react';
import { useDropzone } from 'react-dropzone';

interface ModernUserProfileProps {
  onRegister: (userName: string, userPhoto?: string) => void;
  onCheckUser?: (userName: string) => void;
  isLoading: boolean;
  needsPhoto?: boolean;
  userName?: string;
}

type RegistrationStep = 'name' | 'photo' | 'creating';

export const ModernUserProfile: React.FC<ModernUserProfileProps> = ({ 
  onRegister, 
  onCheckUser, 
  isLoading, 
  needsPhoto, 
  userName: initialUserName 
}) => {
  const [userName, setUserName] = useState(initialUserName || '');
  const [userPhoto, setUserPhoto] = useState<string | null>(null);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [step, setStep] = useState<RegistrationStep>(needsPhoto ? 'photo' : 'name');

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
    maxSize: 10 * 1024 * 1024,
    multiple: false,
  });

  const handleNameSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (userName.trim()) {
      setStep('creating');
      if (onCheckUser && !needsPhoto) {
        onCheckUser(userName.trim());
      } else {
        onRegister(userName.trim());
      }
    }
  };

  const handlePhotoSubmit = async () => {
    setStep('creating');
    let photoBase64: string | undefined;
    if (photoFile) {
      const reader = new FileReader();
      photoBase64 = await new Promise((resolve) => {
        reader.onload = (e) => {
          const base64 = e.target?.result as string;
          resolve(base64.split(',')[1]);
        };
        reader.readAsDataURL(photoFile);
      });
    }
    onRegister(userName.trim(), photoBase64);
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 fashion-background">
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        {/* Hero Section */}
        <div className="text-center mb-8">
          <motion.div
            initial={{ y: -20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="mb-6"
          >
            <div className="fashion-icon-container w-20 h-20 mx-auto mb-4">
              <span className="text-4xl">🦄</span>
            </div>
            <h1 className="fashion-section-title text-4xl mb-2">AI Unicorn Wardrobe</h1>
            <p className="text-xl text-fashion-medium-gray font-light">
              Your Magical Personal Fashion Assistant
            </p>
            <div className="ai-powered-badge mt-4">
              Powered by Unicorn Magic ✨
            </div>
          </motion.div>
        </div>

        {/* Main Card */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="fashion-card p-8"
        >
          <AnimatePresence mode="wait">
            {(step === 'name' || step === 'creating') && (
              <motion.div
                key="name-step"
                initial={{ opacity: 0, x: 0 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
              >
                <div className="text-center mb-6">
                  <h2 className="text-2xl font-bold text-fashion-charcoal mb-2">
                    {step === 'creating' ? 'Welcome aboard!' : 'Get Started'}
                  </h2>
                  <p className="text-fashion-medium-gray">
                    {step === 'creating' 
                      ? 'Setting up your magical unicorn wardrobe...' 
                      : 'Create your AI-powered magical fashion experience'
                    }
                  </p>
                </div>

                {step === 'name' && (
                  <form onSubmit={handleNameSubmit} className="space-y-6">
                    <div>
                      <label htmlFor="userName" className="block text-sm font-medium text-fashion-charcoal mb-2">
                        What should we call you?
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                          <UserIcon className="h-5 w-5 text-fashion-medium-gray" />
                        </div>
                        <input
                          type="text"
                          id="userName"
                          value={userName}
                          onChange={(e) => setUserName(e.target.value)}
                          className="block w-full pl-10 pr-3 py-4 border border-fashion-gray rounded-lg focus:ring-2 focus:ring-fashion-secondary focus:border-transparent transition-all bg-fashion-off-white text-fashion-charcoal placeholder-fashion-medium-gray"
                          placeholder="Enter your name"
                          required
                          disabled={isLoading}
                        />
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={!userName.trim() || isLoading}
                      className="btn-fashion-primary w-full py-4 text-lg"
                    >
                      {isLoading ? (
                        <div className="flex items-center justify-center">
                          <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                          Setting up...
                        </div>
                      ) : (
                        <>
                          Continue
                          <ArrowRight className="w-5 h-5 ml-2" />
                        </>
                      )}
                    </button>
                  </form>
                )}

                {step === 'creating' && (
                  <div className="text-center py-8">
                    <div className="flex justify-center mb-6">
                      <div className="w-16 h-16 border-4 border-fashion-secondary border-t-transparent rounded-full animate-spin"></div>
                    </div>
                    <h3 className="text-xl font-semibold text-fashion-charcoal mb-2">
                      Creating Your Magical Fashion Profile
                    </h3>
                    <p className="text-fashion-medium-gray">
                      Personalizing your AI unicorn fashion experience...
                    </p>
                  </div>
                )}
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
                  <div className="fashion-icon-container w-16 h-16 mx-auto mb-4">
                    <Camera className="w-8 h-8 text-white" />
                  </div>
                  <h2 className="text-2xl font-bold text-fashion-charcoal mb-2">
                    Upload Your Photo
                  </h2>
                  <p className="text-fashion-medium-gray">
                    For the best virtual try-on experience
                  </p>
                </div>

                {/* Enhanced Photo Guidelines */}
                <div className="bg-gradient-to-r from-fashion-secondary/10 to-fashion-accent/10 border border-fashion-secondary/20 rounded-xl p-4 mb-6">
                  <h3 className="font-semibold text-fashion-charcoal mb-3 flex items-center">
                    <Sparkles className="w-5 h-5 mr-2 text-fashion-secondary" />
                    Perfect Photo Guidelines
                  </h3>
                  <div className="grid grid-cols-1 gap-2 text-sm text-fashion-dark-gray">
                    <div className="flex items-center space-x-2">
                      <span className="text-fashion-tertiary">✓</span>
                      <span><strong>Upper body visible</strong> - waist up, arms visible</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-fashion-tertiary">✓</span>
                      <span><strong>Good lighting</strong> - bright, even illumination</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-fashion-tertiary">✓</span>
                      <span><strong>Plain background</strong> - simple, uncluttered</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-fashion-tertiary">✓</span>
                      <span><strong>Face the camera</strong> - straight-on pose</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-6">
                  {!userPhoto ? (
                    <div
                      {...getRootProps()}
                      className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                        isDragActive
                          ? 'border-fashion-secondary bg-fashion-secondary/5'
                          : 'border-fashion-gray hover:border-fashion-secondary hover:bg-fashion-light-gray'
                      }`}
                    >
                      <input {...getInputProps()} />
                      <Upload className="w-12 h-12 text-fashion-medium-gray mx-auto mb-4" />
                      <p className="text-lg font-medium text-fashion-charcoal mb-2">
                        {isDragActive ? 'Drop your photo here!' : 'Upload Your Photo'}
                      </p>
                      <p className="text-sm text-fashion-medium-gray">
                        Click or drag to upload • JPEG, PNG • Max 10MB
                      </p>
                    </div>
                  ) : (
                    <div className="relative mx-auto w-fit">
                      <div className="relative p-4 bg-gradient-to-br from-fashion-light-gray to-fashion-gray/50 rounded-xl">
                        <img
                          src={userPhoto}
                          alt="Your photo"
                          className="w-40 h-40 object-cover rounded-lg shadow-lg border-2 border-fashion-white"
                        />
                        <button
                          onClick={() => {
                            setUserPhoto(null);
                            setPhotoFile(null);
                          }}
                          className="absolute -top-2 -right-2 bg-fashion-accent text-white p-2 rounded-full hover:bg-fashion-accent/80 transition-colors shadow-lg"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                      <p className="text-center text-sm text-fashion-tertiary mt-3 font-medium">
                        Perfect for virtual try-ons!
                      </p>
                    </div>
                  )}

                  {userPhoto && (
                    <button
                      onClick={handlePhotoSubmit}
                      disabled={isLoading}
                      className="btn-fashion-primary w-full py-4 text-lg"
                    >
                      {isLoading ? (
                        <div className="flex items-center justify-center">
                          <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                          Processing...
                        </div>
                      ) : (
                        <>
                          <Check className="w-5 h-5 mr-2" />
                          Start My Magical Fashion Journey 🦄
                        </>
                      )}
                    </button>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Footer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="text-center mt-8"
        >
          <p className="text-sm text-fashion-medium-gray whitespace-nowrap">
            Powered by <span className="text-fashion-secondary font-medium">Amazon Bedrock</span> • 
            Virtual try-on with <span className="text-fashion-accent font-medium">Amazon Nova Canvas</span>
          </p>
        </motion.div>
      </motion.div>
    </div>
  );
};