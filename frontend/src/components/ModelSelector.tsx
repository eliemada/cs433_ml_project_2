'use client';

import { useState, useEffect, useRef } from 'react';
import { ChevronDown, Zap, Scale, Crown, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface Model {
  id: string;
  name: string;
  provider: string;
  tier: 'fast' | 'balanced' | 'premium';
  description: string;
  context: number;
}

interface ModelSelectorProps {
  selectedModel: string;
  onModelChange: (modelId: string) => void;
}

const tierConfig = {
  fast: {
    icon: Zap,
    color: 'text-blue-500',
    bgColor: 'bg-blue-50 dark:bg-blue-900/20',
    label: 'Fast & Cheap'
  },
  balanced: {
    icon: Scale,
    color: 'text-purple-500',
    bgColor: 'bg-purple-50 dark:bg-purple-900/20',
    label: 'Balanced'
  },
  premium: {
    icon: Crown,
    color: 'text-amber-500',
    bgColor: 'bg-amber-50 dark:bg-amber-900/20',
    label: 'Premium'
  }
};

export function ModelSelector({ selectedModel, onModelChange }: ModelSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(true);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch('/api/models')
      .then(res => res.json())
      .then(data => {
        setModels(data.models);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load models:', err);
        setLoading(false);
      });
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  const selected = models.find(m => m.id === selectedModel);

  // Group models by tier
  const groupedModels = {
    fast: models.filter(m => m.tier === 'fast'),
    balanced: models.filter(m => m.tier === 'balanced'),
    premium: models.filter(m => m.tier === 'premium')
  };

  if (loading) {
    return (
      <div className="animate-pulse bg-gray-200 dark:bg-gray-700 h-12 w-64 rounded-xl" />
    );
  }

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-3 px-4 py-2.5 bg-white dark:bg-gray-800
                   border border-gray-200 dark:border-gray-700 rounded-xl
                   hover:border-gray-300 dark:hover:border-gray-600
                   transition-all duration-200 shadow-sm hover:shadow-md min-w-[280px]"
        aria-label="Select model"
        aria-expanded={isOpen}
      >
        {selected && (
          <>
            {(() => {
              const TierIcon = tierConfig[selected.tier].icon;
              return <TierIcon className={`w-4 h-4 ${tierConfig[selected.tier].color}`} />;
            })()}
            <div className="text-left flex-1">
              <div className="text-sm font-medium text-gray-900 dark:text-white">
                {selected.name}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {selected.provider}
              </div>
            </div>
          </>
        )}
        <ChevronDown
          className={`w-4 h-4 transition-transform text-gray-400
                     ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Dropdown Menu */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full mt-2 w-full min-w-[320px] max-w-md
                       bg-white dark:bg-gray-800 rounded-xl shadow-xl border
                       border-gray-200 dark:border-gray-700 overflow-hidden z-50"
          >
            {Object.entries(groupedModels).map(([tier, tierModels]) => {
              const TierIcon = tierConfig[tier as keyof typeof tierConfig].icon;
              const tierColor = tierConfig[tier as keyof typeof tierConfig].color;
              const tierLabel = tierConfig[tier as keyof typeof tierConfig].label;

              if (tierModels.length === 0) return null;

              return (
                <div key={tier}>
                  {/* Tier Header */}
                  <div className="px-4 py-2 bg-gray-50 dark:bg-gray-900/50
                                border-b border-gray-200 dark:border-gray-700">
                    <div className="flex items-center gap-2">
                      <TierIcon className={`w-3.5 h-3.5 ${tierColor}`} />
                      <span className="text-xs font-semibold uppercase tracking-wider
                                     text-gray-600 dark:text-gray-400">
                        {tierLabel}
                      </span>
                    </div>
                  </div>

                  {/* Models in Tier */}
                  {tierModels.map(model => (
                    <button
                      key={model.id}
                      onClick={() => {
                        onModelChange(model.id);
                        setIsOpen(false);
                      }}
                      className={`w-full px-4 py-3 text-left hover:bg-gray-50
                                dark:hover:bg-gray-700/50 transition-colors
                                ${model.id === selectedModel ? tierConfig[model.tier].bgColor : ''}`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-900 dark:text-white">
                              {model.name}
                            </span>
                            <span className="text-xs text-gray-400 dark:text-gray-500">
                              {model.provider}
                            </span>
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                            {model.description}
                          </div>
                          <div className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                            {(model.context / 1000).toFixed(0)}K context
                          </div>
                        </div>
                        {model.id === selectedModel && (
                          <Check className={`w-4 h-4 flex-shrink-0 mt-0.5 ${tierConfig[model.tier].color}`} />
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
