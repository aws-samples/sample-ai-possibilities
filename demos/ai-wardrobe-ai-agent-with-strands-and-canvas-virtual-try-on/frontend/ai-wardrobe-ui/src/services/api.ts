import axios from 'axios';
import { User, WardrobeItem, Outfit } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';
const WS_BASE_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8080';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// User Management
export const registerUser = async (userName: string, profilePhoto?: string) => {
  const response = await api.post('/api/register', { userName, profilePhoto });
  return response.data;
};

// Wardrobe Management
export const uploadClothingItem = async (
  userId: string,
  imageBase64: string,
  category: string,
  attributes?: {
    color?: string;
    style?: string;
    season?: string;
    description?: string;
  }
) => {
  const response = await api.post('/api/upload', {
    userId,
    imageBase64,
    category,
    ...attributes,
  });
  return response.data;
};

export const getWardrobe = async (userId: string, category?: string) => {
  const url = category 
    ? `/api/wardrobe/${userId}?category=${category}`
    : `/api/wardrobe/${userId}`;
  const response = await api.get(url);
  return response.data;
};

// Virtual Try-On
export const createVirtualTryOn = async (
  userId: string,
  modelImageBase64: string,
  garmentItemId: string,
  garmentType: string
) => {
  const response = await api.post('/api/tryon', {
    userId,
    modelImageBase64: modelImageBase64 || null, // Allow null to use profile photo
    garmentItemId,
    garmentType,
  });
  return response.data;
};

// Virtual Try-On with Style Options
export const createVirtualTryOnWithStyle = async (
  userId: string,
  modelImageBase64: string,
  garmentItemId: string,
  garmentType: string,
  styleOptions: {
    sleeveStyle: string;
    tuckingStyle: string;
    outerLayerStyle: string;
  }
) => {
  const response = await api.post('/api/tryon/styled', {
    userId,
    modelImageBase64: modelImageBase64 || null,
    garmentItemId,
    garmentType,
    sleeveStyle: styleOptions.sleeveStyle,
    tuckingStyle: styleOptions.tuckingStyle,
    outerLayerStyle: styleOptions.outerLayerStyle,
  });
  return response.data;
};

// Multi-Item Virtual Try-On
export const createMultiItemTryOn = async (
  userId: string,
  garmentItemIds: string[]
) => {
  const response = await api.post('/api/tryon/multi', {
    userId,
    garmentItemIds,
  });
  return response.data;
};

// Outfits
export const getOutfits = async (userId: string) => {
  const response = await api.get(`/api/outfits/${userId}`);
  return response.data;
};

export const saveOutfit = async (outfitData: {
  userId: string;
  items: string[];
  occasion?: string;
  notes?: string;
}) => {
  const response = await api.post('/api/outfits/save', outfitData);
  return response.data;
};

export const deleteOutfit = async (userId: string, outfitId: string) => {
  const response = await api.delete(`/api/outfits/${outfitId}?user_id=${userId}`);
  return response.data;
};

export const deleteWardrobeItem = async (userId: string, itemId: string) => {
  const response = await api.delete(`/api/wardrobe/${itemId}?user_id=${userId}`);
  return response.data;
};

// WebSocket Connection
export const createWebSocketConnection = (sessionId: string) => {
  return new WebSocket(`${WS_BASE_URL}/ws/${sessionId}`);
};

// Image utilities
export const imageToBase64 = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => {
      const base64 = reader.result as string;
      // Remove data:image/...;base64, prefix
      const base64Data = base64.split(',')[1];
      resolve(base64Data);
    };
    reader.onerror = reject;
  });
};