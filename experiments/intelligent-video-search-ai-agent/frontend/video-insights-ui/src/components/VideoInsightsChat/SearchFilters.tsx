import React from 'react';
import { Users, Building2, Hash, BarChart3, Clock } from 'lucide-react';
import { SearchFiltersProps } from '../../types';

const SearchFilters: React.FC<SearchFiltersProps> = ({ activeFilter, setActiveFilter }) => {
  const filters = [
    { id: 'all', label: 'All Results', icon: null },
    { id: 'people', label: 'People', icon: Users },
    { id: 'brands', label: 'Brands', icon: Hash },
    { id: 'companies', label: 'Companies', icon: Building2 },
    { id: 'sentiment', label: 'Sentiment', icon: BarChart3 },
    { id: 'recent', label: 'Recent', icon: Clock },
  ];

  return (
    <div className="bg-gray-100 border-b px-4 py-3">
      <div className="max-w-4xl mx-auto flex items-center space-x-2 overflow-x-auto">
        {filters.map((filter) => {
          const Icon = filter.icon;
          return (
            <button
              key={filter.id}
              onClick={() => setActiveFilter(filter.id)}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg whitespace-nowrap transition-all ${
                activeFilter === filter.id
                  ? 'bg-brand-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-50'
              }`}
            >
              {Icon && <Icon size={16} />}
              <span className="text-sm font-medium">{filter.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default SearchFilters;