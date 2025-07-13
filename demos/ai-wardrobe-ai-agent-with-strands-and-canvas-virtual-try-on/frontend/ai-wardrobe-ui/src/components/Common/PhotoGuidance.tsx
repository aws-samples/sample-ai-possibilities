import React from 'react';
import { Camera, CheckCircle, XCircle } from 'lucide-react';

interface PhotoGuidanceProps {
  type: 'profile' | 'clothing';
  category?: string;
  compact?: boolean;
}

export const PhotoGuidance: React.FC<PhotoGuidanceProps> = ({ type, category, compact = false }) => {
  const profileGuidance = {
    title: 'Perfect Profile Photo',
    subtitle: 'For amazing virtual try-ons',
    dos: [
      'Show upper body from waist up',
      'Face the camera directly',
      'Use bright, even lighting',
      'Plain background (white/neutral)',
      'Wear fitted clothing'
    ],
    donts: [
      'Dark or poorly lit photos',
      'Busy backgrounds',
      'Loose, baggy clothing',
      'Angled or tilted poses'
    ]
  };

  const clothingGuidance = {
    title: 'Perfect Clothing Photos',
    subtitle: 'For accurate AI analysis',
    dos: [
      'Show the complete garment clearly',
      'Use good lighting and white background',
      'Lay flat or hang properly',
      'Include all details and textures',
      'Take straight-on, uncluttered shots'
    ],
    donts: [
      'Wrinkled or bunched up items',
      'Poor lighting or shadows',
      'Cluttered backgrounds',
      'Partial views of garments'
    ]
  };

  const guidance = type === 'profile' ? profileGuidance : clothingGuidance;

  if (compact) {
    return (
      <div className="bg-gradient-to-r from-blue-50 to-green-50 border border-blue-200 rounded-lg p-3">
        <div className="flex items-center space-x-2 mb-2">
          <Camera className="w-4 h-4 text-blue-600" />
          <span className="text-sm font-semibold text-blue-900">Quick Photo Tips</span>
        </div>
        <div className="text-xs text-blue-700 space-y-1">
          {guidance.dos.slice(0, 3).map((tip, index) => (
            <div key={index} className="flex items-center space-x-1">
              <CheckCircle className="w-3 h-3 text-green-500 flex-shrink-0" />
              <span>{tip}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-blue-50 to-purple-50 border border-blue-200 rounded-xl p-6">
      <div className="flex items-center space-x-3 mb-4">
        <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
          <Camera className="w-5 h-5 text-blue-600" />
        </div>
        <div>
          <h3 className="font-bold text-blue-900">{guidance.title}</h3>
          <p className="text-sm text-blue-600">{guidance.subtitle}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <h4 className="font-semibold text-green-800 mb-2 flex items-center">
            <CheckCircle className="w-4 h-4 mr-1" />
            Do This:
          </h4>
          <div className="space-y-2">
            {guidance.dos.map((tip, index) => (
              <div key={index} className="flex items-start space-x-2">
                <span className="text-green-500 mt-0.5 flex-shrink-0">✓</span>
                <span className="text-sm text-green-800">{tip}</span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h4 className="font-semibold text-red-800 mb-2 flex items-center">
            <XCircle className="w-4 h-4 mr-1" />
            Avoid This:
          </h4>
          <div className="space-y-2">
            {guidance.donts.map((tip, index) => (
              <div key={index} className="flex items-start space-x-2">
                <span className="text-red-500 mt-0.5 flex-shrink-0">✗</span>
                <span className="text-sm text-red-800">{tip}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-4 p-3 bg-white/60 rounded-lg border border-blue-200">
        <p className="text-xs text-blue-700 text-center">
          <span className="font-semibold">💡 Remember:</span> Great photos = Better AI analysis = More accurate virtual try-ons!
        </p>
      </div>
    </div>
  );
};