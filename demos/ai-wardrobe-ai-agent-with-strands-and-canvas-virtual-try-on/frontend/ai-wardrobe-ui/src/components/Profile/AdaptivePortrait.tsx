import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Maximize2, X } from 'lucide-react';

interface AdaptivePortraitProps {
  src: string;
  alt: string;
  userName: string;
  showTryOnLabel?: boolean;
}

export const AdaptivePortrait: React.FC<AdaptivePortraitProps> = ({
  src,
  alt,
  userName,
  showTryOnLabel = false
}) => {
  const [aspectClass, setAspectClass] = useState('aspect-square');
  const [isExpanded, setIsExpanded] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);
  const [isSticky, setIsSticky] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const img = new Image();
    img.onload = () => {
      const aspectRatio = img.width / img.height;
      
      if (aspectRatio < 0.8) {
        // Portrait image
        setAspectClass('aspect-portrait');
      } else if (aspectRatio > 1.2) {
        // Landscape image
        setAspectClass('aspect-landscape');
      } else {
        // Square-ish image
        setAspectClass('aspect-square');
      }
    };
    img.src = src;
  }, [src]);

  // Track scroll for sticky effects and manual sticky positioning
  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY;
      setIsScrolled(scrollY > 100);
      
      // Check if element should be sticky (fallback for CSS sticky)
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        const parentRect = containerRef.current.parentElement?.getBoundingClientRect();
        
        if (parentRect) {
          // If the parent container is scrolled past, activate sticky
          const shouldBeSticky = parentRect.top < 32; // 2rem = 32px
          setIsSticky(shouldBeSticky);
        }
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll(); // Check initial state
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <>
      <div 
        ref={containerRef}
        className={`portrait-container ${aspectClass} group ${
          isScrolled ? 'scrolled' : ''
        } ${
          isSticky ? 'js-sticky' : ''
        }`}
        style={{
          // JavaScript fallback for sticky positioning
          ...(isSticky && window.innerWidth > 1200 ? {
            position: 'fixed',
            top: '2rem',
            zIndex: 50,
            transform: 'translateY(0)',
          } : {})
        }}
      >
        <div className="wall-portrait-frame">
          <div className="portrait-border relative">
            <img
              ref={imgRef}
              src={src}
              alt={alt}
              className="portrait-image cursor-pointer"
              loading="lazy"
              onClick={() => setIsExpanded(true)}
            />
            
            {/* Expand button - shows on hover */}
            <motion.button
              initial={{ opacity: 0 }}
              whileHover={{ scale: 1.1 }}
              className="absolute top-2 left-2 bg-black/50 text-white p-1 rounded-full opacity-0 group-hover:opacity-100 transition-opacity z-10"
              onClick={() => setIsExpanded(true)}
              title="View full image"
            >
              <Maximize2 className="w-4 h-4" />
            </motion.button>
            
            <div className="portrait-nameplate">
              <span>{userName}</span>
              {showTryOnLabel && (
                <span className="text-xs text-blue-600 font-medium">Virtual Try-On</span>
              )}
            </div>
            {/* Frame decorative elements */}
            <div className="frame-corner top-left"></div>
            <div className="frame-corner top-right"></div>
            <div className="frame-corner bottom-left"></div>
            <div className="frame-corner bottom-right"></div>
          </div>
          {/* Wall hanging system */}
          <div className="wall-hanging-wire"></div>
          <div className="wall-nail"></div>
        </div>
      </div>

      {/* Full Screen Modal */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/90 flex items-center justify-center p-4 z-50"
            onClick={() => setIsExpanded(false)}
          >
            <motion.div
              initial={{ scale: 0.8 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.8 }}
              className="relative max-w-4xl max-h-full"
              onClick={(e) => e.stopPropagation()}
            >
              <img
                src={src}
                alt={alt}
                className="max-w-full max-h-full object-contain rounded-lg"
              />
              <button
                onClick={() => setIsExpanded(false)}
                className="absolute top-4 right-4 bg-black/50 text-white p-2 rounded-full hover:bg-black/70 transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
              <div className="absolute bottom-4 left-4 bg-black/50 text-white px-3 py-1 rounded">
                {userName} {showTryOnLabel && '• Virtual Try-On'}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};