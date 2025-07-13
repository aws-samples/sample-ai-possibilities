import React from 'react';
import { motion } from 'framer-motion';
import { LogOut, Sparkles } from 'lucide-react';
import { User } from '../../types';

interface ModernHeaderProps {
  user: User;
  onLogout: () => void;
}

export const ModernHeader: React.FC<ModernHeaderProps> = ({ user, onLogout }) => {
  return (
    <header className="bg-white/95 backdrop-blur-sm border-b border-gray-200 shadow-sm">
      <div className="max-w-full mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-20">
          {/* Logo and Brand */}
          <div className="flex items-center gap-4">
            <div className="fashion-icon-container">
              <span className="text-3xl">🦄</span>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-fashion-primary flex items-center gap-2">
                AI Unicorn Wardrobe
                <span className="ai-powered-badge">✨ Magic Powered</span>
              </h1>
              <p className="text-sm text-fashion-medium-gray">
                Your Magical Personal Fashion Assistant
              </p>
            </div>
          </div>

          {/* User Section */}
          <div className="flex items-center gap-6">
            {/* User Info */}
            <div className="flex items-center gap-3">
              {user.profilePhoto && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="relative"
                >
                  <div className="w-12 h-12 rounded-full overflow-hidden ring-2 ring-white/20">
                    <img
                      src={`data:image/jpeg;base64,${user.profilePhoto}`}
                      alt={user.userName}
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-green-500 rounded-full border-2 border-white"></div>
                </motion.div>
              )}
              <div className="text-fashion-primary">
                <p className="font-medium">{user.userName}</p>
                <p className="text-xs text-fashion-medium-gray">Fashion Enthusiast</p>
              </div>
            </div>

            {/* Logout Button */}
            <button
              onClick={onLogout}
              className="btn-fashion-secondary"
            >
              <LogOut className="w-4 h-4 mr-2" />
              Sign Out
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};